"""Icono premium del enlace (🛒) según la tienda del chollo.

Amazon conserva su logo; cualquier otra tienda sin icono propio (Coolmod...)
usa el genérico. El enlace de Awin (`tidd.ly`) no dice la tienda: cuando se
conoce el chollo, manda su tienda.
"""

import pytest

from app.modules.telegram.application.post_generator import (
    AMAZON_LINK_ICON,
    GENERIC_LINK_ICON,
    STORE_LINK_ICONS,
    TelegramPostGenerator,
    link_icon_for,
)


def _cart_icons(text: str, store_name: str | None = None) -> list[str]:
    generator = TelegramPostGenerator(ai_service=object())
    cart_len = len("🛒".encode("utf-16-le")) // 2
    return [
        e["custom_emoji_id"]
        for e in generator.build_entities(text, store_name=store_name)
        if e["type"] == "custom_emoji" and e["length"] == cart_len
        and text.encode("utf-16-le")[e["offset"] * 2 : (e["offset"] + e["length"]) * 2].decode("utf-16-le") == "🛒"
    ]


def _post(url: str) -> str:
    return TelegramPostGenerator(ai_service=object()).generate_text(
        title="Chollo", current_price=10.0, affiliate_url=url
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://www.amazon.es/dp/B0ABC12345?tag=x-21",
        "https://amzn.to/3abcd",
        "https://amzn.eu/d/abc",
        "https://link.amazon/B03jaRFry",
    ],
)
def test_amazon_links_keep_the_amazon_icon(url: str) -> None:
    assert _cart_icons(_post(url)) == [AMAZON_LINK_ICON]


@pytest.mark.parametrize(
    "url",
    ["https://tidd.ly/4AJGHjb", "https://www.awin1.com/cread.php?awinmid=124624", "https://www.coolmod.com/x"],
)
def test_other_links_use_the_generic_icon(url: str) -> None:
    assert _cart_icons(_post(url)) == [GENERIC_LINK_ICON]


def test_store_of_the_deal_wins_over_the_link() -> None:
    # Coolmod vía Awin: el enlace no lo dice, la tienda sí.
    assert _cart_icons(_post("https://tidd.ly/4AJGHjb"), store_name="Coolmod") == [GENERIC_LINK_ICON]
    assert _cart_icons(_post("https://tidd.ly/4AJGHjb"), store_name="Amazon") == [AMAZON_LINK_ICON]


def test_store_with_its_own_icon(monkeypatch) -> None:
    monkeypatch.setitem(STORE_LINK_ICONS, "samsung", "111")
    assert link_icon_for("https://tidd.ly/x", "Samsung ES") == "111"
    assert link_icon_for("https://www.samsung.com/es/x", None) == "111"


def test_each_cart_line_gets_its_own_icon() -> None:
    # Resumen semanal: varias líneas 🛒, cada una con su enlace.
    text = "1️⃣ A\n🛒 https://www.amazon.es/dp/B0ABC12345\n\n2️⃣ B\n🛒 https://tidd.ly/x\n"
    assert _cart_icons(text) == [AMAZON_LINK_ICON, GENERIC_LINK_ICON]


def test_other_emojis_unchanged() -> None:
    generator = TelegramPostGenerator(ai_service=object())
    ids = {e["custom_emoji_id"] for e in generator.build_entities(_post("https://tidd.ly/x")) if e["type"] == "custom_emoji"}
    assert "5242687246162731515" in ids  # 🍄 título
    assert "5201873447554145566" in ids  # 💶 precio
