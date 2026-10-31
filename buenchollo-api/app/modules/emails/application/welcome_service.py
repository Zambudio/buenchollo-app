"""Servicio de aplicación para el envío del correo de bienvenida.

Garantiza la idempotencia mediante metadatos de usuario en Supabase Auth
para evitar envíos repetidos al mismo usuario.
"""
from datetime import datetime, timezone
import logging

from supabase import Client

from app.modules.emails.application.rendering import EmailBranding, render_welcome
from app.modules.emails.domain.messages import OutgoingEmail
from app.modules.emails.infrastructure.smtp import EmailSenderProtocol, get_email_sender

logger = logging.getLogger(__name__)


class WelcomeEmailService:
    """Envía el correo oficial de bienvenida asegurando idempotencia."""

    def __init__(
        self,
        sender: EmailSenderProtocol | None = None,
        branding: EmailBranding | None = None,
        supabase_client: Client | None = None,
    ) -> None:
        self.sender = sender or get_email_sender()
        self.branding = branding or EmailBranding()
        self.supabase = supabase_client

    async def send_welcome_if_needed(
        self,
        user_id: str,
        email: str,
        name: str | None = None,
    ) -> bool:
        """Envía el correo de bienvenida si no ha sido enviado previamente.

        Devuelve True si se envió el correo, o False si ya se había enviado o falló.
        """
        if not email or "@" not in email:
            logger.warning("Intento de envío de bienvenida a email inválido: %s", email)
            return False

        # Comprobación de idempotencia vía user_metadata en Supabase si está disponible
        user_meta = {}
        if self.supabase is not None:
            try:
                # Comprobar si el admin client está disponible
                admin_auth = getattr(self.supabase.auth, "admin", None)
                if admin_auth and hasattr(admin_auth, "get_user_by_id"):
                    res = admin_auth.get_user_by_id(user_id)
                    user_data = getattr(res, "user", None) or res
                    if user_data:
                        user_meta = getattr(user_data, "user_metadata", {}) or {}
                        if user_meta.get("welcome_email_sent_at"):
                            logger.info("Correo de bienvenida ya enviado previamente a usuario %s", user_id)
                            return False
            except Exception as exc:
                logger.warning("No se pudo verificar metadatos de usuario en Supabase Auth: %s", exc)

        rendered = render_welcome(self.branding, name=name)
        outgoing = OutgoingEmail(
            to=email,
            subject=rendered.subject,
            html=rendered.html,
            text=rendered.text,
        )

        sent = await self.sender.send_async(outgoing)
        if sent and self.supabase is not None:
            try:
                admin_auth = getattr(self.supabase.auth, "admin", None)
                if admin_auth and hasattr(admin_auth, "update_user_by_id"):
                    now_str = datetime.now(timezone.utc).isoformat()
                    updated_meta = {**user_meta, "welcome_email_sent_at": now_str}
                    admin_auth.update_user_by_id(user_id, {"user_metadata": updated_meta})
            except Exception as exc:
                logger.warning("No se pudo actualizar welcome_email_sent_at en Supabase Auth: %s", exc)

        return sent
