"""Suscriptores del Canal de WhatsApp, registrados en `app.core.bootstrap`:

- `DealPostPublished`: si el canal cuenta para WhatsApp (`WHATSAPP_CHANNELS`),
  encola el post en la misma transacción que Telegram.
- `WhatsAppPostRequested` (resumen semanal): lo encola con su propia sesión.
"""

from app.core.config import get_settings
from app.core.events import DealPostPublished, WhatsAppPostRequested
from app.core.jobs import job_session
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


async def on_whatsapp_post_requested(event: WhatsAppPostRequested) -> None:
    settings = get_settings()
    if not settings.whatsapp_enabled or not settings.database_url:
        return
    async with job_session(settings) as session:
        if await queue_whatsapp_post(
            session,
            settings,
            deal_id=event.deal_id,
            telegram_text=event.telegram_text,
            whatsapp_text=event.whatsapp_text,
            card=event.image,
            image_url=None,
            strip_prices=event.strip_prices,
        ):
            await session.commit()
