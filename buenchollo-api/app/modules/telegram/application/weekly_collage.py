"""Collage del resumen semanal: una imagen con lo que se lee de un
vistazo en el móvil (foto, número del top, precio y descuento, todo grande).
Los títulos y los enlaces van en el texto de la publicación.

Formato 1200×800 (3:2), el mismo que la tarjeta de oferta de cada chollo
(`deal_card.py`): en el canal todas las imágenes salen con el mismo ancho y
alto (2026-11-24). Antes fue 10:9 y, antes aún, una vertical que Telegram
recortaba con pie de foto. Diez tarjetas verticales en 5 columnas × 2 filas.

Usa Space Grotesk, la tipografía de la web (`app/assets/fonts`). Si no se
pudiera cargar, cae a la fuente escalable de Pillow (sin «€» ni «–»).
"""

import io
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1200, 800  # igual que la tarjeta de oferta
HEADER = 92
PADDING = 18
GAP = 12
COLUMNS = 5
ROWS = 2

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
    title: str = ""


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


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: float, max_lines: int) -> list[str]:
    """Parte el texto en líneas que caben en `width`; la última acaba en «…» si sobra."""
    lines: list[str] = []
    words = text.split()
    while words and len(lines) < max_lines:
        line = words.pop(0)
        while words and draw.textlength(f"{line} {words[0]}", font=font) <= width:
            line = f"{line} {words.pop(0)}"
        lines.append(line)
    def fit(line: str) -> str:
        while line and draw.textlength(f"{line}…", font=font) > width:
            line = line[:-1].rstrip()
        return f"{line}…"

    # Una palabra más ancha que la línea (p. ej. un modelo con guiones) se corta.
    lines = [line if draw.textlength(line, font=font) <= width else fit(line) for line in lines]
    if words and lines and not lines[-1].endswith("…"):
        lines[-1] = fit(lines[-1])
    return lines


def build_collage(items: list[CollageItem], title: str, subtitle: str) -> bytes:
    """JPEG 1200×800: cabecera y 5 columnas × 2 filas de tarjetas verticales."""
    canvas = Image.new("RGB", (WIDTH, HEIGHT), _NIGHT)
    draw = ImageDraw.Draw(canvas)

    # Cabecera: solo el título, grande y centrado (un subtítulo no se leería en
    # el móvil). `subtitle` se mantiene en la firma por compatibilidad.
    size = 64
    font = _font(size)
    while size > 36 and draw.textlength(title, font=font) > WIDTH - 2 * PADDING:
        size -= 2
        font = _font(size)
    _text_center(draw, (WIDTH / 2, HEADER / 2 + 4), title, font, (255, 255, 255))

    if not items:
        return _jpeg(canvas)

    grid_top = HEADER + 6
    tile_w = (WIDTH - 2 * PADDING - (COLUMNS - 1) * GAP) // COLUMNS
    tile_h = (HEIGHT - grid_top - PADDING - (ROWS - 1) * GAP) // ROWS
    inner = 10
    photo_side = tile_w - 2 * inner

    number_font = _font(32)
    for index, item in enumerate(items[: COLUMNS * ROWS]):
        row, col = divmod(index, COLUMNS)
        x = PADDING + col * (tile_w + GAP)
        y = grid_top + row * (tile_h + GAP)
        draw.rounded_rectangle([x, y, x + tile_w, y + tile_h], radius=18, fill=_CARD)

        # Foto del producto arriba, cuadrada y lo más grande posible.
        box = (photo_side, photo_side)
        bx0, by0 = x + inner, y + inner
        photo = _product_image(item.image, box)
        if photo is not None:
            canvas.paste(photo, (bx0 + (photo_side - photo.width) // 2, by0 + (photo_side - photo.height) // 2), photo)
        else:
            _text_center(draw, (bx0 + photo_side / 2, by0 + photo_side / 2), "Sin imagen", _font(22, "Medium"), _MUTED)

        # Debajo, solo lo que se lee de un vistazo: precio y descuento en
        # grande, centrados (el detalle va en el texto de la publicación).
        area_top = by0 + photo_side + 4
        area_h = y + tile_h - inner - area_top
        tw = tile_w - 2 * inner
        size = 46
        price_font = _font(size)
        while size > 24 and draw.textlength(item.price, font=price_font) > tw:
            size -= 2
            price_font = _font(size)
        chip = f"-{item.discount} %" if item.discount else ""
        chip_h, chip_size = 42, 30
        block_h = size + (8 + chip_h if chip else 0)
        center_x = x + tile_w / 2
        top = area_top + max(0, (area_h - block_h) / 2)
        _text_center(draw, (center_x, top + size / 2), item.price, price_font, _TEXT)
        if chip:
            chip_font = _font(chip_size)
            chip_w = draw.textlength(chip, font=chip_font) + 28
            cy = top + size + 8 + chip_h / 2
            draw.rounded_rectangle(
                [center_x - chip_w / 2, cy - chip_h / 2, center_x + chip_w / 2, cy + chip_h / 2],
                radius=12,
                fill=_ORANGE,
            )
            _text_center(draw, (center_x, cy), chip, chip_font, (255, 255, 255))

        # Número del top sobre la esquina de la foto.
        r = 26
        cx, cy = x + 6 + r, y + 6 + r
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_BADGE, outline=_CYAN, width=4)
        _text_center(draw, (cx, cy), str(item.position), number_font, (255, 255, 255))

    return _jpeg(canvas)


def _jpeg(canvas: Image.Image) -> bytes:
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue()
