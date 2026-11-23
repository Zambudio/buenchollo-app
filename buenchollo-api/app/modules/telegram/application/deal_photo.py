"""Foto de cada publicación de chollo en Telegram.

Punto único para todos los envíos de un chollo con foto (panel, publicaciones
programadas, republicación al canal Admin y copia de WhatsApp): intenta la
tarjeta «Simple claro» (`deal_card.py`) y, si no se puede, publica la foto del
producto tal cual, como siempre. Nunca bloquea una publicación:

- sin precio anterior, o anterior ≤ actual → foto original;
- la foto no se descarga o no se puede leer → foto original;
- falla la composición → foto original;
- Telegram rechaza la tarjeta → se reintenta con la foto original;
- `DEAL_CARD_ENABLED=false` → foto original.

Si Telegram no responde al enviar la tarjeta (tiempo agotado), la foto pudo
llegar igualmente: se da por enviada y no se reintenta, para no duplicar un
post en el canal público.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from decimal import Decimal

from app.core.config import get_settings
from app.modules.telegram.application.deal_card import DealCardData, build_deal_card
from app.modules.telegram.application.post_generator import strip_price_lines, with_price_lines

logger = logging.getLogger(__name__)

Number = float | Decimal | int | None


def store_name_of(deal) -> str | None:
    """Nombre de la tienda de un chollo (`Deal` con `store` cargada), o None."""
    name = getattr(getattr(deal, "store", None), "name", None)
    return name if isinstance(name, str) and name.strip() else None


def card_data(
    current_price: Number, previous_price: Number, store: str | None, discount: Number = None
) -> DealCardData | None:
    """Datos de la tarjeta, o None si falta o no se entiende el precio actual.

    `discount` es el porcentaje que lleva el texto del post: la insignia muestra
    el mismo (si no viene o no es positivo, se calcula de los precios)."""
    try:
        if current_price is None:
            return None
        pct = int(discount) if discount is not None and int(discount) > 0 else None
        return DealCardData(
            current_price=float(current_price),
            previous_price=float(previous_price) if previous_price is not None else None,
            store=store.strip() if isinstance(store, str) else "",
            discount=pct,
        )
    except (TypeError, ValueError):
        return None


def deal_card_data(deal) -> DealCardData | None:
    """Datos de la tarjeta de un chollo (`Deal`) con su tienda ya cargada."""
    return card_data(
        getattr(deal, "current_price", None),
        getattr(deal, "previous_price", None),
        store_name_of(deal),
        getattr(deal, "discount_percentage", None),
    )


def render_card(bot, image_url: str | None, data: DealCardData | None) -> bytes | None:
    """Tarjeta JPEG para `image_url`, o None (se publicará la foto original)."""
    if not image_url or data is None or not get_settings().deal_card_enabled:
        return None
    try:
        image = bot.download_image(image_url)
        if not image:
            logger.info("Tarjeta de oferta: no se pudo descargar la foto; se usa la original")
            return None
        return build_deal_card(data, image)
    except Exception:
        logger.warning("Tarjeta de oferta no disponible; se usa la foto original", exc_info=True)
        return None


def caption_for(text: str, *, card_sent: bool, data: DealCardData | None) -> str:
    """Texto del post según la imagen: con tarjeta, sin las líneas de precio y
    ahorro (ya están en la imagen); sin ella, con esas líneas aunque la plantilla
    las omitiera, para que ningún post salga sin precio."""
    if card_sent:
        return strip_price_lines(text)
    if data is None:
        return text
    return with_price_lines(text, data.current_price, data.previous_price, data.discount)


def send_deal_post(
    bot,
    *,
    text: str,
    entities_for: Callable[[str], list[dict]],
    image_url: str | None,
    chat_id: str | None,
    card: bytes | None,
    data: DealCardData | None = None,
) -> str | None:
    """Publica el post con la tarjeta si la hay; si no, con la foto original.

    Devuelve el texto que salió (para registrarlo y para la copia de WhatsApp)
    o None si no se pudo publicar. `entities_for` calcula las entidades del
    texto final (cambia según lleve o no las líneas de precio)."""
    if card:
        caption = caption_for(text, card_sent=True, data=data)
        if bot.send_photo_bytes(card, chat_id=chat_id, caption=caption, entities=entities_for(caption)):
            return caption
        if getattr(bot, "last_delivery_unknown", False):
            logger.warning("Telegram no respondió al enviar la tarjeta; se da por enviada para no duplicar")
            return caption
        logger.warning("Telegram rechazó la tarjeta (%s); se envía la foto original", getattr(bot, "last_error", None))
    caption = caption_for(text, card_sent=False, data=data)
    if bot.send_preformatted(text=caption, entities=entities_for(caption), image_url=image_url, chat_id=chat_id):
        return caption
    return None
