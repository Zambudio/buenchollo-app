"""Dominio común de ofertas de redes de afiliación (sin I/O)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.modules.affiliates.domain.offers import (
    PublishCandidate,
    ProgramPolicy,
    data_freshness,
    destination_url,
    html_to_text,
    lowest_price_last_30_days,
    normalize_product_url,
    parse_money,
    publication_blockers,
    savings,
    short_summary,
    slug_keywords,
    url_matches,
)

NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
D = Decimal


def test_destination_conserva_variante_y_quita_seguimiento():
    url = "https://www.pccomponentes.com/ssd?color=negro&utm_source=x&capacidad=1tb&gclid=1#reviews"
    assert destination_url(url) == "https://www.pccomponentes.com/ssd?color=negro&capacidad=1tb"


def test_normalizacion_url_exacta():
    a = normalize_product_url("http://WWW.Pccomponentes.com/ssd/?capacidad=1tb&color=negro&utm_medium=x")
    b = normalize_product_url("https://pccomponentes.com/ssd?color=negro&capacidad=1tb")
    assert a == b
    # Otra variante NO es la misma URL.
    assert normalize_product_url("https://pccomponentes.com/ssd?color=blanco&capacidad=1tb") != b


def test_url_matches_dominio_y_ruta():
    assert url_matches("https://www.samsung.com/es/smartphones/x/", ["samsung.com/es"])
    assert not url_matches("https://www.samsung.com/uk/smartphones/x/", ["samsung.com/es"])
    assert not url_matches("https://www.samsung.com/estonia", ["samsung.com/es"])
    assert url_matches("https://tienda.coolmod.com/x", ["coolmod.com"])
    assert not url_matches("https://coolmod.com.evil.example/x", ["coolmod.com"])


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1.299,95", D("1299.95")),
        ("1299.95", D("1299.95")),
        ("EUR 12.5", D("12.50")),
        ("12,50", D("12.50")),
        (19.999, D("20.00")),
        ("", None),
        ("gratis", None),
        (None, None),
        ("-3", None),
    ],
)
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


def test_ahorro_exacto_y_redondeo_half_up():
    assert savings(D("199.90"), D("279.00")) == (D("79.10"), 28)
    assert savings(D("50.00"), D("100.00")) == (D("50.00"), 50)
    assert savings(D("0.99"), D("1.98")) == (D("0.99"), 50)  # 50,0 %
    assert savings(D("10"), D("10")) is None
    assert savings(D("10"), None) is None


def test_html_externo_se_queda_en_texto_plano():
    raw = "<p>Panel IPS</p><script>alert('x')</script><img src=x onerror=alert(1)>&amp; 165 Hz‮"
    assert html_to_text(raw) == "Panel IPS\n& 165 Hz"


def test_resumen_corto_usa_frases_del_proveedor():
    text = "Panel IPS 27 pulgadas QHD. Frecuencia de 165 Hz. " + "Más texto largo " * 20
    summary = short_summary(text, 60)
    assert summary == "Panel IPS 27 pulgadas QHD. Frecuencia de 165 Hz."


def test_slug_keywords():
    words = slug_keywords("https://www.mediamarkt.es/es/product/_fixture-portatil-15-77.html")
    assert words == ["fixture", "portatil"]


def test_minimo_30_dias_omnibus():
    history = [
        (datetime(2026, 9, 1, tzinfo=timezone.utc), D("899.00")),
        (datetime(2026, 10, 10, tzinfo=timezone.utc), D("849.00")),
        (datetime(2026, 11, 7, tzinfo=timezone.utc), D("699.00")),
    ]
    # Bajada el 7/11: la ventana 8/10–7/11 tiene 899 (vigente al empezar) y 849 → mínimo 849.
    assert lowest_price_last_30_days(history, D("699.00"), NOW) == D("849.00")
    # Sin un precio mayor antes, no hay referencia.
    assert lowest_price_last_30_days([(NOW - timedelta(days=3), D("699.00"))], D("699.00"), NOW) is None
    assert lowest_price_last_30_days([], D("10"), NOW) is None


def test_frescura_distingue_dato_de_consulta():
    assert data_freshness(None, None, 24, NOW) == "unknown"
    assert data_freshness(NOW - timedelta(hours=30), None, 24, NOW) == "stale"
    assert data_freshness(NOW - timedelta(hours=30), NOW - timedelta(hours=1), 24, NOW) == "fresh"


def _candidate(**kw):
    base = dict(
        affiliate_url="https://www.awin1.com/cread.php?awinmid=20982&awinaffid=1&ued=x",
        title="Monitor",
        current_price=D("199.90"),
        previous_price=D("249.00"),
        reference_type="store_strikethrough_verified",
        reference_evidence="Precio tachado en la tienda el 08/11/2026 10:00",
        shipping_info="Envío: 4,99 €",
        short_description="Monitor QHD 165 Hz.",
        category_id="cat",
        image_url="https://img.example.com/x.jpg",
        provider_updated_at=NOW - timedelta(hours=2),
        price_verified_at=None,
    )
    base.update(kw)
    return PublishCandidate(**base)


OK_POLICY = ProgramPolicy(True, "joined", ("web", "telegram"), 24)


def test_candidata_completa_se_puede_publicar():
    assert publication_blockers(_candidate(), OK_POLICY, NOW) == []


def test_pvp_recomendado_no_prueba_el_precio_anterior():
    blockers = publication_blockers(_candidate(reference_type="rrp"), OK_POLICY, NOW)
    assert "reference_not_proof" in blockers


def test_precio_anterior_sin_evidencia_bloquea():
    assert "reference_evidence" in publication_blockers(_candidate(reference_evidence=" "), OK_POLICY, NOW)
    assert "previous_price" in publication_blockers(_candidate(previous_price=None), OK_POLICY, NOW)


def test_programa_pendiente_o_sin_permiso_de_imagen_bloquea():
    pending = ProgramPolicy(True, "pending", ("web", "telegram"), 24)
    assert "program_not_joined" in publication_blockers(_candidate(), pending, NOW)
    no_images = ProgramPolicy(True, "joined", (), 24)
    assert "image_rights" in publication_blockers(_candidate(), no_images, NOW)


def test_datos_caducados_o_sin_fecha_bloquean():
    stale = _candidate(provider_updated_at=NOW - timedelta(days=3))
    assert "stale_data" in publication_blockers(stale, OK_POLICY, NOW)
    unknown = _candidate(provider_updated_at=None)
    assert "unknown_data_age" in publication_blockers(unknown, OK_POLICY, NOW)
    verified = _candidate(provider_updated_at=None, price_verified_at=NOW - timedelta(minutes=5))
    assert publication_blockers(verified, OK_POLICY, NOW) == []


def test_enlace_no_afiliado_de_la_red_bloquea():
    blockers = publication_blockers(_candidate(affiliate_url="https://www.pccomponentes.com/x"), OK_POLICY, NOW)
    assert "affiliate_url" in blockers
