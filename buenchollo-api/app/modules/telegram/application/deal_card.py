"""Tarjeta de oferta "Simple claro" para la imagen de cada chollo en Telegram.

Sustituye a la foto del producto tal cual: foto, insignia de descuento,
tienda, precio actual, precio anterior tachado, «Ahorras X €» y el logo. El
título y la descripción siguen en el pie de foto.

Fuente de verdad del diseño: `_handoff/plantilla-telegram-oferta/
ESPECIFICACION.md` (raíz de WEB-Buenchollo) y su `referencia.html`. Las alturas
de cada bloque reproducen las del navegador en esa referencia (alto de línea
«normal» de Space Grotesk, 1,276 × tamaño), así que la composición cuadra al
píxel con los PNG de referencia.

Nunca bloquea una publicación: `build_deal_card` devuelve None si faltan datos
(sin precio anterior, o anterior ≤ actual), si la imagen no se puede leer o si
algo falla al componer. Quien la llame publica entonces con la foto original.
"""

from __future__ import annotations

import io
import logging
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from app.modules.telegram.application.weekly_collage import MAX_SOURCE_PIXELS

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1200, 800
PADDING = 32
COLUMN_GAP = 40

_BG = (226, 232, 240)  # #e2e8f0
_WHITE = (255, 255, 255)
_INK = (15, 23, 42)  # #0f172a
_MUTED = (71, 85, 105)  # #475569
_PRICE = (215, 82, 25)  # #d75219
_GREEN = (22, 163, 74)  # #16a34a
_DARK = (11, 17, 32)  # #0b1120

# Geometría (ESPECIFICACION.md).
_PHOTO_BOX = (PADDING, PADDING, 728, 768)  # tarjeta blanca de la foto
_PHOTO_RADIUS = 28
_PRODUCT_MAX = (612, 648)  # foto contenida (88 % de la tarjeta)
_BADGE_ORIGIN = (56, 56)
_COL_X, _COL_W = 768, 400
_COL_TOP, _COL_BOTTOM = 44, 764
_LOGO_W = 340  # 260 en la especificación; ampliado a petición (2026-11-23)
_BLOCK_GAP = 30
# «Ahorras X €»: 34 px y relleno 16/24 en la especificación; ampliado a petición (2026-11-23).
_SAVINGS_SIZE = 40
_SAVINGS_PAD_Y, _SAVINGS_PAD_X = 18, 28
_LINE = 1.276  # alto de línea «normal» de Space Grotesk (ascendente + descendente)

# Tamaño de la parte entera del precio según sus caracteres (con el punto de miles).
_PRICE_SIZES = {1: 210, 2: 180, 3: 140}
_PRICE_SIZE_LONG = 104

# Punto de color de cada tienda; la clave se compara sin mayúsculas ni espacios.
STORE_COLORS: dict[str, tuple[int, int, int]] = {
    "amazon": (255, 153, 0),
    "aliexpress": (255, 71, 71),
    "pccomponentes": (255, 96, 0),
    "mediamarkt": (223, 0, 0),
    "elcorteingles": (0, 166, 80),
    "fnac": (225, 169, 37),
    "carrefour": (30, 91, 198),
    "worten": (227, 6, 19),
    "miravia": (255, 47, 109),
}
DEFAULT_STORE_COLOR = (148, 163, 184)  # #94a3b8

_ASSETS = Path(__file__).resolve().parents[3] / "assets"
_FONT_PATH = _ASSETS / "fonts" / "SpaceGrotesk-latin.woff2"
# Provisional (sacado de una captura): sustituir por el logo original en alta.
LOGO_PATH = _ASSETS / "images" / "logo-bctech.png"


@dataclass(frozen=True)
class DealCardData:
    """Datos de la tarjeta. `discount` y `savings`, si vienen, mandan."""

    current_price: float
    previous_price: float | None
    store: str
    discount: int | None = None
    savings: float | None = None


# ── Reglas de datos (puras) ─────────────────────────────────────────────────


def format_price_es(value: float) -> str:
    """Formato español: miles con «.», decimales con «,», sin «,00» (99, 264,99, 1.299)."""
    cents = int(math.floor(abs(value) * 100 + 0.5))
    integer, decimals = divmod(cents, 100)
    text = f"{integer:,}".replace(",", ".")
    if decimals:
        text += f",{decimals:02d}"
    return f"-{text}" if value < 0 else text


def discount_percentage(current: float, previous: float) -> int:
    """`round((anterior - actual) / anterior * 100)`, redondeando .5 hacia arriba como la referencia."""
    return int(math.floor((previous - current) / previous * 100 + 0.5))


def savings_amount(current: float, previous: float) -> float:
    return round(previous - current, 2)


def price_size(integer_part: str) -> int:
    """Tamaño (px) de la parte entera: 1 → 210 · 2 → 180 · 3 → 140 · ≥4 → 104."""
    return _PRICE_SIZES.get(len(integer_part), _PRICE_SIZE_LONG)


