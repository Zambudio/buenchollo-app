"""Worker periódico para el resumen nocturno de alertas por correo.

Se ejecuta cada noche para recopilar chollos coincidentes y enviarlos en un único
resumen consolidado a los usuarios con aviso por email activado.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import logging

from sqlalchemy import select, and_, text

from app.core.config import Settings
from app.core.database import AsyncSessionLocal
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


async def _process_nightly_alert_digest(settings: Settings) -> None:
    sender = SmtpEmailSender(settings)
    branding = EmailBranding()
    today = date.today()

    async with AsyncSessionLocal() as session:
        # 1. Obtener alertas activas con aviso por correo
        alerts_result = await session.execute(
            select(Alert).where(and_(Alert.is_active == True, Alert.notify_email == True))
        )
        active_alerts = alerts_result.scalars().all()
        if not active_alerts:
            logger.info("Resumen de alertas: No hay alertas activas con aviso por email.")
            return

        # 2. Agrupar alertas por user_id
        user_alerts: dict[str, list[Alert]] = {}
        for alert in active_alerts:
            user_alerts.setdefault(alert.user_id, []).append(alert)

        # 3. Obtener chollos activos recientes (últimas 24h)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        deals_result = await session.execute(
            select(Deal).where(and_(Deal.is_active == True, Deal.created_at >= since))
        )
        recent_deals = deals_result.scalars().all()
        if not recent_deals:
            logger.info("Resumen de alertas: No hay chollos nuevos en las últimas 24h.")
            return

        # 4. Para cada usuario, casar chollos con sus alertas
        for user_id, alerts in user_alerts.items():
            matched_deals: list[DigestDeal] = []
            matched_deal_ids = set()

            for deal in recent_deals:
                matching_alert_names = []
                for alert in alerts:
                    # Comprobación de palabras clave
                    if alert.keyword and alert.keyword.lower() not in (deal.title or "").lower():
                        continue
                    # Comprobación de categoría
                    if alert.category_id and deal.category_id != alert.category_id:
                        continue
                    # Comprobación de tienda
                    if alert.store_id and deal.store_id != alert.store_id:
                        continue
                    # Comprobación de precio máximo
                    if alert.max_price is not None and deal.price is not None and deal.price > alert.max_price:
                        continue
                    # Comprobación de descuento mínimo
                    if alert.min_discount is not None and (deal.discount or 0) < alert.min_discount:
                        continue

                    matching_alert_names.append(alert.name)

                if matching_alert_names and deal.id not in matched_deal_ids:
                    matched_deal_ids.add(deal.id)
                    digest_deal = build_digest_deal(
                        branding=branding,
                        title=deal.title,
                        slug=deal.slug or str(deal.id),
                        image_url=deal.image_url,
                        current_price=Decimal(str(deal.price)) if deal.price is not None else Decimal("0.00"),
                        previous_price=Decimal(str(deal.original_price)) if deal.original_price is not None else None,
                        discount_percentage=deal.discount,
                        store_name=deal.store.name if getattr(deal, "store", None) else None,
                        short_description=deal.short_description or (deal.description[:120] if deal.description else None),
                        expires_at=getattr(deal, "expires_at", None),
                        asin=getattr(deal, "asin", None),
                        show_price_history=bool(getattr(deal, "asin", None)),
                        alert_names=tuple(matching_alert_names),
                    )
                    matched_deals.append(digest_deal)

            if not matched_deals:
                continue

            unsubscribe_url = f"{branding.base_url}/perfil?tab=alertas"

            try:
                # Obtener email y display_name del usuario
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
                    logger.warning("No se pudo obtener el email de auth.users para el usuario %s", user_id)
                    continue

                user_email = user_row["email"]
                display_name = user_row.get("display_name")

                rendered = render_alert_digest(
                    branding,
                    name=display_name,
                    digest_date=today,
                    deals=matched_deals,
                    unsubscribe_url=unsubscribe_url,
                )

                outgoing = OutgoingEmail(
                    to=user_email,
                    subject=rendered.subject,
                    html=rendered.html,
                    text=rendered.text,
                    headers={"List-Unsubscribe": f"<{unsubscribe_url}>"},
                )

                sent = sender.send(outgoing)
                if sent:
                    logger.info("Resumen nocturno enviado con éxito a %s (%d chollos)", user_email, len(matched_deals))
                else:
                    logger.warning("Fallo al enviar resumen nocturno a %s", user_email)
            except Exception as exc:
                logger.error("Error al procesar resumen de alertas para usuario %s: %s", user_id, exc)


def run_due_alert_digest(settings: Settings) -> None:
    """Entrypoint síncrono para el BackgroundScheduler de APScheduler."""
    import asyncio
    try:
        asyncio.run(_process_nightly_alert_digest(settings))
    except Exception as exc:
        logger.error("Fallo general en ejecución de resumen nocturno de alertas: %s", exc)
