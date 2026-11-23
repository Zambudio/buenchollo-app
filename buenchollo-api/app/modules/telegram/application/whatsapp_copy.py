"""Segundo envío de cada publicación: la versión WhatsApp al canal Admin de
Telegram, lista para copiarla al Canal de WhatsApp desde el móvil (WhatsApp no
tiene API oficial para publicar en Canales).

Va siempre al canal Admin, nunca al público, y un fallo aquí no afecta a la
publicación de Telegram, que ya está enviada.
"""

import logging

from app.modules.telegram.application.whatsapp_formatter import to_whatsapp_text

logger = logging.getLogger(__name__)


def send_whatsapp_copy(
    bot,
    *,
    chat_id: str,
    telegram_text: str,
    image_url: str | None = None,
    whatsapp_text: str | None = None,
    image_bytes: bytes | None = None,
) -> bool:
    """Envía en texto plano (sin entidades: los `*` quedan para WhatsApp), con la
    tarjeta de oferta (`image_bytes`) si la hay o la foto original. Si la imagen
    falla (p. ej. pie de foto demasiado largo), reintenta con la foto original y
    luego solo con texto."""
    if not chat_id:
        return False
    try:
        text = (whatsapp_text or "").strip() or to_whatsapp_text(telegram_text)
        if not text:
            return False
        if image_bytes and bot.send_photo_bytes(image_bytes, chat_id=chat_id, caption=text):
            return True
        if bot.send_preformatted(text=text, entities=[], image_url=image_url, chat_id=chat_id):
            return True
        if image_url and bot.send_preformatted(text=text, entities=[], image_url=None, chat_id=chat_id):
            return True
    except Exception:
        logger.exception("No se pudo enviar la versión WhatsApp al canal Admin")
        return False
    logger.warning("Telegram rechazó la versión WhatsApp: %s", getattr(bot, "last_error", None))
    return False
