"""Suscriptor de `DealPostPublished`: si el canal cuenta para Facebook
(`FACEBOOK_CHANNELS`), encola el post. Registrado en `app.core.bootstrap`."""

from app.core.config import get_settings
from app.core.events import DealPostPublished
from app.modules.facebook.application.queue import goes_to_facebook, queue_facebook_post


async def on_deal_post_published(event: DealPostPublished) -> None:
    settings = get_settings()
    if not settings.facebook_enabled or not goes_to_facebook(event.channel_id, settings):
        return
    await queue_facebook_post(
        event.session,
        settings,
        deal_id=event.deal_id,
        telegram_text=event.text,
        card=event.card,
        image_url=event.image_url,
        download=event.download,
    )
