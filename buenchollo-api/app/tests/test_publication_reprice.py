"""Publicación anterior con el precio corregido, lista para volver a publicarla."""
from datetime import datetime, timezone
from decimal import Decimal

from app.modules.telegram.application.post_generator import TelegramPostGenerator
from app.modules.telegram.application.reprice import reprice_publication_text

NOW = datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)
GEN = TelegramPostGenerator(ai_service=object())


def _original(**kw):
    base = dict(
        title="JBL Quantum 360", current_price=69.90, previous_price=99.99, discount_pct=30,
        description="Auriculares gaming", affiliate_url="https://amzn.to/x", expires_at="2026-11-01T22:59:00Z",
    )
    base.update(kw)
    return GEN.generate_text(**base)


def test_cambia_precio_ahorro_y_quita_una_fecha_de_fin_ya_pasada():
    text = reprice_publication_text(
        _original(), price=Decimal("59.90"), previous_price=Decimal("99.99"), discount_pct=40, expires_at=None, now=NOW
    )
    assert "💶 Precio: 59,90 € (antes 99,99 €)" in text
    assert "💰 Ahorro: 40,09 € | -40 %" in text
    assert "69,90" not in text
    assert "Finaliza" not in text
    # El resto del mensaje (título, enlace, descripción, enlace a la web) se conserva
    assert text.startswith("🍄 JBL Quantum 360\n\n")
    assert "🛒 https://amzn.to/x\n\n✏️Auriculares gaming\n\n" in text
    assert text == GEN.generate_text(
        title="JBL Quantum 360", current_price=59.90, previous_price=99.99, discount_pct=40,
        description="Auriculares gaming", affiliate_url="https://amzn.to/x",
    )


def test_respeta_texto_editado_a_mano():
    edited = _original().replace("✏️Auriculares gaming", "✏️¡Mínimo histórico! Mi texto propio")
    text = reprice_publication_text(
        edited, price=Decimal("59.90"), previous_price=Decimal("99.99"), discount_pct=40, expires_at=None, now=NOW
    )
    assert "✏️¡Mínimo histórico! Mi texto propio" in text and "59,90 €" in text


def test_sin_precio_anterior_quita_la_linea_de_ahorro():
    text = reprice_publication_text(
        _original(), price=Decimal("80"), previous_price=None, discount_pct=None, expires_at=None, now=NOW
    )
    assert "💶 Precio: 80,00 €\n\n🛒" in text
    assert "💰" not in text


def test_anade_la_linea_de_ahorro_si_antes_no_habia():
    original = _original(previous_price=None, discount_pct=None)
    text = reprice_publication_text(
        original, price=Decimal("50"), previous_price=Decimal("80"), discount_pct=37, expires_at=None, now=NOW
    )
    assert "💶 Precio: 50,00 € (antes 80,00 €)\n💰 Ahorro: 30,00 € | -37 %\n\n🛒" in text


def test_fecha_de_fin_futura_se_actualiza():
    future = datetime(2026, 11, 20, 22, 59, tzinfo=timezone.utc)
    text = reprice_publication_text(
        _original(), price=Decimal("59.90"), previous_price=Decimal("99.99"), discount_pct=40, expires_at=future, now=NOW
    )
    assert "⚠️ Finaliza el 20 de noviembre" in text


def test_texto_sin_linea_de_precio_devuelve_none():
    assert reprice_publication_text(
        "Mensaje libre sin formato", price=Decimal("1"), previous_price=None, discount_pct=None, expires_at=None, now=NOW
    ) is None
