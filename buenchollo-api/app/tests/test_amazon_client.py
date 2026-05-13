"""Tests for Amazon product infrastructure helpers."""

from types import SimpleNamespace

from app.core.config import Settings
from app.modules.products.infrastructure import amazon_client
from app.modules.products.infrastructure.amazon_client import AmazonProductClient, extract_asin_from_url


def test_extract_asin_from_dp_url() -> None:
    assert extract_asin_from_url("https://www.amazon.es/dp/B08TEST123") == "B08TEST123"


def test_extract_asin_from_gp_product_url() -> None:
    assert extract_asin_from_url("https://www.amazon.es/gp/product/B09TEST456") == "B09TEST456"


def test_extract_asin_from_direct_asin() -> None:
    assert extract_asin_from_url("b10test789") == "B10TEST789"


def test_amazon_client_maps_sdk_item(monkeypatch) -> None:
    settings = Settings(amazon_client_id="client", amazon_client_secret="secret", amazon_affiliate_tag="tag-21")
    item = SimpleNamespace(
        asin="B08TEST123",
        detail_page_url="https://www.amazon.es/dp/B08TEST123?tag=tag-21",
        item_info=SimpleNamespace(
            title=SimpleNamespace(display_value="Producto Test, detalle extra"),
            by_line_info=SimpleNamespace(brand=SimpleNamespace(display_value="Marca")),
            features=SimpleNamespace(display_values=["Feature uno", "Feature dos"]),
        ),
        browse_node_info=SimpleNamespace(
            browse_nodes=[SimpleNamespace(display_name="Informatica"), SimpleNamespace(display_name="Accesorios")]
        ),
        images=SimpleNamespace(primary=SimpleNamespace(large=SimpleNamespace(url="https://img.test/1.jpg"))),
        offers_v2=SimpleNamespace(
            listings=[
                SimpleNamespace(
                    is_buy_box_winner=True,
                    price=SimpleNamespace(
                        money=SimpleNamespace(amount=10.0, currency="EUR"),
                        saving_basis=SimpleNamespace(money=SimpleNamespace(amount=20.0)),
                        savings=SimpleNamespace(percentage=50),
                    ),
                )
            ]
        ),
    )

    monkeypatch.setattr(amazon_client, "AmazonCreatorsApi", object)
    monkeypatch.setattr(amazon_client, "GetItemsRequestContent", object)

    client = AmazonProductClient(settings)
    monkeypatch.setattr(client, "_get_items", lambda asin: [item])

    product = client.get_product_preview("https://www.amazon.es/dp/B08TEST123")

    assert product is not None
    assert product.title == "Producto Test"
    assert product.brand == "Marca"
    assert product.current_price == 10.0
    assert product.original_price == 20.0
    assert product.discount_percentage == 50
    assert "Producto Test" in product.telegram_text


def test_settings_accepts_legacy_amazon_api_version() -> None:
    settings = Settings(amazon_api_version="3.2", amazon_credential_version="")

    assert settings.amazon_effective_credential_version == "3.2"


def test_settings_allows_credential_version_override() -> None:
    settings = Settings(amazon_api_version="3.2", amazon_credential_version="3.1")

    assert settings.amazon_effective_credential_version == "3.1"


def test_amazon_client_uses_working_creators_client(monkeypatch) -> None:
    captured: dict[str, object] = {}
    settings = Settings(
        amazon_client_id="client",
        amazon_client_secret="secret",
        amazon_api_version="3.2",
        amazon_affiliate_tag="tag-21",
    )

    class FakeAmazonCreatorsApi:
        def __init__(self, **kwargs) -> None:
            captured["client_kwargs"] = kwargs

        def get_items(self, asin, resources):
            captured["asin"] = asin
            captured["resources"] = resources
            return []

    monkeypatch.setattr(amazon_client, "AmazonCreatorsApi", FakeAmazonCreatorsApi)

    client = AmazonProductClient(settings)
    client._get_items_with_credential_version("B08TEST123", "3.2")

    assert captured["client_kwargs"]["version"] == "3.2"
    assert captured["client_kwargs"]["tag"] == "tag-21"
    assert captured["asin"] == "B08TEST123"

