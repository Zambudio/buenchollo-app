"""Registro de publicaciones de Telegram (panel y chollos programados)."""

import logging
from datetime import datetime
from decimal import Decimal

from app.modules.affiliates.domain.links import InvalidLinkError, canonicalize
from app.modules.telegram.application.reprice import reprice_publication_text
from app.modules.telegram.domain.models import TelegramPublication

logger = logging.getLogger(__name__)


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


async def record_safely(session, repo, deal_repo, **kwargs) -> bool:
    """Registra en un savepoint y nunca lanza: la publicación ya está en
    Telegram, y un fallo del registro no puede deshacer ni repetir el envío
    (abortaría la transacción y el llamante lo reintentaría)."""
    try:
        async with session.begin_nested():
            await record_publication(repo, deal_repo, **kwargs)
        return True
    except Exception:
        logger.exception("No se pudo registrar la publicación de Telegram (ya enviada)")
        return False


class PublicationRecorder:
    """Adaptador para workers: registra con el canal clasificado y una fuente fija."""

    def __init__(self, repo, deal_repo, settings, source: str):
        self.repo = repo
        self.deal_repo = deal_repo
        self.settings = settings
        self.source = source

    async def record(self, *, deal_id, channel_id, text, image_url=None, message_id=None):
        return await record_safely(
            self.repo.session, self.repo, self.deal_repo, text=text, channel_id=channel_id,
            kind=channel_kind(channel_id, self.settings), source=self.source,
            image_url=image_url, deal_id=deal_id, message_id=message_id,
        )


def with_current_price(publications, deal, now: datetime) -> list[str | None]:
    """Texto de cada publicación con el precio actual del chollo (None si no se
    puede corregir): «Usar la última publicación» nunca reutiliza un precio viejo."""
    if deal is None:
        return [None for _ in publications]
    previous = Decimal(str(deal.previous_price)) if deal.previous_price is not None else None
    return [
        reprice_publication_text(
            p.text, price=Decimal(str(deal.current_price)), previous_price=previous,
            discount_pct=deal.discount_percentage, expires_at=deal.expires_at, now=now,
        )
        for p in publications
    ]
