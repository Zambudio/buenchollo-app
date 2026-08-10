"""Tests for Amazon product infrastructure helpers.

El cliente se reescribió a HTTP directo (eliminado el SDK `amazon_paapi`),
así que los tests mockean `_fetch_item` con un payload tipo `itemsResult`
del Creators API.
"""

import pytest

from app.core.config import Settings
from app.modules.products.application.preview_product_from_url import ProductProviderUnavailableError
from app.modules.products.infrastructure.amazon_client import (
    AmazonProductClient,
    MAX_ITEMS_PER_REQUEST,
    RESOURCES,
    extract_asin_from_url,
)


def test_extract_asin_from_dp_url() -> None:
    assert extract_asin_from_url("https://www.amazon.es/dp/B08TEST123") == "B08TEST123"


def test_extract_asin_from_gp_product_url() -> None:
    assert extract_asin_from_url("https://www.amazon.es/gp/product/B09TEST456") == "B09TEST456"


def test_extract_asin_from_direct_asin() -> None:
    assert extract_asin_from_url("b10test789") == "B10TEST789"


def test_settings_accepts_legacy_amazon_api_version() -> None:
    settings = Settings(amazon_api_version="3.2", amazon_credential_version="")
    assert settings.amazon_effective_credential_version == "3.2"


def test_settings_allows_credential_version_override() -> None:
    settings = Settings(amazon_api_version="3.2", amazon_credential_version="3.1")
    assert settings.amazon_effective_credential_version == "3.1"


def test_amazon_client_maps_creators_api_payload(monkeypatch) -> None:
    """`_map_item` debe construir un ProductPreview correcto a partir del dict
    JSON que devuelve el Creators API. El test mockea `_fetch_item` para evitar
    salida a red y `_get_token` para evitar el flujo OAuth."""
    settings = Settings(
        amazon_client_id="client",
        amazon_client_secret="secret",
        amazon_affiliate_tag="tag-21",
    )
    item_payload = {
        "asin": "B08TEST123",
        "detailPageURL": "https://www.amazon.es/dp/B08TEST123?tag=tag-21",
        "itemInfo": {
            "title": {"displayValue": "Producto Test, detalle extra"},
            "byLineInfo": {"brand": {"displayValue": "Marca"}},
            "features": {"displayValues": ["Feature uno", "Feature dos"]},
        },
        "browseNodeInfo": {
            "browseNodes": [
                {"displayName": "Informatica"},
                {"displayName": "Accesorios"},
            ]
        },
        "images": {"primary": {"large": {"url": "https://img.test/1.jpg"}}},
        "offersV2": {
            "listings": [
                {
                    "isBuyBoxWinner": True,
                    "availability": {"type": "NOW", "message": "En stock"},
                    "deliveryInfo": {"isAmazonFulfilled": True},
                    "price": {
                        "money": {"amount": 10.0, "currency": "EUR"},
                        "savingBasis": {"money": {"amount": 20.0}},
                        "savings": {"percentage": 50},
                    },
                }
            ]
        },
    }

    client = AmazonProductClient(settings)
    monkeypatch.setattr(client, "_get_token", lambda: "fake-token")
    monkeypatch.setattr(client, "_fetch_item", lambda asin, token: item_payload)

    product = client.get_product_preview("https://www.amazon.es/dp/B08TEST123")

    assert product is not None
    assert product.asin == "B08TEST123"
    assert product.title == "Producto Test"  # _clean_title parte por la primera coma
    assert product.brand == "Marca"
    assert product.current_price == 10.0
    assert product.original_price == 20.0
    assert product.discount_percentage == 50
    assert product.in_stock is True
    assert product.shipping_type == "Gestionado por Amazon"
    # telegram_text no se rellena aquí: lo genera la IA en el enriquecimiento
    # posterior (preview_product_from_url.py). Si queda vacío, el generador
    # de posts de Telegram simplemente omite la sección de descripción en
    # lugar de incrustar un mensaje pre-formateado obsoleto.
    assert product.telegram_text == ""


def test_amazon_client_returns_none_when_asin_missing() -> None:
    settings = Settings(amazon_client_id="client", amazon_client_secret="secret", amazon_affiliate_tag="tag-21")
    client = AmazonProductClient(settings)
    assert client.get_product_preview("https://no-es-una-url-amazon.com") is None


def test_creators_api_request_uses_only_supported_offer_resources() -> None:
    assert "offersV2.listings.availability" in RESOURCES
    assert "offersV2.listings.merchantInfo" in RESOURCES
    assert "offersV2.listings.deliveryInfo" not in RESOURCES


