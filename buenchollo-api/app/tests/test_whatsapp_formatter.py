from app.modules.telegram.application.post_generator import TelegramPostGenerator
from app.modules.telegram.application.whatsapp_formatter import WHATSAPP_LINK_URL, to_whatsapp_text


def _telegram_text(**overrides) -> str:
    data = {
        "title": "DJI Osmo Pocket 3",
        "current_price": 269.0,
        "previous_price": 429.0,
        "discount_pct": 37,
        "description": "Captura cada momento",
        "affiliate_url": "https://amzn.to/x",
        "expires_at": "2026-12-05T10:00:00Z",
        **overrides,
    }
    generator = TelegramPostGenerator(ai_service=object())
    return generator.generate_text(**data)


def test_sustituye_los_emojis_premium_por_emojis_estandar():
    text = to_whatsapp_text(_telegram_text(shipping_info="Envío gratis", notice="Solo socios"))

    for premium in ("🍄", "💶", "💰", "🛒", "✏", "⚠", "🔗"):
        assert premium not in text
    assert "🔥 *DJI Osmo Pocket 3*" in text
    assert "🏷️ *Precio: 269,00 € (antes 429,00 €)*" in text
    assert "💸 *Ahorro: 160,00 € | -37 %*" in text
    assert "🚚 Envío gratis" in text
    assert "👉 https://amzn.to/x" in text
    assert "📝 Captura cada momento" in text
    assert "⏰ Finaliza el 5 de diciembre" in text
    assert "ℹ️ Solo socios" in text


def test_el_enlace_a_la_web_lleva_la_url_visible():
    text = to_whatsapp_text(_telegram_text())

    assert text.endswith(f"🌐 Todos los chollos en nuestra web: {WHATSAPP_LINK_URL}")


def test_quita_las_categorias_del_canal_de_telegram():
    text = to_whatsapp_text(_telegram_text() + "#Gadgets\n#Camaras")

    assert "#" not in text


def test_las_negritas_no_se_rompen_con_asteriscos_del_titulo():
    text = to_whatsapp_text(_telegram_text(title="Pack *oferta* 2x1"))

    assert "🔥 *Pack oferta 2x1*" in text


def test_respeta_el_texto_editado_a_mano():
    edited = "🍄 Título editado\n\nLínea libre sin emoji\n\n🛒 https://amzn.to/y\n"

    assert to_whatsapp_text(edited) == "🔥 *Título editado*\n\nLínea libre sin emoji\n\n👉 https://amzn.to/y"


def test_texto_vacio():
    assert to_whatsapp_text("") == ""
