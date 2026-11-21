"""«Los chollos de la semana»: resumen de los domingos a las 22:30 (Madrid).

Toma los chollos activos publicados (o reactivados) en la semana (de lunes a
domingo, en hora de Madrid) con más descuento y envía al canal Admin de
Telegram dos mensajes: la versión de Telegram (emojis premium y negrita, como
los posts normales) y la versión de WhatsApp, para que el admin la reenvíe al
canal oficial y la copie al Canal de WhatsApp a mano. Nunca publica
directamente en el canal público.

Un chollo de Awin/Tradedoubler solo entra si sigue cumpliendo las reglas de
publicación (las mismas que comprueba `/telegram/notify`).
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.jobs import SCHEDULER_TIMEZONE, job_session
from app.modules.affiliates.application.programs import needs_network_rules
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


@dataclass(frozen=True)
class WeekWindow:
    first_day: date
    last_day: date
    since: datetime  # medianoche (Madrid) del primer día


def week_window(now: datetime) -> WeekWindow:
    """Los 7 días naturales que acaban hoy (hora de Madrid). Etiqueta y consulta
    usan la misma ventana: un chollo no sale en dos resúmenes seguidos."""
    last_day = now.astimezone(_MADRID).date()
    first_day = last_day - timedelta(days=6)
    return WeekWindow(first_day, last_day, datetime.combine(first_day, time.min, tzinfo=_MADRID))


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
        return WeeklyDigest(text, whatsapp_version(text) if text else None, count)

    def send(self, digest: WeeklyDigest) -> bool:
        """Envía las dos versiones al canal Admin. Devuelve si salió la de Telegram."""
        if not digest.telegram_text or not self.admin_chat_id:
            return False
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