def test_fetch_item_delega_en_fetch_items_con_un_solo_asin(monkeypatch) -> None:
    settings = Settings(amazon_client_id="client", amazon_client_secret="secret", amazon_affiliate_tag="tag-21")
    client = AmazonProductClient(settings)
    captured = {}

    def fake_fetch_items(asins, token):
        captured["asins"] = list(asins)
        return [{"asin": "B001", "title": "x"}]

    monkeypatch.setattr(client, "_fetch_items", fake_fetch_items)

    item = client._fetch_item("B001", "token")

    assert captured["asins"] == ["B001"]
    assert item == {"asin": "B001", "title": "x"}


def test_fetch_item_devuelve_none_si_fetch_items_no_encuentra_nada(monkeypatch) -> None:
    settings = Settings(amazon_client_id="client", amazon_client_secret="secret", amazon_affiliate_tag="tag-21")
    client = AmazonProductClient(settings)
    monkeypatch.setattr(client, "_fetch_items", lambda asins, token: [])

    assert client._fetch_item("B001", "token") is None


def test_get_product_previews_hace_una_sola_peticion_para_varios_asin(monkeypatch) -> None:
    settings = Settings(amazon_client_id="client", amazon_client_secret="secret", amazon_affiliate_tag="tag-21")
    client = AmazonProductClient(settings)
    monkeypatch.setattr(client, "_get_token", lambda: "fake-token")
    calls = []

    def fake_fetch_items(asins, token):
        calls.append(list(asins))
        return [
            {
                "asin": asin,
                "itemInfo": {"title": {"displayValue": f"Producto {asin}"}},
                "offersV2": {
                    "listings": [
                        {
                            "isBuyBoxWinner": True,
                            "availability": {"type": "NOW"},
                            "price": {"money": {"amount": 10.0, "currency": "EUR"}},
                        }
                    ]
                },
            }
            for asin in asins
        ]

    monkeypatch.setattr(client, "_fetch_items", fake_fetch_items)

    result = client.get_product_previews(["B001", "B002", "B003"])

    assert calls == [["B001", "B002", "B003"]]  # una única petición, no 3
    assert set(result.keys()) == {"B001", "B002", "B003"}
    assert all(v is not None and v.current_price == 10.0 for v in result.values())


def test_get_product_previews_no_troceA_internamente_es_cosa_del_caller(monkeypatch) -> None:
    """`get_product_previews` hace exactamente 1 llamada HTTP por invocación:
    trocear listas largas en lotes de MAX_ITEMS_PER_REQUEST es responsabilidad
    del caller (PriceCheckHandler), no de este método — así un fallo de red
    en un lote no oculte cuántos ASIN se pidieron ni reintente lotes ya
    resueltos."""
    settings = Settings(amazon_client_id="client", amazon_client_secret="secret", amazon_affiliate_tag="tag-21")
    client = AmazonProductClient(settings)
    monkeypatch.setattr(client, "_get_token", lambda: "fake-token")
    calls = []
    monkeypatch.setattr(client, "_fetch_items", lambda asins, token: calls.append(list(asins)) or [])

    asins = [f"B{i:03d}" for i in range(MAX_ITEMS_PER_REQUEST + 5)]
    client.get_product_previews(asins)

    assert len(calls) == 1
    assert len(calls[0]) == MAX_ITEMS_PER_REQUEST + 5


def test_get_product_previews_marca_none_los_asin_no_encontrados(monkeypatch) -> None:
    settings = Settings(amazon_client_id="client", amazon_client_secret="secret", amazon_affiliate_tag="tag-21")
    client = AmazonProductClient(settings)
    monkeypatch.setattr(client, "_get_token", lambda: "fake-token")
    monkeypatch.setattr(client, "_fetch_items", lambda asins, token: [])  # Amazon no devuelve nada

    result = client.get_product_previews(["B001", "B002"])

    assert result == {"B001": None, "B002": None}


def test_get_product_previews_vacio_no_llama_a_amazon(monkeypatch) -> None:
    settings = Settings(amazon_client_id="client", amazon_client_secret="secret", amazon_affiliate_tag="tag-21")
    client = AmazonProductClient(settings)
    called = False

    def fake_get_token():
        nonlocal called
        called = True
        return "token"

    monkeypatch.setattr(client, "_get_token", fake_get_token)

    result = client.get_product_previews([])

    assert result == {}
    assert called is False


def test_get_product_previews_sin_credenciales_lanza_error() -> None:
    settings = Settings(amazon_client_id="", amazon_client_secret="")
    client = AmazonProductClient(settings)

    with pytest.raises(ProductProviderUnavailableError):
        client.get_product_previews(["B001"])
