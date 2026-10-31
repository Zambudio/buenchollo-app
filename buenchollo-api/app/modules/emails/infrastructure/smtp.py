"""Cliente de envío de correo electrónico a través de SMTP (Zoho Mail / Producción).

Soporta conexiones directas con SSL (puerto 465) y STARTTLS (puerto 587),
con ejecución asíncrona mediante `asyncio.to_thread` para no bloquear el bucle de eventos
de FastAPI durante las operaciones de red.
"""
import asyncio
from email.message import EmailMessage
import logging
import smtplib
from typing import Protocol

from app.core.config import Settings, get_settings
from app.modules.emails.domain.messages import OutgoingEmail

logger = logging.getLogger(__name__)


class EmailSenderProtocol(Protocol):
    """Interfaz para enviar correos electrónicos salientes."""

    def send(self, email: OutgoingEmail) -> bool:
        ...

    async def send_async(self, email: OutgoingEmail) -> bool:
        ...


class SmtpEmailSender:
    """Implementación de envío SMTP estándar compatible con Zoho Mail."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def send(self, email: OutgoingEmail) -> bool:
        """Envía un correo de forma síncrona. Devuelve True si tuvo éxito, False en caso de error."""
        if not self.settings.smtp_host or not self.settings.smtp_user:
            logger.warning("SMTP no configurado: omitiendo envío a %s", email.to)
            return False

        if not self.settings.smtp_password:
            logger.warning("SMTP_PASSWORD no configurado en el entorno: omitiendo envío a %s", email.to)
            return False

        msg = EmailMessage()
        msg["Subject"] = email.subject
        msg["From"] = f"{self.settings.smtp_from_name} <{self.settings.smtp_from_email}>"
        msg["To"] = email.to
        if self.settings.smtp_reply_to:
            msg["Reply-To"] = self.settings.smtp_reply_to

        for header_key, header_val in email.headers.items():
            if header_key not in msg:
                msg[header_key] = header_val

        msg.set_content(email.text)
        msg.add_alternative(email.html, subtype="html")

        try:
            timeout = self.settings.smtp_timeout_seconds
            if self.settings.smtp_port == 465 or self.settings.smtp_use_ssl:
                with smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, timeout=timeout) as server:
                    server.login(self.settings.smtp_user, self.settings.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=timeout) as server:
                    server.starttls()
                    server.login(self.settings.smtp_user, self.settings.smtp_password)
                    server.send_message(msg)

            logger.info("Correo enviado con éxito a %s: '%s'", email.to, email.subject)
            return True
        except (smtplib.SMTPException, OSError) as exc:
            # Nunca se loguea la contraseña ni credenciales
            logger.error("Error al enviar correo vía SMTP a %s (%s): %s", email.to, self.settings.smtp_host, exc)
            return False

    async def send_async(self, email: OutgoingEmail) -> bool:
        """Envía un correo de forma asíncrona delegando en un hilo de trabajo."""
        return await asyncio.to_thread(self.send, email)


_default_sender: SmtpEmailSender | None = None


def get_email_sender() -> SmtpEmailSender:
    """Devuelve la instancia singleton del remitente SMTP."""
    global _default_sender
    if _default_sender is None:
        _default_sender = SmtpEmailSender()
    return _default_sender
