"""API tests for product preview endpoints."""

from fastapi.testclient import TestClient

from app.main import app
from app.modules.deals.api.router import get_deal_repository
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


class FakeDealRepoNoDuplicate:
    """Fake repo: ningún ASIN está en uso, deja pasar el caso de uso."""

    async def find_by_external_id(self, external_id: str, *, exclude_id: str | None = None):
        return None


class FakeExistingDeal:
    id = "existing-deal-id"
    slug = "existing-deal-slug"
    title = "Producto ya publicado"


class FakeDealRepoDuplicate:
    """Fake repo: simula que el ASIN ya tiene un chollo asociado."""

    async def find_by_external_id(self, external_id: str, *, exclude_id: str | None = None):
        return FakeExistingDeal()


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
    response = integration_client.post("/v1/products/preview-from-url", json={})
    assert response.status_code == 422


def test_preview_from_url_returns_normalized_response(integration_client) -> None:
    app.dependency_overrides[get_preview_use_case] = override_use_case
    app.dependency_overrides[get_deal_repository] = lambda: FakeDealRepoNoDuplicate()

    response = integration_client.post(
        "/v1/products/preview-from-url",
        json={"url": "https://www.amazon.es/dp/B08TEST123"},
    )

    app.dependency_overrides.pop(get_preview_use_case, None)
    app.dependency_overrides.pop(get_deal_repository, None)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Producto API"
    assert body["asin"] == "B08TEST123"
    assert body["current_price"] == 10.0
    assert body["store"] == "Amazon"


def test_preview_from_url_duplicate_asin_short_circuits(integration_client) -> None:
    """Si el ASIN ya tiene un chollo, se corta antes de invocar el caso de
    uso (que es quien llama a Amazon Creators API + OpenAI)."""
    from unittest.mock import MagicMock

    use_case = MagicMock(spec=PreviewProductFromUrlUseCase)
    app.dependency_overrides[get_preview_use_case] = lambda: use_case
    app.dependency_overrides[get_deal_repository] = lambda: FakeDealRepoDuplicate()

    response = integration_client.post(
        "/v1/products/preview-from-url",
        json={"url": "https://www.amazon.es/dp/B08TEST123"},
    )

    app.dependency_overrides.pop(get_preview_use_case, None)
    app.dependency_overrides.pop(get_deal_repository, None)

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "DUPLICATE_DEAL"
    assert body["existing_deal"]["title"] == "Producto ya publicado"
    use_case.execute.assert_not_called()

