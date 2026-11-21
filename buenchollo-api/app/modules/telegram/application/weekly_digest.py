"""«Los chollos de la semana»: resumen de los domingos a las 22:30 (Madrid).

Toma los chollos activos publicados (o reactivados) en los 7 días naturales
anteriores (hora de Madrid) con más descuento y envía al canal Admin de
Telegram dos mensajes: la publicación de Telegram (un collage vertical con la
foto, el número, el precio y el descuento de cada chollo, y el texto con los
enlaces como pie de foto, como los chollos) y la versión de WhatsApp con el
texto completo, para que el admin la reenvíe al canal oficial y la copie al
Canal de WhatsApp a mano. Nunca publica directamente en el canal público.

La lista es la de `deals.application.weekly_top` (la misma que el lateral
«Top de la semana» de la web), que ya deja fuera los chollos de Awin/Tradedoubler
que no cumplen las reglas de publicación.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, wait
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.config import Settings
from app.core.jobs import job_session
from app.modules.deals.application.weekly_top import weekly_top
from app.modules.deals.domain.week import WeekWindow, week_window
from app.modules.telegram.application.weekly_collage import CollageItem, build_collage
from app.modules.telegram.application.post_generator import LINK_TEXT, _format_price_es
from app.modules.telegram.application.whatsapp_copy import send_whatsapp_copy
from app.modules.telegram.application.whatsapp_formatter import to_whatsapp_text

logger = logging.getLogger(__name__)

WEEKLY_DIGEST_LIMIT = 10
# Telegram admite 4096 caracteres por mensaje; se deja margen.
MAX_TEXT_LENGTH = 3900

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


# El número del top en emoji (el mismo que lleva cada tarjeta del collage).
_KEYCAPS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


def number_emoji(position: int) -> str:
    return _KEYCAPS[position - 1] if 1 <= position <= len(_KEYCAPS) else f"{position}."


def _discount(deal) -> int | None:
    price = float(deal.current_price)
    previous = float(deal.previous_price) if deal.previous_price else None
    discount = deal.discount_percentage
    if not discount and previous and previous > price:
        discount = round((1 - price / previous) * 100)
    return discount or None


def _shorten(title: str, max_chars: int | None) -> str:
    if max_chars is None or len(title) <= max_chars:
        return title
    return title[: max_chars - 1].rstrip(" ,.-(") + "…"


def _deal_block(
    position: int,
    deal,
    site_url: str,
    *,
    with_previous: bool = True,
    with_price: bool = True,
    title_max: int | None = None,
) -> str:
    price = float(deal.current_price)
    previous = float(deal.previous_price) if deal.previous_price else None
    discount = _discount(deal)
    link = deal.affiliate_url or f"{site_url.rstrip('/')}/chollo/{deal.slug}"
    block = f"{number_emoji(position)} {_shorten(deal.title, title_max)}\n"
    if with_price:
        line = f"💶 {_format_price_es(price)} €"
        if discount:
            line += f" | -{discount} %"
        if with_previous and previous and previous > price:
            line += f" | antes: {_format_price_es(previous)} €"
        block += line + "\n"
    return block + f"🛒 {link}\n\n"


def _header(window: WeekWindow) -> str:
    return f"📅 Los chollos de la semana · {week_label(window)}\n\n"


_FOOTER = f"🔗 {LINK_TEXT}\n\n"


def build_weekly_digest(deals: list, window: WeekWindow, site_url: str) -> tuple[str | None, int]:
    """Texto completo del resumen (versión WhatsApp y respaldo sin imagen) y
    cuántos chollos lleva (None, 0 si no hay). Si no caben todos en un mensaje,
    se corta la lista (nunca un chollo a medias)."""
    if not deals:
        return None, 0
    header = _header(window)
    body = ""
    included = 0
    for deal in deals:
        block = _deal_block(included + 1, deal, site_url)
        if len(header) + len(body) + len(block) + len(_FOOTER) > MAX_TEXT_LENGTH:
            break
        body += block
        included += 1
    return header + body + _FOOTER, included


# Telegram limita a 1024 caracteres (UTF-16) el texto que acompaña a una foto.
CAPTION_LIMIT = 1024
# De más a menos completo: el pie se va recortando hasta caber. Primero se
# acortan los títulos (el collage ya identifica cada producto) para conservar el
# precio anterior; después se quita el «antes» y, en último caso, el precio.
# Los enlaces siempre van enteros.
_CAPTION_LEVELS = (
    {"with_previous": True, "with_price": True, "title_max": None},
    {"with_previous": True, "with_price": True, "title_max": 45},
    {"with_previous": True, "with_price": True, "title_max": 32},
    {"with_previous": True, "with_price": True, "title_max": 24},
    {"with_previous": True, "with_price": True, "title_max": 20},
    {"with_previous": True, "with_price": True, "title_max": 16},
    {"with_previous": False, "with_price": True, "title_max": 32},
    {"with_previous": False, "with_price": True, "title_max": 24},
    {"with_previous": False, "with_price": False, "title_max": 24},
)


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def build_caption(deals: list, window: WeekWindow, site_url: str) -> tuple[str | None, int]:
    """Texto para publicar junto al collage, en un solo mensaje (como los
    chollos): el más completo que quepa en el pie de foto de Telegram."""
    if not deals:
        return None, 0
    for count in range(len(deals), 0, -1):
        for level in _CAPTION_LEVELS:
            body = "".join(_deal_block(i, deal, site_url, **level) for i, deal in enumerate(deals[:count], 1))
            text = (_header(window) + body + _FOOTER).rstrip()
            if _utf16_len(text) <= CAPTION_LIMIT:
                return text, count
    return None, 0


def whatsapp_version(telegram_text: str) -> str:
    """La versión WhatsApp de los posts, con la cabecera y los títulos en negrita."""
    lines = to_whatsapp_text(telegram_text).split("\n")
    for i, line in enumerate(lines):
        for emoji in _KEYCAPS:
            if line.startswith(f"{emoji} "):
                lines[i] = f"{emoji} *{line[len(emoji) + 1:].replace('*', '')}*"
                break
    if lines and lines[0]:
        lines[0] = f"*{lines[0]}*"
    return "\n".join(lines)


@dataclass
class WeeklyDigest:
    # Texto de la publicación de Telegram: el pie de foto del collage (máx. 1024
    # caracteres) o, si no cabe ni un chollo, el texto completo.
    telegram_text: str | None
    whatsapp_text: str | None
    count: int
    # Los chollos que van en el mensaje, en orden (para el collage).
    deals: list = field(default_factory=list)
    window: WeekWindow | None = None
    # Texto completo (con precio anterior y títulos enteros): respaldo sin imagen.
    full_text: str | None = None
    # Si `telegram_text` cabe como pie de foto del collage.
    caption_fits: bool = True


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
        price = f"{_format_price_es(float(deal.current_price))} €"
        items.append(CollageItem(position, image, price, _discount(deal), deal.title))
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

    async def preview(self, now: datetime | None = None) -> WeeklyDigest:
        now = now or datetime.now(timezone.utc)
        window = week_window(now)
        # El mismo ranking que el lateral «Top de la semana» de la web.
        deals = await weekly_top(self.deal_repo, self.guard, WEEKLY_DIGEST_LIMIT, now)
        caption, count = build_caption(deals, window, self.site_url)
        # El collage, el pie, el texto completo y WhatsApp llevan los mismos chollos.
        full, full_count = build_weekly_digest(deals[:count] if caption else deals, window, self.site_url)
        if caption is None:
            logger.warning("Resumen semanal: el texto no cabe como pie de foto; irá aparte del collage")
            count = full_count
        return WeeklyDigest(
            caption or full,
            whatsapp_version(full) if full else None,
            count,
            deals[:count],
            window,
            full_text=full,
            caption_fits=caption is not None,
        )

    def collage(self, digest: WeeklyDigest) -> bytes | None:
        try:
            return build_digest_collage(digest, self.bot.download_image)
        except Exception:
            logger.exception("No se pudo generar el collage del resumen semanal")
            return None

    def send(self, digest: WeeklyDigest) -> bool:
        """Envía al canal Admin la publicación de Telegram (collage con el texto
        como pie de foto, en un solo mensaje, como los chollos) y después la
        versión de WhatsApp. Si el collage falla, sale el texto completo sin
        imagen. Devuelve si salió la publicación de Telegram."""
        if not digest.telegram_text or not self.admin_chat_id:
            return False
        image = self.collage(digest)
        sent = False
        if image and digest.caption_fits:
            sent = self.bot.send_photo_bytes(
                image,
                chat_id=self.admin_chat_id,
                caption=digest.telegram_text,
                entities=self.build_entities(digest.telegram_text),
            )
            if not sent and getattr(self.bot, "last_delivery_unknown", False):
                # Sin respuesta (p. ej. tiempo agotado): Telegram pudo haberla
                # publicado. No se reenvía en texto para no duplicar el resumen.
                logger.error("Resumen semanal: no se sabe si llegó la publicación; no se reenvía")
                return False
            if not sent:
                logger.warning("No se pudo enviar el collage del resumen: %s", getattr(self.bot, "last_error", None))
        elif image:
            # El texto no cabe como pie: collage suelto y después el texto completo.
            self.bot.send_photo_bytes(image, chat_id=self.admin_chat_id)
        if not sent:
            text = digest.full_text or digest.telegram_text
            sent = self.bot.send_preformatted(
                text=text,
                entities=self.build_entities(text),
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
