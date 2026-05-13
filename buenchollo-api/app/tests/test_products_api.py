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
    return PreviewProductFromUrlUseCase(FakeProductProvider())


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_preview_from_url_requires_url() -> None:
    client = TestClient(app)

    response = client.post("/products/preview-from-url", json={})

    assert response.status_code == 422


def test_preview_from_url_returns_normalized_response() -> None:
    app.dependency_overrides[get_preview_use_case] = override_use_case
    client = TestClient(app)

    response = client.post("/products/preview-from-url", json={"url": "https://www.amazon.es/dp/B08TEST123"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Producto API"
    assert body["asin"] == "B08TEST123"
    assert body["current_price"] == 10.0
    assert body["store"] == "Amazon"

