"""Encola en Instagram el chollo que acaba de salir en el canal principal.

Lo llaman el panel (`/v1/telegram/notify`) y las publicaciones programadas,
solo si el canal de destino está en `INSTAGRAM_CHANNELS` (`goes_to_instagram`).
La imagen es la misma tarjeta de oferta (1200×800, encaja en el feed); si el
post salió con la foto original, se centra esa foto en un lienzo blanco del
mismo tamaño (Instagram rechaza proporciones extremas). Nunca lanza: Telegram
ya está publicado.
"""

from __future__ import annotations

import asyncio
import io
import logging
from collections.abc import Callable

from PIL import Image, ImageOps

from app.core.config import Settings
from app.modules.instagram.domain.caption import to_instagram_caption
from app.modules.instagram.domain.models import InstagramPost
from app.modules.instagram.infrastructure.repository import InstagramRepository

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1200, 800  # igual que la tarjeta de oferta
_MARGIN = 40
MAX_SOURCE_PIXELS = 24_000_000


def fit_photo(raw: bytes | None) -> bytes | None:
    """Foto del producto centrada en un lienzo blanco 1200×800, en JPEG."""
    if not raw:
        return None
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.width * img.height > MAX_SOURCE_PIXELS:
                return None
            box = (WIDTH - 2 * _MARGIN, HEIGHT - 2 * _MARGIN)
            img.draft("RGB", box)
            img = ImageOps.exif_transpose(img).convert("RGBA")
            img = ImageOps.contain(img, box, Image.LANCZOS)
            canvas = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
            canvas.paste(img, ((WIDTH - img.width) // 2, (HEIGHT - img.height) // 2), img)
            out = io.BytesIO()
            canvas.save(out, format="JPEG", quality=90, optimize=True)
            return out.getvalue()
    except Exception:
        logger.warning("Instagram: la foto del producto no se puede leer")
        return None


def goes_to_instagram(channel_id: str | None, settings: Settings) -> bool:
    """Si un chollo publicado en ese canal de Telegram va también a Instagram.

    `INSTAGRAM_CHANNELS` dice qué canales cuentan: `main` (canal público) y/o
    `admin` (canal Admin, donde hoy salen las publicaciones programadas)."""
    target = str(channel_id or "").strip()
    if not target:
        return False
    ids = {
        "main": (settings.telegram_main_channel_id or "").strip(),
        "admin": (settings.telegram_admin_channel_id or "").strip(),
    }
    kinds = {k.strip().lower() for k in (settings.instagram_channels or "").split(",")}
    return any(ids.get(kind) == target for kind in kinds if ids.get(kind))


async def queue_instagram_post(
    session,
    settings: Settings,
    *,
    deal_id: str | None,
    telegram_text: str | None,
    card: bytes | None,
    image_url: str | None,
    download: Callable[[str], bytes | None] | None = None,
) -> bool:
    """Deja el post en la cola (`instagram_posts`). True si se encoló."""
    if not settings.instagram_enabled or not telegram_text:
        return False
    try:
        image = card
        if image is None and image_url and download is not None:
            image = await asyncio.to_thread(lambda: fit_photo(download(image_url)))
        if not image:
            logger.warning("Instagram: chollo sin imagen utilizable; no se publica allí")
            return False
        caption = to_instagram_caption(telegram_text, settings.instagram_hashtags)
        async with session.begin_nested():
            await InstagramRepository(session).add_post(
                InstagramPost(deal_id=str(deal_id) if deal_id else None, caption=caption, image=image)
            )
        return True
    except Exception:
        logger.exception("Instagram: no se pudo encolar la publicación (Telegram ya está publicado)")
        return False
