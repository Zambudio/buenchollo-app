import logging
from collections.abc import Awaitable, Callable

from fastapi.concurrency import run_in_threadpool

from app.core import database
from app.core.config import Settings
from app.core.security import get_supabase_client
from app.modules.emails.application.rendering import (
    EmailBranding,
    format_eur,
    render_submission_admin,
    render_submission_approved,
    render_submission_rejected,
)
from app.modules.emails.domain.messages import OutgoingEmail, RenderedEmail
from app.modules.emails.infrastructure.smtp import EmailSenderProtocol
from app.modules.notifications.infrastructure.repository import NotificationRepository
from app.modules.submissions.domain.models import APPROVED, REJECTED
from app.modules.submissions.infrastructure.repository import SubmissionRepository

logger = logging.getLogger(__name__)

WARNING_LABELS = {
    "amazon_foreign_marketplace": "Amazon de otro país (sin nuestro tag)",
    "third_party_affiliate_removed": "Se eliminó un enlace de afiliado ajeno",
    "not_affiliable": "Tienda sin afiliación",
}


def supabase_user_email_lookup(settings: Settings) -> Callable[[str], Awaitable[str | None]]:
    def _lookup(user_id: str) -> str | None:
        res = get_supabase_client(settings).auth.admin.get_user_by_id(user_id)
        return getattr(getattr(res, "user", None), "email", None)

    async def lookup(user_id: str) -> str | None:
        return await run_in_threadpool(_lookup, user_id)

    return lookup


class SubmissionNotifier:
    def __init__(
        self,
        sender: EmailSenderProtocol,
        branding: EmailBranding,
        settings: Settings,
        user_email_lookup: Callable[[str], Awaitable[str | None]],
        session_factory: Callable | None = None,
    ) -> None:
        self.sender = sender
        self.branding = branding
        self.settings = settings
        self.user_email_lookup = user_email_lookup
        self.session_factory = session_factory or (lambda: database.AsyncSessionLocal())

    async def notify_admin_new(self, submission_id: str) -> None:
        try:
            admin_email = (self.settings.admin_notification_email or "").strip()
            if not admin_email:
                return
            async with self.session_factory() as session:
                sub = await SubmissionRepository(session).get(submission_id)
                if sub is None:
                    logger.warning("Propuesta %s no encontrada: aviso al admin omitido", submission_id)
                    return
                rendered = render_submission_admin(
                    self.branding,
                    title=sub.title,
                    price=format_eur(sub.current_price) or "",
                    previous_price=format_eur(sub.previous_price),
                    store=sub.store.name if sub.store else sub.store_name,
                    author=(sub.user.display_name or sub.user.username or "Usuario"),
                    image_url=sub.image_url,
                    review_url=f"{self.branding.site_url}/admin/propuestas?id={sub.id}",
                    warnings=[WARNING_LABELS.get(w, w) for w in (sub.warnings or [])],
                )
            await self._send(admin_email, rendered)
        except Exception:
            logger.exception("No se pudo avisar al admin de la propuesta %s", submission_id)

    async def notify_user_decision(self, submission_id: str) -> None:
        try:
            async with self.session_factory() as session:
                sub = await SubmissionRepository(session).get(submission_id)
                if sub is None:
                    logger.warning("Propuesta %s no encontrada: notificación al usuario omitida", submission_id)
                    return
                if sub.status not in (APPROVED, REJECTED):
                    return
                name = sub.user.display_name or sub.user.username
                if sub.status == APPROVED:
                    if sub.deal is None:
                        logger.warning("Propuesta aprobada %s sin chollo asociado: notificación omitida", submission_id)
                        return
                    slug = sub.deal.slug
                    notification = {
                        "user_id": sub.user_id,
                        "type": "submission_approved",
                        "title": "Tu chollo ya está publicado",
                        "body": sub.title,
                        "link_url": f"/chollo/{slug}",
                        "deal_id": sub.deal_id,
                    }
                    rendered = render_submission_approved(
                        self.branding,
                        name=name,
                        title=sub.title,
                        deal_url=f"{self.branding.site_url}/chollo/{slug}",
                    )
                else:
                    notification = {
                        "user_id": sub.user_id,
                        "type": "submission_rejected",
                        "title": "Tu propuesta no ha sido publicada",
                        "body": sub.rejection_reason,
                        "link_url": "/mis-chollos",
                    }
                    rendered = render_submission_rejected(
                        self.branding,
                        name=name,
                        title=sub.title,
                        reason=sub.rejection_reason or "Sin motivo indicado",
                        my_deals_url=f"{self.branding.site_url}/mis-chollos",
                    )
                await NotificationRepository(session).create(notification)
                await session.commit()
                user_id = sub.user_id
            email = await self.user_email_lookup(user_id)
            if email:
                await self._send(email, rendered)
        except Exception:
            logger.exception("No se pudo notificar la decisión de la propuesta %s", submission_id)

    async def _send(self, to: str, rendered: RenderedEmail) -> None:
        sent = await self.sender.send_async(
            OutgoingEmail(to=to, subject=rendered.subject, html=rendered.html, text=rendered.text)
        )
        if not sent:
            logger.warning("El envío del correo '%s' no se completó", rendered.subject)
