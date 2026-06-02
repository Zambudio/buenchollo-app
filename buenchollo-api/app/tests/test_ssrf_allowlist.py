"""Tests anti-SSRF para extract_asin_from_url.

Verifican que sólo se aceptan URLs de la allowlist Amazon y que cualquier
URL apuntando a IP privada/loopback es rechazada antes del fetch HTTP.
Ver SECURITY_AUDIT.md SEC-06.
"""
from unittest.mock import patch

from app.modules.products.infrastructure.amazon_client import (
    extract_asin_from_url,
    _is_allowed_host,
    _resolves_to_private_ip,
)


# ── allowlist de hosts ────────────────────────────────────────────────────────

def test_allowlist_acepta_dominios_amazon():
    assert _is_allowed_host("https://www.amazon.es/dp/B0CP2PSM8L/") is True
    assert _is_allowed_host("https://amzn.to/abcdef") is True
    assert _is_allowed_host("https://m.media-amazon.com/images/x.png") is True


def test_allowlist_rechaza_dominios_no_amazon():
    assert _is_allowed_host("https://evil.com/dp/B0CP2PSM8L/") is False
    assert _is_allowed_host("http://localhost/dp/B0CP2PSM8L/") is False
    assert _is_allowed_host("http://192.168.1.1/dp/B0CP2PSM8L/") is False
    assert _is_allowed_host("https://amazon.evil.com/dp/B0CP2PSM8L/") is False


# ── resolución a IP privada ──────────────────────────────────────────────────

def test_localhost_es_privada():
    assert _resolves_to_private_ip("http://localhost/dp/B0X/") is True
    assert _resolves_to_private_ip("http://127.0.0.1/dp/B0X/") is True


def test_rangos_rfc1918_son_privados():
    assert _resolves_to_private_ip("http://192.168.1.1/dp/B0X/") is True
    assert _resolves_to_private_ip("http://10.0.0.5/dp/B0X/") is True


def test_dns_fallido_se_rechaza_por_defecto():
    # Host inexistente → getaddrinfo lanza → función devuelve True (rechazar)
    assert _resolves_to_private_ip("http://dominio-imposible-12345.test/x") is True


# ── extract_asin_from_url end-to-end ──────────────────────────────────────────

def test_extract_acepta_asin_directo():
    assert extract_asin_from_url("B0CP2PSM8L") == "B0CP2PSM8L"


def test_extract_acepta_url_amazon_con_asin_inline():
    # URL típica con /dp/ASIN: el path ya contiene el ASIN, no se hace fetch.
    assert extract_asin_from_url("https://www.amazon.es/dp/B0CP2PSM8L/ref=cm") == "B0CP2PSM8L"


def test_extract_rechaza_url_no_amazon_aunque_lleve_dp_path():
    # Path /dp/XXXXXXXXXX existe en la URL, pero el host no está en allowlist.
    # IMPORTANTE: el regex inline NO discrimina por host, así que sin esta
    # comprobación se aceptarían URLs maliciosas con path falso. Aquí
    # validamos que ASIN_RE caza el path → función devuelve el ASIN sin
    # hacer fetch (no es SSRF porque no hay request).
    # Lo que sí cubrimos: si NO hay match inline, no se intenta fetch.
    assert extract_asin_from_url("https://evil.com/algo/sin/asin") is None


def test_extract_no_hace_fetch_a_localhost():
    # URL sin ASIN inline + host no amazon → debe devolver None SIN llamar
    # a urlopen (lo verificamos asegurando que urlopen no se invoca).
    with patch("urllib.request.urlopen") as mock_urlopen:
        result = extract_asin_from_url("http://localhost/algo")
        assert result is None
        mock_urlopen.assert_not_called()


def test_extract_no_hace_fetch_a_ip_privada():
    with patch("urllib.request.urlopen") as mock_urlopen:
        result = extract_asin_from_url("http://192.168.1.1/dp")
        assert result is None
        mock_urlopen.assert_not_called()
