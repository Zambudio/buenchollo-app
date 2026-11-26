"""Encola en el Canal de WhatsApp el chollo que acaba de salir en Telegram.

Lo llama el suscriptor de `DealPostPublished` solo si el canal de Telegram está
en `WHATSAPP_CHANNELS` (`goes_to_whatsapp`). La imagen es la misma tarjeta de
oferta; si el post salió con la foto original, se usa esa foto en JPEG. Nunca
lanza: Telegram ya está publicado.
"""

from __future__ import annotations

import asyncio
import io
import logging
import random
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageOps

from app.core.config import Settings
from app.modules.whatsapp.domain.models import WhatsAppPost
from app.modules.whatsapp.domain.text import channel_text
from app.modules.whatsapp.infrastructure.repository import WhatsAppRepository

logger = logging.getLogger(__name__)

MAX_SIDE = 1600
MAX_SOURCE_PIXELS = 24_000_000
# El mismo chollo no se repite en el Canal en este plazo (p. ej. si sale en el
# canal principal y en el Admin, o si se reenvía desde el panel).
DEDUP_WINDOW = timedelta(hours=24)
# Margen aleatorio entre Telegram y WhatsApp: no sale todo «al segundo».
DELAY_SECONDS = (45, 180)


def to_jpeg(raw: bytes | None) -> bytes | None:
    """Foto del producto en JPEG (lado mayor ≤ 1600 px, fondo blanco)."""
    if not raw:
        return None
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.width * img.height > MAX_SOURCE_PIXELS:
                return None
            img.draft("RGB", (MAX_SIDE, MAX_SIDE))
            img = ImageOps.exif_transpose(img).convert("RGBA")
            img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            canvas = Image.new("RGB", img.size, (255, 255, 255))
            canvas.paste(img, (0, 0), img)
            out = io.BytesIO()
            canvas.save(out, format="JPEG", quality=88, optimize=True)
            return out.getvalue()
    except Exception:
        logger.warning("WhatsApp: la foto del producto no se puede leer; saldrá solo el texto")
        return None


def goes_to_whatsapp(channel_id: str | None, settings: Settings) -> bool:
    """Si un chollo publicado en ese canal de Telegram va también al Canal de
    WhatsApp. `WHATSAPP_CHANNELS`: `main` (canal público) y/o `admin` (canal
    Admin, donde salen las publicaciones programadas)."""
    target = str(channel_id or "").strip()
    if not target:
        return False
    ids = {
        "main": (settings.telegram_main_channel_id or "").strip(),
        "admin": (settings.telegram_admin_channel_id or "").strip(),
    }
    kinds = {k.strip().lower() for k in (settings.whatsapp_channels or "").split(",")}
    return any(ids.get(kind) == target for kind in kinds if ids.get(kind))


async def queue_whatsapp_post(
    session,
    settings: Settings,
    *,
    deal_id: str | None,
    telegram_text: str | None,
    whatsapp_text: str | None = None,
    card: bytes | None,
    image_url: str | None,
    download: Callable[[str], bytes | None] | None = None,
    now: datetime | None = None,
    strip_prices: bool | None = None,
) -> bool:
    """Deja el post en la cola (`whatsapp_posts`). True si se encoló."""
    if not settings.whatsapp_enabled or not (telegram_text or whatsapp_text):
        return False
    now = now or datetime.now(timezone.utc)
    try:
        repo = WhatsAppRepository(session)
        if deal_id and await repo.has_recent_for_deal(str(deal_id), now - DEDUP_WINDOW):
            logger.info("WhatsApp: el chollo %s ya está en el Canal (o en cola); no se repite", deal_id)
            return False
        image = card
        if image is None and image_url and download is not None:
            image = await asyncio.to_thread(lambda: to_jpeg(download(image_url)))
        with_card = card is not None if strip_prices is None else strip_prices
        text = channel_text(telegram_text, edited=whatsapp_text, with_card=with_card)
        if not text:
            return False
        async with session.begin_nested():
            await repo.add_post(
                WhatsAppPost(
                    deal_id=str(deal_id) if deal_id else None,
                    text=text,
                    image=image,
                    created_at=now,
                    not_before=now + timedelta(seconds=random.randint(*DELAY_SECONDS)),
                )
            )
        return True
    except Exception:
        logger.exception("WhatsApp: no se pudo encolar la publicación (Telegram ya está publicado)")
        return False
