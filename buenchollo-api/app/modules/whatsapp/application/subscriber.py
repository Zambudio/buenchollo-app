"""Suscriptor de `DealPostPublished`: si el canal cuenta para WhatsApp
(`WHATSAPP_CHANNELS`), encola el post. Registrado en `app.core.bootstrap`."""

from app.core.config import get_settings
from app.core.events import DealPostPublished
from app.modules.whatsapp.application.queue import goes_to_whatsapp, queue_whatsapp_post


async def on_deal_post_published(event: DealPostPublished) -> None:
    settings = get_settings()
    if not settings.whatsapp_enabled or not goes_to_whatsapp(event.channel_id, settings):
        return
    await queue_whatsapp_post(
        event.session,
        settings,
        deal_id=event.deal_id,
        telegram_text=event.text,
        whatsapp_text=event.whatsapp_text,
        card=event.card,
        image_url=event.image_url,
        download=event.download,
    )
