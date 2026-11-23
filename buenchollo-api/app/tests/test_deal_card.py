"""Tarjeta de oferta "Simple claro" (imagen de cada chollo en Telegram)."""

import io

import pytest
from PIL import Image

from app.modules.telegram.application import deal_card
from app.modules.telegram.application.deal_card import (
    DEFAULT_STORE_COLOR,
    DealCardData,
    build_deal_card,
    card_is_applicable,
    discount_percentage,
    format_price_es,
    price_size,
    savings_amount,
    store_color,
)


def _photo(size=(428, 414), fmt="PNG") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, (250, 210, 30)).save(out, format=fmt)
    return out.getvalue()


# ── Formato de precios ───────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("value", "text"),
    [
        (99, "99"),
        (99.0, "99"),
        (264.99, "264,99"),
        (1299, "1.299"),
        (1599.5, "1.599,50"),
        (12345.67, "12.345,67"),
        (0.99, "0,99"),
        (9.999, "10"),  # redondeo a céntimos
    ],
)
def test_format_price_es(value, text):
    assert format_price_es(value) == text


# ── % y ahorro ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("current", "previous", "pct"),
    [(99, 159, 38), (264.99, 349.99, 24), (1299, 1599, 19), (50, 100, 50), (87.5, 100, 13)],
)
def test_discount_percentage(current, previous, pct):
    assert discount_percentage(current, previous) == pct


def test_discount_rounds_half_up_like_the_reference():
    # Math.round de la referencia: 12,5 → 13 (round() de Python daría 12).
    assert discount_percentage(87.5, 100) == 13


def test_savings_amount():
    assert savings_amount(264.99, 349.99) == 85.0
    assert format_price_es(savings_amount(264.99, 349.99)) == "85"
    assert format_price_es(savings_amount(99.95, 129.99)) == "30,04"


# ── Tamaño del precio ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("integer", "size"),
    [("9", 210), ("99", 180), ("264", 140), ("1.299", 104), ("12.345", 104)],
)
def test_price_size_by_characters(integer, size):
    assert price_size(integer) == size


@pytest.mark.parametrize("price", [9.99, 99, 264.99, 1299, 12345.67])
def test_price_always_fits_the_column(price):
    integer, decimals = deal_card._price_parts(price)
    size = deal_card._fitting_price_size(integer, decimals)
    width = deal_card._text_width(integer, deal_card._font(size), -0.04 * size)
    dec_font = deal_card._font(round(size * 0.38))
    assert width + 4 + dec_font.getlength(decimals or "€") <= 400


# ── Tienda ───────────────────────────────────────────────────────────────────

def test_store_colors():
    assert store_color("Amazon") == (255, 153, 0)
    assert store_color("PcComponentes") == (255, 96, 0)
    assert store_color("El Corte Inglés") == (0, 166, 80)
    assert store_color("Coolmod") == DEFAULT_STORE_COLOR


# ── Imagen ───────────────────────────────────────────────────────────────────

def test_card_is_jpeg_1200x800():
    jpg = build_deal_card(DealCardData(264.99, 349.99, "PcComponentes"), _photo())
    img = Image.open(io.BytesIO(jpg))
    assert (img.format, img.size) == ("JPEG", (1200, 800))


@pytest.mark.parametrize("price", [9.99, 99, 264.99, 1299])
def test_card_for_each_price_length(price):
    assert build_deal_card(DealCardData(price, price * 1.5, "Amazon"), _photo()) is not None


def test_manual_discount_and_savings_win(monkeypatch):
    seen = {}

    def fake_compose(data, product, discount, savings):
        seen.update(discount=discount, savings=savings)
        return Image.new("RGBA", (1200, 800))

    monkeypatch.setattr(deal_card, "_compose", fake_compose)
    build_deal_card(DealCardData(99, 159, "Amazon", discount=40, savings=61), _photo())
    assert seen == {"discount": 40, "savings": 61}
    build_deal_card(DealCardData(99, 159, "Amazon"), _photo())
    assert seen == {"discount": 38, "savings": 60}


def test_jpeg_and_rotated_photos_are_accepted():
    assert build_deal_card(DealCardData(99, 159, "Amazon"), _photo((1600, 900), "JPEG")) is not None
    assert build_deal_card(DealCardData(99, 159, "Amazon"), _photo((60, 60))) is not None  # se amplía


# ── Respaldos: nunca bloquea, devuelve None y se publica la foto original ────

@pytest.mark.parametrize(
    "data",
    [
        DealCardData(99, None, "Amazon"),  # sin precio anterior
        DealCardData(99, 99, "Amazon"),  # anterior = actual
        DealCardData(99, 80, "Amazon"),  # anterior < actual
        DealCardData(0, 50, "Amazon"),  # precio actual no válido
    ],
)
def test_no_card_without_a_real_discount(data):
    assert card_is_applicable(data) is False
    assert build_deal_card(data, _photo()) is None


@pytest.mark.parametrize("image", [None, b"", b"esto no es una imagen"])
def test_no_card_with_missing_or_unreadable_image(image):
    assert build_deal_card(DealCardData(99, 159, "Amazon"), image) is None


def test_no_card_with_an_oversized_image(monkeypatch):
    monkeypatch.setattr(deal_card, "MAX_SOURCE_PIXELS", 100)
    assert build_deal_card(DealCardData(99, 159, "Amazon"), _photo()) is None


def test_no_card_if_composition_fails(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("fallo al dibujar")

    monkeypatch.setattr(deal_card, "_compose", boom)
    assert build_deal_card(DealCardData(99, 159, "Amazon"), _photo()) is None


def test_card_without_logo_still_renders(monkeypatch):
    monkeypatch.setattr(deal_card, "_logo", lambda: None)
    assert build_deal_card(DealCardData(99, 159, "Amazon"), _photo()) is not None
