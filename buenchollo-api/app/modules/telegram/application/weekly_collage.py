"""Collage del resumen semanal: una imagen vertical con la foto, el número del
top, el precio, el descuento y el título de cada chollo, para identificar de un
vistazo los enlaces del mensaje.

Proporción 5:6 (1080×1296): Telegram recorta en el chat las fotos más altas
que ~3:4, y una 2:3 obligaba a abrirla para verla entera. Así se ve completa
y a todo el ancho del mensaje.

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

WIDTH, HEIGHT = 1080, 1296
HEADER = 118
PADDING = 22
GAP = 12
COLUMNS = 2
ROWS = 5

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
    """JPEG 1080×1296: cabecera y 2 columnas × 5 filas de tarjetas horizontales."""
    canvas = Image.new("RGB", (WIDTH, HEIGHT), _NIGHT)
    draw = ImageDraw.Draw(canvas)

    # Cabecera
    draw.text((PADDING + 2, 22), title, font=_font(56), fill=(255, 255, 255))
    draw.text((PADDING + 4, 82), subtitle, font=_font(26, "Medium"), fill=_CYAN)
    draw.line([(PADDING, HEADER), (WIDTH - PADDING, HEADER)], fill=_RULE, width=2)

    if not items:
        return _jpeg(canvas)

    grid_top = HEADER + 16
    tile_w = (WIDTH - 2 * PADDING - (COLUMNS - 1) * GAP) // COLUMNS
    tile_h = (HEIGHT - grid_top - PADDING - (ROWS - 1) * GAP) // ROWS
    inner = 12
    photo_side = tile_h - 2 * inner

    discount_font, number_font, title_font = _font(25), _font(30), _font(21, "Medium")
    for index, item in enumerate(items[: COLUMNS * ROWS]):
        row, col = divmod(index, COLUMNS)
        x = PADDING + col * (tile_w + GAP)
        y = grid_top + row * (tile_h + GAP)
        draw.rounded_rectangle([x, y, x + tile_w, y + tile_h], radius=18, fill=_CARD)

        # Foto del producto a la izquierda, centrada en su hueco.
        box = (photo_side, photo_side)
        bx0, by0 = x + inner, y + (tile_h - photo_side) // 2
        photo = _product_image(item.image, box)
        if photo is not None:
            canvas.paste(photo, (bx0 + (photo_side - photo.width) // 2, by0 + (photo_side - photo.height) // 2), photo)
        else:
            _text_center(draw, (bx0 + photo_side / 2, by0 + photo_side / 2), "Sin imagen", _font(22, "Medium"), _MUTED)

        # Precio, descuento y título a la derecha.
        tx = bx0 + photo_side + 16
        tw = x + tile_w - inner - tx
        # Precio y descuento en la misma línea (grandes); debajo, el título.
        chip = f"-{item.discount} %" if item.discount else ""
        chip_w = draw.textlength(chip, font=discount_font) + 18 if chip else 0
        size = 40
        price_font = _font(size)
        while size > 24 and draw.textlength(item.price, font=price_font) + (chip_w + 10 if chip else 0) > tw:
            size -= 2
            price_font = _font(size)
        ty = y + 20
        draw.text((tx, ty), item.price, font=price_font, fill=_TEXT, anchor="lt")
        if chip:
            cx = tx + draw.textlength(item.price, font=price_font) + 10
            cy = ty + size / 2 + 3
            draw.rounded_rectangle([cx, cy - 17, cx + chip_w, cy + 17], radius=9, fill=_ORANGE)
            _text_center(draw, (cx + chip_w / 2, cy), chip, discount_font, (255, 255, 255))
        ty += size + 16
        for line in _wrap(draw, item.title, title_font, tw, 3):
            draw.text((tx, ty), line, font=title_font, fill=_MUTED, anchor="lt")
            ty += 26

        # Número del top, sobre la esquina de la foto.
        r = 24
        cx, cy = x + 8 + r, y + 8 + r
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_BADGE, outline=_CYAN, width=4)
        _text_center(draw, (cx, cy), str(item.position), number_font, (255, 255, 255))

    return _jpeg(canvas)


def _jpeg(canvas: Image.Image) -> bytes:
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue()
