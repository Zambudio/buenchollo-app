"""Registro de publicaciones de Telegram (panel y chollos programados)."""

from app.modules.affiliates.domain.links import InvalidLinkError, canonicalize
from app.modules.telegram.domain.models import TelegramPublication


def channel_kind(channel_id: str, settings) -> str:
    if channel_id and channel_id == settings.telegram_main_channel_id:
        return "main"
    if channel_id and channel_id == settings.telegram_admin_channel_id:
        return "admin"
    return "other"


async def record_publication(
    repo,
    deal_repo,
    *,
    text: str,
    channel_id: str,
    kind: str,
    source: str,
    image_url: str | None = None,
    deal_id: str | None = None,
    affiliate_url: str | None = None,
    message_id: int | None = None,
    sent_by: str | None = None,
) -> TelegramPublication:
    """Guarda lo enviado. El chollo se identifica por `deal_id` o, si el panel
    no lo conoce (formulario sin guardar), por el ASIN del enlace. Se guardan
    los precios del chollo en ese momento para poder corregirlos después."""
    deal = await deal_repo.get_by_id(deal_id) if deal_id else None
    if deal is None and affiliate_url:
        asin = _asin_of(affiliate_url)
        if asin:
            deal = await deal_repo.find_by_external_id(asin, exclude_id=None)
    publication = TelegramPublication(
        deal_id=deal.id if deal else None,
        channel_id=channel_id,
        channel_kind=kind,
        source=source,
        text=text,
        image_url=image_url,
        price=deal.current_price if deal else None,
        previous_price=deal.previous_price if deal else None,
        discount_percentage=deal.discount_percentage if deal else None,
        telegram_message_id=message_id,
        sent_by=sent_by,
    )
    return await repo.add(publication)


def _asin_of(url: str) -> str | None:
    try:
        asin = canonicalize(url).asin
    except InvalidLinkError:
        return None
    return asin.upper() if asin else None


class PublicationRecorder:
    """Adaptador para workers: registra con el canal clasificado y una fuente fija."""

    def __init__(self, repo, deal_repo, settings, source: str):
        self.repo = repo
        self.deal_repo = deal_repo
        self.settings = settings
        self.source = source

    async def record(self, *, deal_id, channel_id, text, image_url=None, message_id=None):
        return await record_publication(
            self.repo, self.deal_repo, text=text, channel_id=channel_id,
            kind=channel_kind(channel_id, self.settings), source=self.source,
            image_url=image_url, deal_id=deal_id, message_id=message_id,
        )
