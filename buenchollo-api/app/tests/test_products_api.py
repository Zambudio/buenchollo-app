"""API tests for product preview endpoints."""

from fastapi.testclient import TestClient

from app.main import app
from app.modules.products.api.router import get_preview_use_case
from app.modules.products.application.preview_product_from_url import PreviewProductFromUrlUseCase
from app.modules.products.domain.entities import ProductPreview


class FakeProductProvider:
    """Provider fake used to avoid Amazon calls in API tests."""

    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None:
        return ProductPreview(
            title="Producto API",
            brand="Marca",
            asin="B08TEST123",
            product_url="https://www.amazon.es/dp/B08TEST123",
            affiliate_url="https://www.amazon.es/dp/B08TEST123?tag=test-21",
            image_url="https://img.test/1.jpg",
            current_price=10.0,
            original_price=20.0,
            discount_percentage=50,
            category="Informática",
            description="Descripción corta",
            telegram_text="Producto API\nhttps://www.amazon.es/dp/B08TEST123?tag=test-21",
        )


def override_use_case() -> PreviewProductFromUrlUseCase:
    from unittest.mock import MagicMock
    category_client = MagicMock()
    category_client.get_categories_hierarchy.return_value = []
    category_client.format_categories_for_prompt.return_value = ""
    ai_assistant = MagicMock()
    ai_assistant.enrich_product.return_value = {}
    return PreviewProductFromUrlUseCase(FakeProductProvider(), category_client, ai_assistant)


def test_health(integration_client) -> None:
    response = integration_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_preview_from_url_requires_url(integration_client) -> None:
    response = integration_client.post("/products/preview-from-url", json={})
    assert response.status_code == 422


def test_preview_from_url_returns_normalized_response(integration_client) -> None:
    app.dependency_overrides[get_preview_use_case] = override_use_case

    response = integration_client.post(
        "/products/preview-from-url",
        json={"url": "https://www.amazon.es/dp/B08TEST123"},
    )

    app.dependency_overrides.pop(get_preview_use_case, None)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Producto API"
    assert body["asin"] == "B08TEST123"
    assert body["current_price"] == 10.0
    assert body["store"] == "Amazon"

