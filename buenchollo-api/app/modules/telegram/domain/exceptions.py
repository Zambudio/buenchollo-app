"""Excepciones de dominio del módulo telegram."""
from app.core.exceptions import ServiceUnavailableError, ValidationError


class TelegramNotConfigured(ServiceUnavailableError):
    def __init__(self) -> None:
        super().__init__("Telegram no configurado. Añade TELEGRAM_BOT_TOKEN al .env")


class TelegramChannelNotConfigured(ServiceUnavailableError):
    def __init__(self) -> None:
        super().__init__("No hay canal Telegram configurado. Añade TELEGRAM_MAIN_CHANNEL_ID al .env")


class TelegramNotifyPayloadInvalid(ValidationError):
    """El status original de este error era 422, no el 400 por defecto de ValidationError."""

    http_status = 422

    def __init__(self) -> None:
        super().__init__("Se requiere 'text' o bien 'title' + 'current_price'")


class TelegramSendFailed(ServiceUnavailableError):
    def __init__(self) -> None:
        super().__init__("Error al enviar a Telegram. Revisa los logs del servidor.")