def store_color(store: str) -> tuple[int, int, int]:
    key = "".join(ch for ch in store.lower() if ch.isalnum())
    key = key.replace("é", "e")
    return STORE_COLORS.get(key, DEFAULT_STORE_COLOR)


def card_is_applicable(data: DealCardData) -> bool:
    """La tarjeta solo tiene sentido con una rebaja real."""
    return (
        data.current_price is not None
        and data.current_price > 0
        and data.previous_price is not None
        and data.previous_price > data.current_price
    )


# ── Dibujo ──────────────────────────────────────────────────────────────────


_WEIGHTS = {"SemiBold": 600, "Bold": 700}


@lru_cache(maxsize=32)
def _font(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    """Space Grotesk variable. No trae instancia «SemiBold» con nombre: el peso
    se fija en el eje (`wght` 300-700)."""
    font = ImageFont.truetype(str(_FONT_PATH), size)
    font.set_variation_by_axes([_WEIGHTS[weight]])
    return font


@lru_cache(maxsize=1)
def _logo() -> Image.Image | None:
    try:
        with Image.open(LOGO_PATH) as img:
            logo = img.convert("RGBA")
        height = round(logo.height * _LOGO_W / logo.width)
        return logo.resize((_LOGO_W, height), Image.LANCZOS)
    except Exception:
        logger.warning("Logo de la tarjeta de oferta no disponible; se omite")
        return None


def _product_image(raw: bytes) -> Image.Image:
    """Foto contenida en 612 × 648 (sin recorte ni deformación). Lanza si no se puede leer."""
    with Image.open(io.BytesIO(raw)) as img:
        if img.width * img.height > MAX_SOURCE_PIXELS:
            raise ValueError("imagen de producto demasiado grande")
        img.draft("RGB", _PRODUCT_MAX)  # JPEG: decodifica ya reducida
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGBA")
    return ImageOps.contain(img, _PRODUCT_MAX, method=Image.LANCZOS)


def _line_height(size: float) -> float:
    return size * _LINE


def _baseline(top: float, size: int, line_box: float) -> float:
    """Línea base de un texto en una caja de línea (como CSS: el contenido, centrado)."""
    ascent, descent = _font(size).getmetrics()
    return top + (line_box - (ascent + descent)) / 2 + ascent


def _text_width(text: str, font: ImageFont.FreeTypeFont, spacing: float = 0) -> float:
    return sum(font.getlength(ch) for ch in text) + spacing * len(text)


def _draw_spaced(draw: ImageDraw.ImageDraw, x: float, baseline: float, text: str, font, fill, spacing: float) -> float:
    """Texto con interletraje (letter-spacing de CSS: también tras el último carácter)."""
    for ch in text:
        draw.text((x, baseline), ch, font=font, fill=fill, anchor="ls")
        x += font.getlength(ch) + spacing
    return x


def _badge(canvas: Image.Image, text: str) -> None:
    font = _font(64, "Bold")
    spacing = -2
    width = round(_text_width(text, font, spacing) + 44)
    height = 10 + 64 + 10
    x, y = _BADGE_ORIGIN
    # Sombra suave verde: 0 10px 24px rgba(22,163,74,.35).
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x, y + 10, x + width, y + 10 + height), radius=18, fill=(*_GREEN, 89)
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((x, y, x + width, y + height), radius=18, fill=_GREEN)
    _draw_spaced(draw, x + 22, _baseline(y + 10, 64, 64), text, font, _WHITE, spacing)


def _price_parts(value: float) -> tuple[str, str]:
    text = format_price_es(value)
    integer, _, decimals = text.partition(",")
    return integer, f",{decimals}" if decimals else ""


def _fitting_price_size(integer: str, decimals: str) -> int:
    """Tamaño de la tabla, reducido si (raro) no cupiera en los 400 px de la columna."""
    size = price_size(integer)
    while size > 40:
        width = _text_width(integer, _font(size), -0.04 * size)
        dec_font = _font(round(size * 0.38))
        dec_width = max(dec_font.getlength(decimals or "€"), dec_font.getlength("€"))
        if width + 4 + dec_width <= _COL_W:
            return size
        size -= 4
    return size


def _fitting_savings_size(text: str) -> int:
    """Tamaño del «Ahorras X €»; se reduce si un importe largo no cupiera en la columna."""
    size = _SAVINGS_SIZE
    while size > 24 and _font(size).getlength(text) + 2 * _SAVINGS_PAD_X > _COL_W:
        size -= 2
    return size


