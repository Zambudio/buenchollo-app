"""Aviso al canal Admin de Telegram (y alertas de usuario) cuando un chollo
vuelve a estar en oferta o baja de precio tras la revisión diaria. Nunca
publica en el canal oficial: Pedro comprueba la oferta y decide si la reenvía.

Se envían dos mensajes: el aviso (qué ha pasado y el precio de antes) y la
última publicación de Telegram del chollo con el precio corregido (o una nueva
si nunca se publicó), lista para reenviar.

Antispam: un aviso por chollo cada 7 días, salvo que el precio sea menor que
el del último aviso. Además, solo se avisa al canal Admin si el chollo se
publicó hace al menos 10 días (última publicación registrada en Telegram, en
cualquier canal, o, si
nunca se publicó allí, su alta en la web): reenviar algo de hace pocos días es
repetir contenido. Las alertas de usuario no dependen de esa antigüedad. Un
fallo de Telegram nunca deshace lo aplicado.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from starlette.concurrency import run_in_threadpool

from app.modules.telegram.application.post_generator import _format_price_es
from app.modules.telegram.application.deal_photo import deal_card_data, render_card, send_deal_post, store_name_of
from app.modules.telegram.application.whatsapp_copy import send_whatsapp_copy
from app.modules.telegram.application.reprice import reprice_publication_text

logger = logging.getLogger(__name__)

ADMIN_COOLDOWN = timedelta(days=7)
REPOST_MIN_AGE = timedelta(days=10)
_NOTIFIABLE = ("reactivated", "price_dropped")


@dataclass(frozen=True)
class OfferEvent:
    deal_id: str
    kind: str  # reactivated | price_dropped
    old_price: Decimal | None  # precio de la oferta anterior


@dataclass(frozen=True)
class LastPublication:
    at: datetime
    on_telegram: bool  # False: nunca se publicó en Telegram; `at` es el alta en la web


def is_old_enough(last: LastPublication, now: datetime) -> bool:
    return now - last.at >= REPOST_MIN_AGE


def should_notify(
    notified_at: datetime | None, notified_price: Decimal | None, price: Decimal, now: datetime
) -> bool:
    if notified_at is None or notified_price is None:
        return True
    if now - notified_at >= ADMIN_COOLDOWN:
        return True
    return Decimal(str(price)) < Decimal(str(notified_price))


def notifiable_events(run) -> list[OfferEvent]:
    return [
        OfferEvent(item.deal_id_snapshot, item.transition, getattr(item, "old_price", None))
        for item in run.items
        if item.transition in _NOTIFIABLE
    ]


def _eur(value) -> str:
    return f"{_format_price_es(float(value))} €"


def _published_line(last: LastPublication, now: datetime) -> str:
    days = (now - last.at).days
    where = "Última publicación en Telegram" if last.on_telegram else "Publicado en la web (nunca en Telegram)"
    return f"🗓️ {where}: {last.at:%d/%m/%Y} (hace {days} días)"


def build_admin_message(deal, event: OfferEvent, site_url: str, last: LastPublication, now: datetime) -> str:
    if event.kind == "price_dropped":
        lines = ["📉 Ha bajado de precio", deal.title]
        price = f"💶 Ahora {_eur(deal.current_price)}"
        if event.old_price is not None:
            price += f" · antes {_eur(event.old_price)}"
    else:
        lines = ["🔁 Vuelve a estar en oferta", deal.title]
        price = f"💶 Ahora {_eur(deal.current_price)}"
        if event.old_price is not None:
            price += f" · la última vez que fue chollo: {_eur(event.old_price)}"
    lines.append(price)
    lines.append(_published_line(last, now))
    if deal.previous_price is not None:
        reference = f"🏷️ Referencia de la tienda: {_eur(deal.previous_price)}"
        if deal.discount_percentage:
            reference += f" (-{deal.discount_percentage} %)"
        lines.append(reference)
    lines += [
        f"🏪 {deal.store.name if deal.store else 'Tienda'}",
        f"🌐 {site_url.rstrip('/')}/chollo/{deal.slug}",
        "👇 Publicación con el precio corregido, lista para reenviar (comprueba antes que sigue siendo buena oferta)",
    ]
    return "\n".join(lines)


class ReactivationNotifier:
    def __init__(
        self, bot, admin_chat_id: str, matcher, deal_repo, site_url: str, *, publications, generator,
        whatsapp_copy: bool = True,
    ):
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        self.matcher = matcher
        self.deal_repo = deal_repo
        self.site_url = site_url
        self.publications = publications
        self.generator = generator
        # Copia «versión WhatsApp» al canal Admin; se apaga con el Canal automático.
        self.whatsapp_copy = whatsapp_copy

    async def notify(self, events: list[OfferEvent], now: datetime) -> int:
        """Devuelve cuántos avisos llegaron al canal Admin."""
        sent = 0
        for event in events:
            deal = await self.deal_repo.get_by_id(event.deal_id)
            if deal is None or deal.status != "active":
                continue
            if not should_notify(deal.admin_notified_at, deal.admin_notified_price, deal.current_price, now):
                continue
            await self.matcher.notify_matching_alerts(deal)
            if not self.admin_chat_id:
                logger.info("Cambio de oferta de %s sin canal Admin configurado: no se avisa", deal.slug)
                continue
            publication = await self._latest_publication(deal)
            last = (LastPublication(publication.sent_at, on_telegram=True) if publication is not None
                    else LastPublication(deal.created_at, on_telegram=False))
            if not is_old_enough(last, now):
                logger.info("Cambio de oferta de %s publicado hace menos de %d días: no se avisa",
                            deal.slug, REPOST_MIN_AGE.days)
                continue
            message = build_admin_message(deal, event, self.site_url, last, now)
            if not await self._call(self.bot.send_admin_notification, message, chat_id=self.admin_chat_id):
                continue
            deal.admin_notified_at = now
            deal.admin_notified_price = deal.current_price
            sent += 1
            await self._send_republishable(deal, publication, now)
        return sent

    async def _latest_publication(self, deal):
        """Si la consulta falla, se trata como nunca publicado en Telegram
        (cuenta el alta en la web) para no perder el aviso."""
        try:
            return await self.publications.latest_for_deal(deal.id)
        except Exception:
            logger.exception("No se pudo leer la última publicación de %s", deal.slug)
            return None

    async def _send_republishable(self, deal, publication, now: datetime) -> None:
        """Segundo mensaje; aislado para que un fallo en un chollo no deje sin
        aviso a los siguientes ni deshaga el antispam de los ya avisados."""
        try:
            text, image_url = self._republishable(deal, publication, now)
            store = store_name_of(deal)
            data = deal_card_data(deal)
        except Exception:
            logger.exception("No se pudo preparar la publicación corregida de %s", deal.slug)
            return
        # Tarjeta de oferta con el precio nuevo (si no se puede, la foto original).
        card = await run_in_threadpool(render_card, self.bot, image_url, data)
        try:
            sent_text = await run_in_threadpool(
                send_deal_post, self.bot, text=text,
                entities_for=lambda t: self.generator.build_entities(t, store_name=store),
                image_url=image_url, chat_id=self.admin_chat_id, card=card, data=data,
            )
        except Exception:
            logger.exception("Fallo enviando al canal Admin")
            sent_text = None
        if sent_text is None:
            logger.warning("No se pudo enviar al canal Admin la publicación corregida de %s", deal.slug)
            return
        if not self.whatsapp_copy:
            return
        await self._call(send_whatsapp_copy, self.bot, chat_id=self.admin_chat_id,
                         telegram_text=sent_text, image_url=image_url, image_bytes=card)

    def _republishable(self, deal, publication, now: datetime) -> tuple[str, str | None]:
        """Última publicación registrada con el precio corregido; si no existe (o
        no tiene el formato estándar), una publicación nueva."""
        if publication is not None:
            text = reprice_publication_text(
                publication.text,
                price=Decimal(str(deal.current_price)),
                previous_price=Decimal(str(deal.previous_price)) if deal.previous_price is not None else None,
                discount_pct=deal.discount_percentage,
                expires_at=deal.expires_at,
                now=now,
            )
            if text is not None:
                return text, publication.image_url or deal.image_url
        text = self.generator.generate_text(
            title=deal.title,
            current_price=float(deal.current_price),
            previous_price=float(deal.previous_price) if deal.previous_price is not None else None,
            discount_pct=deal.discount_percentage,
            description=deal.short_description,
            affiliate_url=deal.affiliate_url,
            expires_at=deal.expires_at.isoformat() if deal.expires_at else None,
        )
        return text, deal.image_url

    @staticmethod
    async def _call(fn, *args, **kwargs) -> bool:
        try:
            return bool(await run_in_threadpool(fn, *args, **kwargs))
        except Exception:
            logger.exception("Fallo enviando al canal Admin")
            return False
