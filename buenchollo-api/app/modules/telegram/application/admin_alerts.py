"""Suscriptor de `AdminAlert`: entrega los avisos de otros módulos (p. ej. un
fallo de Instagram) al canal Admin de Telegram. Nunca lanza."""

import asyncio
import logging

from app.core.config import get_settings
from app.core.events import AdminAlert
from app.modules.telegram.infrastructure.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)


async def send_admin_alert(event: AdminAlert) -> None:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_admin_channel_id:
        logger.warning("Aviso al administrador sin canal Admin configurado: %s", event.text[:200])
        return
    bot = TelegramBot(settings.telegram_bot_token)
    await asyncio.to_thread(bot.send_admin_notification, event.text, chat_id=settings.telegram_admin_channel_id)