def _compose(data: DealCardData, product: Image.Image, discount: int, savings: float) -> Image.Image:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (*_BG, 255))
    draw = ImageDraw.Draw(canvas)

    # Foto.
    draw.rounded_rectangle(_PHOTO_BOX, radius=_PHOTO_RADIUS, fill=_WHITE)
    cx = (_PHOTO_BOX[0] + _PHOTO_BOX[2]) / 2
    cy = (_PHOTO_BOX[1] + _PHOTO_BOX[3]) / 2
    canvas.alpha_composite(product, (round(cx - product.width / 2), round(cy - product.height / 2)))
    _badge(canvas, f"-{discount}%")
    draw = ImageDraw.Draw(canvas)

    # Columna derecha: grupo de datos centrado en el hueco sobre el logo.
    logo = _logo()
    logo_top = _COL_BOTTOM - (logo.height if logo else 0)
    if logo:
        canvas.alpha_composite(logo, (_COL_X, logo_top))

    integer, decimals = _price_parts(data.current_price)
    size = _fitting_price_size(integer, decimals)
    dec_size = round(size * 0.38)
    label_h = _line_height(22)
    pill_h = 12 + _line_height(26) + 12
    dec_h = 0.08 * dec_size + 0.85 * dec_size + 4 + 0.85 * dec_size
    price_h = max(0.85 * size, dec_h)
    now_h = label_h + 4 + price_h
    before_h = label_h + 4 + _line_height(46)
    savings_text = f"Ahorras {format_price_es(savings)} €"
    savings_size = _fitting_savings_size(savings_text)
    savings_h = _SAVINGS_PAD_Y + _line_height(savings_size) + _SAVINGS_PAD_Y
    group_h = pill_h + now_h + before_h + savings_h + 3 * _BLOCK_GAP
    y = _COL_TOP + (logo_top - _COL_TOP - group_h) / 2

    # Tienda.
    store_font = _font(26, "SemiBold")
    pill_w = 22 + 14 + 12 + store_font.getlength(data.store) + 22
    draw.rounded_rectangle((_COL_X, y, _COL_X + pill_w, y + pill_h), radius=pill_h / 2, fill=_WHITE)
    dot_cy = y + pill_h / 2
    draw.ellipse((_COL_X + 22, dot_cy - 7, _COL_X + 36, dot_cy + 7), fill=store_color(data.store))
    draw.text(
        (_COL_X + 48, _baseline(y + 12, 26, _line_height(26))), data.store,
        font=store_font, fill=_INK, anchor="ls",
    )
    y += pill_h + _BLOCK_GAP

    # AHORA + precio.
    label_font = _font(22, "Bold")
    _draw_spaced(draw, _COL_X, _baseline(y, 22, label_h), "AHORA", label_font, _MUTED, 4)
    top = y + label_h + 4
    price_font = _font(size, "Bold")
    end = _draw_spaced(draw, _COL_X, _baseline(top, size, 0.85 * size), integer, price_font, _PRICE, -0.04 * size)
    dec_font = _font(dec_size, "Bold")
    dec_x = end + 4
    line_top = top + 0.08 * dec_size
    for part in ([decimals, "€"] if decimals else ["€"]):
        draw.text((dec_x, _baseline(line_top, dec_size, 0.85 * dec_size)), part, font=dec_font, fill=_PRICE, anchor="ls")
        line_top += 0.85 * dec_size + 4
    y += now_h + _BLOCK_GAP

    # ANTES (tachado).
    _draw_spaced(draw, _COL_X, _baseline(y, 22, label_h), "ANTES", label_font, _MUTED, 4)
    before_font = _font(46, "SemiBold")
    before_text = f"{format_price_es(data.previous_price)} €"
    base = _baseline(y + label_h + 4, 46, _line_height(46))
    draw.text((_COL_X, base), before_text, font=before_font, fill=_MUTED, anchor="ls")
    strike_y = base - 0.30 * 46
    draw.rectangle((_COL_X, strike_y - 2, _COL_X + before_font.getlength(before_text), strike_y + 2), fill=_MUTED)
    y += before_h + _BLOCK_GAP

    # Ahorras X €.
    savings_font = _font(savings_size, "Bold")
    savings_w = _SAVINGS_PAD_X + savings_font.getlength(savings_text) + _SAVINGS_PAD_X
    draw.rounded_rectangle((_COL_X, y, _COL_X + savings_w, y + savings_h), radius=18, fill=_DARK)
    draw.text(
        (_COL_X + _SAVINGS_PAD_X, _baseline(y + _SAVINGS_PAD_Y, savings_size, _line_height(savings_size))),
        savings_text,
        font=savings_font, fill=_WHITE, anchor="ls",
    )
    return canvas


def build_deal_card(data: DealCardData, image: bytes | None) -> bytes | None:
    """Tarjeta JPEG 1200 × 800, o None si no aplica o falla (se publica la foto original)."""
    if not image or not card_is_applicable(data):
        return None
    try:
        product = _product_image(image)
        discount = data.discount if data.discount is not None else discount_percentage(
            data.current_price, data.previous_price
        )
        savings = data.savings if data.savings is not None else savings_amount(
            data.current_price, data.previous_price
        )
        canvas = _compose(data, product, discount, savings)
        out = io.BytesIO()
        canvas.convert("RGB").save(out, format="JPEG", quality=90, optimize=True)
        return out.getvalue()
    except Exception:
        logger.warning("No se pudo generar la tarjeta de oferta; se usa la foto original", exc_info=True)
        return None
