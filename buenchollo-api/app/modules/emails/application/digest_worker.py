"""Worker periódico para el resumen nocturno de alertas por correo.

Se ejecuta cada noche para recopilar chollos coincidentes y enviarlos en un único
resumen consolidado a los usuarios con aviso por email activado.
"""
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
import logging

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.database import AsyncSessionLocal
from app.modules.alerts.application.matching import matches_alert
from app.modules.alerts.domain.models import Alert
from app.modules.deals.domain.models import Deal
from app.modules.emails.application.rendering import (
    EmailBranding,
    build_digest_deal,
    render_alert_digest,
)
from app.modules.emails.domain.messages import DigestDeal, OutgoingEmail
from app.modules.emails.infrastructure.smtp import SmtpEmailSender

logger = logging.getLogger(__name__)

DIGEST_WINDOW = timedelta(hours=24)


def _to_digest_deal(branding: EmailBranding, deal: Deal, alert_names: tuple[str, ...]) -> DigestDeal:
    store = deal.store
    return build_digest_deal(
        branding=branding,
        title=deal.title,
        slug=deal.slug,
        image_url=deal.image_url,
        current_price=deal.current_price,
        previous_price=deal.previous_price,
        discount_percentage=deal.discount_percentage,
        store_name=store.name if store else None,
        short_description=deal.short_description or (deal.description[:120] if deal.description else None),
        expires_at=deal.expires_at,
        asin=deal.external_id,
        show_price_history=bool(deal.show_keepa_chart),
        alert_names=alert_names,
    )


def build_user_digests(
    branding: EmailBranding,
    alerts: Iterable[Alert],
    deals: Iterable[Deal],
) -> dict[str, list[DigestDeal]]:
    """Agrupa por usuario los chollos que coinciden con alguna de sus alertas.

    Función pura (sin BD ni I/O). Cada chollo aparece una sola vez por usuario,
    con los nombres de todas las alertas que lo han disparado.
    """
    alerts_by_user: dict[str, list[Alert]] = {}
    for alert in alerts:
        alerts_by_user.setdefault(str(alert.user_id), []).append(alert)

    deals = list(deals)
    digests: dict[str, list[DigestDeal]] = {}
    for user_id, user_alerts in alerts_by_user.items():
        matched: list[DigestDeal] = []
        for deal in deals:
            names = tuple(alert.name for alert in user_alerts if matches_alert(alert, deal))
            if names:
                matched.append(_to_digest_deal(branding, deal, names))
        if matched:
            digests[user_id] = matched
    return digests


async def _process_nightly_alert_digest(settings: Settings) -> None:
    sender = SmtpEmailSender(settings)
    branding = EmailBranding()
    today = date.today()
    since = datetime.now(timezone.utc) - DIGEST_WINDOW

    async with AsyncSessionLocal() as session:
        alerts = (
            await session.execute(
                select(Alert).where(Alert.is_active.is_(True), Alert.notify_email.is_(True))
            )
        ).scalars().all()
        if not alerts:
            logger.info("Resumen de alertas: no hay alertas activas con aviso por email.")
            return

        deals = (
            await session.execute(
                select(Deal)
                .options(selectinload(Deal.store))
                .where(Deal.status == "active", Deal.published_at >= since)
            )
        ).scalars().all()
        if not deals:
            logger.info("Resumen de alertas: no hay chollos publicados en las últimas 24 h.")
            return

        unsubscribe_url = f"{branding.site_url}/perfil?tab=alertas"
        for user_id, matched_deals in build_user_digests(branding, alerts, deals).items():
            try:
                user_row = (
                    await session.execute(
                        text(
                            "SELECT u.email, p.display_name "
                            "FROM auth.users u "
                            "LEFT JOIN public.profiles p ON p.user_id = u.id "
                            "WHERE u.id = CAST(:user_id AS uuid)"
                        ),
                        {"user_id": user_id},
                    )
                ).mappings().first()

                if not user_row or not user_row.get("email"):
                    logger.warning("Resumen de alertas: usuario %s sin email en auth.users", user_id)
                    continue

                rendered = render_alert_digest(
                    branding,
                    name=user_row.get("display_name"),
                    digest_date=today,
                    deals=matched_deals,
                    unsubscribe_url=unsubscribe_url,
                )
                sent = sender.send(
                    OutgoingEmail(
                        to=user_row["email"],
                        subject=rendered.subject,
                        html=rendered.html,
                        text=rendered.text,
                        headers={"List-Unsubscribe": f"<{unsubscribe_url}>"},
                    )
                )
                # Solo user_id en logs: el email es PII (SECURITY_AUDIT.md SEC-09).
                if sent:
                    logger.info(
                        "Resumen nocturno enviado a user_id=%s (%d chollos)", user_id, len(matched_deals)
                    )
                else:
                    logger.warning("Fallo al enviar resumen nocturno a user_id=%s", user_id)
            except Exception:
                logger.exception("Error al procesar el resumen de alertas de user_id=%s", user_id)


def run_due_alert_digest(settings: Settings) -> None:
    """Entrypoint síncrono para el BackgroundScheduler de APScheduler."""
    import asyncio

    try:
        asyncio.run(_process_nightly_alert_digest(settings))
    except Exception:
        logger.exception("Fallo general en la ejecución del resumen nocturno de alertas")
