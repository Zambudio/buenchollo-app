"""Encola en Facebook el chollo que acaba de salir en Telegram.

Solo si el canal de destino está en `FACEBOOK_CHANNELS` (`goes_to_facebook`).
La imagen es la misma tarjeta de oferta; si el post salió con la foto original,
se reconvierte a JPEG (Facebook admite cualquier proporción). Nunca lanza:
Telegram ya está publicado.
"""

from __future__ import annotations

import asyncio
import io
import logging
from collections.abc import Callable

from PIL import Image, ImageOps

from app.core.config import Settings
from app.modules.facebook.domain.models import FacebookPost
from app.modules.facebook.domain.text import to_facebook_text
from app.modules.facebook.infrastructure.repository import FacebookRepository

logger = logging.getLogger(__name__)

MAX_SIDE = 2048
MAX_SOURCE_PIXELS = 24_000_000


def to_jpeg(raw: bytes | None) -> bytes | None:
    """Foto del producto en JPEG (como mucho 2048 px de lado), con fondo blanco."""
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
            canvas.save(out, format="JPEG", quality=90, optimize=True)
            return out.getvalue()
    except Exception:
        logger.warning("Facebook: la foto del producto no se puede leer")
        return None


def goes_to_facebook(channel_id: str | None, settings: Settings) -> bool:
    """Si un chollo publicado en ese canal de Telegram va también a Facebook
    (`FACEBOOK_CHANNELS`: `main` y/o `admin`)."""
    target = str(channel_id or "").strip()
    if not target:
        return False
    ids = {
        "main": (settings.telegram_main_channel_id or "").strip(),
        "admin": (settings.telegram_admin_channel_id or "").strip(),
    }
    kinds = {k.strip().lower() for k in (settings.facebook_channels or "").split(",")}
    return any(ids.get(kind) == target for kind in kinds if ids.get(kind))


async def queue_facebook_post(
    session,
    settings: Settings,
    *,
    deal_id: str | None,
    telegram_text: str | None,
    card: bytes | None,
    image_url: str | None,
    download: Callable[[str], bytes | None] | None = None,
) -> bool:
    """Deja el post en la cola (`facebook_posts`). True si se encoló."""
    if not settings.facebook_enabled or not telegram_text:
        return False
    try:
        image = card
        if image is None and image_url and download is not None:
            image = await asyncio.to_thread(lambda: to_jpeg(download(image_url)))
        if not image:
            logger.warning("Facebook: chollo sin imagen utilizable; no se publica allí")
            return False
        message = to_facebook_text(telegram_text, settings.facebook_hashtags, settings.facebook_disclosure)
        async with session.begin_nested():
            await FacebookRepository(session).add_post(
                FacebookPost(deal_id=str(deal_id) if deal_id else None, message=message, image=image)
            )
        return True
    except Exception:
        logger.exception("Facebook: no se pudo encolar la publicación (Telegram ya está publicado)")
        return False
