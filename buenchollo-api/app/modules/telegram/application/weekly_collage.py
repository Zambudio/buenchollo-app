"""Collage del resumen semanal: una imagen con la foto de cada chollo y su
número del top, para identificar de un vistazo los enlaces del mensaje.

Usa Space Grotesk, la tipografía de la web (`app/assets/fonts`). Si no se
pudiera cargar, cae a la fuente escalable de Pillow (sin «€» ni «–»).
"""

import io
import logging
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1600, 900
HEADER = 128
PADDING = 26
GAP = 20
COLUMNS = 5

# Colores de la marca (tema oscuro de la web).
_NIGHT = (7, 10, 20)
_CARD = (255, 255, 255)
_TEXT = (15, 23, 42)
_MUTED = (100, 116, 139)
_CYAN = (34, 211, 238)
_ORANGE = (234, 88, 12)
_BADGE = (12, 18, 34)
_RULE = (16, 80, 96)  # cian al 35 % sobre el fondo

# Imágenes descargadas de tiendas: nunca se decodifica más que esto (≈ 4000×6000).
MAX_SOURCE_PIXELS = 24_000_000


@dataclass(frozen=True)
class CollageItem:
    position: int
    image: bytes | None
    price: str
    discount: int | None


_FONT_PATH = Path(__file__).resolve().parents[3] / "assets" / "fonts" / "SpaceGrotesk-latin.woff2"


@lru_cache(maxsize=16)
def _font(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        font = ImageFont.truetype(str(_FONT_PATH), size)
        font.set_variation_by_name(weight)
        return font
    except Exception:
        logger.error("Space Grotesk no disponible para el collage; se usa la fuente de Pillow (sin «€» ni «–»)")
        return ImageFont.load_default(size=size)


def _product_image(raw: bytes | None, box: tuple[int, int]) -> Image.Image | None:
    if not raw:
        return None
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.width * img.height > MAX_SOURCE_PIXELS:
                logger.warning("Imagen de producto demasiado grande para el collage; se omite")
                return None
            img.draft("RGB", box)  # JPEG: decodifica ya reducida
            img = ImageOps.exif_transpose(img)
            img.thumbnail(box, Image.LANCZOS)
            return img.convert("RGBA")
    except Exception:
        logger.warning("Imagen de producto no legible para el collage")
        return None


def _text_center(draw: ImageDraw.ImageDraw, center: tuple[float, float], text: str, font, fill, stroke=0) -> None:
    draw.text(center, text, font=font, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=fill)


def build_collage(items: list[CollageItem], title: str, subtitle: str) -> bytes:
    """JPEG 1600×900: cabecera y una cuadrícula de hasta 5 columnas."""
    canvas = Image.new("RGB", (WIDTH, HEIGHT), _NIGHT)
    draw = ImageDraw.Draw(canvas)

    # Cabecera
    draw.text((PADDING + 2, 30), title, font=_font(54), fill=(255, 255, 255))
    draw.text((PADDING + 4, 92), subtitle, font=_font(28, "Medium"), fill=_CYAN)
    draw.line([(PADDING, HEADER), (WIDTH - PADDING, HEADER)], fill=_RULE, width=2)

    if not items:
        return _jpeg(canvas)

    columns = min(COLUMNS, len(items))
    rows = math.ceil(len(items) / COLUMNS)
    grid_top = HEADER + PADDING
    tile_w = (WIDTH - 2 * PADDING - (columns - 1) * GAP) // columns
    tile_h = (HEIGHT - grid_top - PADDING - (rows - 1) * GAP) // rows
    price_band = 78

    price_font, discount_font, number_font = _font(34), _font(27), _font(40)
    for index, item in enumerate(items):
        row, col = divmod(index, COLUMNS)
        x = PADDING + col * (tile_w + GAP)
        y = grid_top + row * (tile_h + GAP)
        draw.rounded_rectangle([x, y, x + tile_w, y + tile_h], radius=18, fill=_CARD)

        # Foto del producto, centrada en la zona superior.
        box = (tile_w - 36, tile_h - price_band - 30)
        photo = _product_image(item.image, box)
        if photo is not None:
            px = x + (tile_w - photo.width) // 2
            py = y + 18 + (box[1] - photo.height) // 2
            canvas.paste(photo, (px, py), photo)
        else:
            _text_center(draw, (x + tile_w / 2, y + 18 + box[1] / 2), "Sin imagen", _font(26, "Medium"), _MUTED)

        # Precio y descuento
        band_y = y + tile_h - price_band
        draw.line([(x + 16, band_y), (x + tile_w - 16, band_y)], fill=(226, 232, 240), width=2)
        center_y = band_y + price_band / 2
        if item.discount:
            chip = f"-{item.discount} %"
            chip_w = draw.textlength(chip, font=discount_font) + 22
            # Precios largos (12.999,00 €): se reduce la letra hasta que quepan en la tarjeta.
            size = 34
            font = price_font
            while size > 20 and draw.textlength(item.price, font=font) + 12 + chip_w > tile_w - 32:
                size -= 2
                font = _font(size)
            price_w = draw.textlength(item.price, font=font)
            start = x + (tile_w - (price_w + 12 + chip_w)) / 2
            draw.text((start, center_y), item.price, font=font, fill=_TEXT, anchor="lm")
            cx = start + price_w + 12
            draw.rounded_rectangle([cx, center_y - 21, cx + chip_w, center_y + 21], radius=10, fill=_ORANGE)
            _text_center(draw, (cx + chip_w / 2, center_y), chip, discount_font, (255, 255, 255))
        else:
            _text_center(draw, (x + tile_w / 2, center_y), item.price, price_font, _TEXT)

        # Número del top
        r = 34
        bx, by = x + 14 + r, y + 14 + r
        draw.ellipse([bx - r, by - r, bx + r, by + r], fill=_BADGE, outline=_CYAN, width=4)
        _text_center(draw, (bx, by), str(item.position), number_font, (255, 255, 255))

    return _jpeg(canvas)


def _jpeg(canvas: Image.Image) -> bytes:
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue()
