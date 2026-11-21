"""«Los chollos de la semana»: resumen de los domingos a las 22:30 (Madrid).

Toma los chollos activos publicados (o reactivados) en los 7 días naturales
anteriores (hora de Madrid) con más descuento y envía al canal Admin de
Telegram tres mensajes: un collage con la foto de cada chollo y su número del
top, la versión de Telegram del texto (emojis premium y negrita, como los posts
normales) y la versión de WhatsApp, para que el admin los reenvíe al canal
oficial y los copie al Canal de WhatsApp a mano. Nunca publica directamente en
el canal público.

Un chollo de Awin/Tradedoubler solo entra si sigue cumpliendo las reglas de
publicación (las mismas que comprueba `/telegram/notify`).
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, wait
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.jobs import SCHEDULER_TIMEZONE, job_session
from app.modules.affiliates.application.programs import needs_network_rules
from app.modules.deals.domain.week import WeekWindow, week_window  # noqa: F401  (ventana común con la web)
from app.modules.telegram.application.weekly_collage import CollageItem, build_collage
from app.modules.telegram.application.post_generator import LINK_TEXT, _format_price_es
from app.modules.telegram.application.whatsapp_copy import send_whatsapp_copy
from app.modules.telegram.application.whatsapp_formatter import to_whatsapp_text

logger = logging.getLogger(__name__)

WEEKLY_DIGEST_LIMIT = 10
# Se piden más de los que se publican por si alguno no pasa las reglas de afiliación.
_CANDIDATES = 25
# Telegram admite 4096 caracteres por mensaje; se deja margen.
MAX_TEXT_LENGTH = 3900

_MADRID = ZoneInfo(SCHEDULER_TIMEZONE)
_MONTHS = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def week_label(window: WeekWindow) -> str:
    """«16–22 de noviembre» o «26 de noviembre – 2 de diciembre»."""
    start, end = window.first_day, window.last_day
    if start.month == end.month:
        return f"{start.day}–{end.day} de {_MONTHS[end.month]}"
    return f"{start.day} de {_MONTHS[start.month]} – {end.day} de {_MONTHS[end.month]}"


def _deal_block(position: int, deal, site_url: str) -> str:
    price = float(deal.current_price)
    previous = float(deal.previous_price) if deal.previous_price else None
    discount = deal.discount_percentage
    if not discount and previous and previous > price:
        discount = round((1 - price / previous) * 100)
    line = f"💶 {_format_price_es(price)} €"
    if previous and previous > price:
        line += f" (antes {_format_price_es(previous)} €)"
    if discount:
        line += f" | -{discount} %"
    link = deal.affiliate_url or f"{site_url.rstrip('/')}/chollo/{deal.slug}"
    return f"🍄 {position}. {deal.title}\n{line}\n🛒 {link}\n\n"


def build_weekly_digest(deals: list, window: WeekWindow, site_url: str) -> tuple[str | None, int]:
    """Texto del resumen para Telegram y cuántos chollos lleva (None, 0 si no
    hay). Si no caben todos en un mensaje, se corta la lista (nunca un chollo
    a medias)."""
    if not deals:
        return None, 0
    header = f"📅 Los chollos de la semana · {week_label(window)}\n\n"
    footer = f"🔗 {LINK_TEXT}\n\n"
    body = ""
    included = 0
    for deal in deals:
        block = _deal_block(included + 1, deal, site_url)
        if len(header) + len(body) + len(block) + len(footer) > MAX_TEXT_LENGTH:
            break
        body += block
        included += 1
    return header + body + footer, included


def whatsapp_version(telegram_text: str) -> str:
    """La versión WhatsApp de los posts, con la cabecera en negrita."""
    text = to_whatsapp_text(telegram_text)
    first, _, rest = text.partition("\n")
    return f"*{first}*\n{rest}" if first else text


@dataclass
class WeeklyDigest:
    telegram_text: str | None
    whatsapp_text: str | None
    count: int
    # Los chollos que van en el mensaje, en orden (para el collage).
    deals: list = field(default_factory=list)
    window: WeekWindow | None = None


# Tiempo máximo para bajar todas las fotos del collage (en paralelo): una tienda
# lenta deja su hueco con «Sin imagen» en vez de retrasar el resumen.
COLLAGE_DOWNLOAD_SECONDS = 25


def _download_all(urls: list[str | None], download: Callable[[str], bytes | None]) -> list[bytes | None]:
    pool = ThreadPoolExecutor(max_workers=max(1, len(urls)))
    futures = [pool.submit(download, url) if url else None for url in urls]
    done, _ = wait([f for f in futures if f is not None], timeout=COLLAGE_DOWNLOAD_SECONDS)
    pool.shutdown(wait=False, cancel_futures=True)
    images: list[bytes | None] = []
    for future in futures:
        try:
            images.append(future.result() if future is not None and future in done else None)
        except Exception:
            images.append(None)
    return images


def collage_items(deals: list, download: Callable[[str], bytes | None]) -> list[CollageItem]:
    images = _download_all([deal.image_url for deal in deals], download)
    items = []
    for position, (deal, image) in enumerate(zip(deals, images), start=1):
        price = float(deal.current_price)
        previous = float(deal.previous_price) if deal.previous_price else None
        discount = deal.discount_percentage
        if not discount and previous and previous > price:
            discount = round((1 - price / previous) * 100)
        items.append(CollageItem(position, image, f"{_format_price_es(price)} €", discount or None))
    return items


def build_digest_collage(digest: "WeeklyDigest", download: Callable[[str], bytes | None]) -> bytes | None:
    """JPEG con la foto y el número de cada chollo del resumen (None si no hay)."""
    if not digest.deals or digest.window is None:
        return None
    subtitle = f"{week_label(digest.window)}  ·  buenchollotech.com"
    return build_collage(collage_items(digest.deals, download), "LOS CHOLLOS DE LA SEMANA", subtitle)


class WeeklyDigestService:
    def __init__(
        self,
        deal_repo,
        bot,
        build_entities: Callable[[str], list[dict]],
        admin_chat_id: str,
        site_url: str,
        guard=None,
    ):
        self.deal_repo = deal_repo
        self.bot = bot
        self.build_entities = build_entities
        self.admin_chat_id = admin_chat_id
        self.site_url = site_url
        self.guard = guard

    async def _publishable(self, deal) -> bool:
        """Los chollos de redes de afiliación deben seguir cumpliendo sus reglas
        (programa aprobado, datos no caducados…), como en `/telegram/notify`."""
        if self.guard is None:
            return True
        from app.modules.deals.application.deal_service import _GUARD_FIELDS

        data = {column: getattr(deal, column, None) for column in _GUARD_FIELDS}
        data["status"] = "active"
        if not needs_network_rules(data):
            return True
        blockers = await self.guard.blockers_for(data)
        if blockers:
            logger.info("Resumen semanal: se omite %s (%s)", getattr(deal, "slug", "?"), ", ".join(blockers))
        return not blockers

    async def preview(self, now: datetime | None = None) -> WeeklyDigest:
        window = week_window(now or datetime.now(timezone.utc))
        candidates = await self.deal_repo.get_top_discount_active_since(window.since, limit=_CANDIDATES)
        deals = []
        for deal in candidates:
            if await self._publishable(deal):
                deals.append(deal)
            if len(deals) == WEEKLY_DIGEST_LIMIT:
                break
        text, count = build_weekly_digest(deals, window, self.site_url)
        return WeeklyDigest(text, whatsapp_version(text) if text else None, count, deals[:count], window)

    def collage(self, digest: WeeklyDigest) -> bytes | None:
        try:
            return build_digest_collage(digest, self.bot.download_image)
        except Exception:
            logger.exception("No se pudo generar el collage del resumen semanal")
            return None

    def send(self, digest: WeeklyDigest) -> bool:
        """Envía al canal Admin el collage, el texto de Telegram y el de WhatsApp.
        Devuelve si salió el texto de Telegram (un fallo del collage no lo impide).
        El collage va primero para que el canal se lea de arriba abajo; si
        Telegram rechazara después el texto, el collage quedaría solo (raro)."""
        if not digest.telegram_text or not self.admin_chat_id:
            return False
        image = self.collage(digest)
        if image and not self.bot.send_photo_bytes(image, chat_id=self.admin_chat_id):
            logger.warning("No se pudo enviar el collage del resumen semanal: %s", getattr(self.bot, "last_error", None))
        sent = self.bot.send_preformatted(
            text=digest.telegram_text,
            entities=self.build_entities(digest.telegram_text),
            image_url=None,
            chat_id=self.admin_chat_id,
        )
        if not sent:
            logger.error("Telegram rechazó el resumen semanal: %s", getattr(self.bot, "last_error", None))
            return False
        send_whatsapp_copy(
            self.bot,
            chat_id=self.admin_chat_id,
            telegram_text=digest.telegram_text,
            whatsapp_text=digest.whatsapp_text,
        )
        return True


def build_weekly_digest_service(session, settings: Settings) -> WeeklyDigestService:
    from app.modules.affiliates.application.programs import PublicationGuard
    from app.modules.affiliates.infrastructure.repository import AffiliateRepository
    from app.modules.deals.infrastructure.repository import DealRepository
    from app.modules.telegram.application.post_generator import TelegramPostGenerator
    from app.modules.telegram.infrastructure.telegram_bot import TelegramBot

    generator = TelegramPostGenerator(settings=settings)
    return WeeklyDigestService(
        deal_repo=DealRepository(session),
        bot=TelegramBot(settings.telegram_bot_token),
        build_entities=generator.build_entities,
        admin_chat_id=settings.telegram_admin_channel_id,
        site_url=settings.public_site_url,
        guard=PublicationGuard(AffiliateRepository(session)),
    )


async def _run(settings: Settings) -> bool:
    if not settings.weekly_digest_enabled:
        logger.info("Resumen semanal desactivado (WEEKLY_DIGEST_ENABLED=false)")
        return False
    if not settings.telegram_admin_channel_id or not settings.telegram_bot_token:
        logger.warning("Resumen semanal sin canal Admin o token de Telegram: no se envía")
        return False
    async with job_session(settings) as session:
        service = build_weekly_digest_service(session, settings)
        digest = await service.preview()
    if not digest.telegram_text:
        logger.info("Resumen semanal: ningún chollo activo de la semana; no se envía")
        return False
    sent = service.send(digest)
    logger.info("Resumen semanal enviado al canal Admin: %s (%d chollos)", sent, digest.count)
    return sent


def run_weekly_deals_digest(settings: Settings) -> bool:
    """Job de APScheduler (síncrono): domingos a las 22:30, hora de Madrid."""
    return asyncio.run(_run(settings))
