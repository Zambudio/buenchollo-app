"""Enriquecimiento con IA de un producto ya importado (Awin / Tradedoubler).

Mismo copywriting y categorización que el autocompletado de Amazon, pero a
partir de los datos del catálogo: sin llamar a Amazon ni a la tienda.
"""

from unittest.mock import MagicMock

import pytest

from app.core.security import require_admin
from app.main import app
from app.modules.products.api.router import get_enrich_use_case
from app.modules.products.application.preview_product_from_url import EnrichProductUseCase

CATEGORIES = [
    {"id": "cat-tv", "name": "Televisores", "parent_id": None, "slug": "televisores"},
    {"id": "sub-tv", "name": "Smart TV", "parent_id": "cat-tv", "slug": "smart-tv"},
    {"id": "cat-varios", "name": "Varios", "parent_id": None, "slug": "varios-xly2"},
    {"id": "sub-varios", "name": "Varios", "parent_id": "cat-varios", "slug": "varios-y175"},
]


def _use_case(ai_data: dict) -> tuple[EnrichProductUseCase, MagicMock]:
    category_client = MagicMock()
    category_client.get_categories_hierarchy.return_value = CATEGORIES
    category_client.format_categories_for_prompt.return_value = "PROMPT"
    ai = MagicMock()
    ai.enrich_product.return_value = ai_data
    return EnrichProductUseCase(category_client, ai), ai


class TestEnrichProductUseCase:
    def test_ai_fields_are_returned(self):
        use_case, ai = _use_case(
            {
                "short_description": "Mini LED 4K de 43 pulgadas",
                "long_description": "**Mini LED**",
                "telegram_text": "Tele Mini LED a buen precio",
                "category_id": "cat-tv",
                "subcategory_id": "sub-tv",
            }
        )
        product = use_case.execute(title="Samsung M70H 43", description="Tele 4K", brand="Samsung")
        assert product.short_description == "Mini LED 4K de 43 pulgadas"
        assert product.long_description == "**Mini LED**"
        assert product.telegram_text == "Tele Mini LED a buen precio"
        assert (product.category_id, product.subcategory_id) == ("cat-tv", "sub-tv")
        sent = ai.enrich_product.call_args.args[0]
        assert sent.title == "Samsung M70H 43"
        assert sent.brand == "Samsung"
        assert ai.enrich_product.call_args.args[1] == "PROMPT"

    def test_store_category_is_given_to_the_ai_as_context(self):
        use_case, ai = _use_case({})
        use_case.execute(title="Samsung M70H", description="Tele 4K", category_hint="Televisores")
        sent = ai.enrich_product.call_args.args[0]
        assert "Televisores" in sent.description
        assert "Tele 4K" in sent.description

    def test_fallback_long_description_drops_the_category_hint(self):
        # El enriquecedor, si la IA falla, devuelve la descripción recibida.
        use_case, ai = _use_case({})
        ai.enrich_product.side_effect = lambda product, *_a, **_k: {"long_description": product.description}
        product = use_case.execute(title="X", description="Tele 4K", category_hint="Televisores")
        assert product.long_description == "Tele 4K"

    def test_falls_back_to_varios_when_ai_does_not_classify(self):
        use_case, _ = _use_case({})
        product = use_case.execute(title="Cosa rara", description="")
        assert (product.category_id, product.subcategory_id) == ("cat-varios", "sub-varios")

    def test_provider_is_forwarded(self):
        use_case, ai = _use_case({})
        use_case.execute(title="X", provider="openai")
        assert ai.enrich_product.call_args.kwargs["provider"] == "openai"


@pytest.fixture
def as_admin():
    app.dependency_overrides[require_admin] = lambda: object()
    yield
    app.dependency_overrides.pop(require_admin, None)


def test_enrich_requires_authentication(integration_client) -> None:
    response = integration_client.post("/v1/products/enrich", json={"title": "X"})
    assert response.status_code in (401, 403)


def test_enrich_requires_title(integration_client, as_admin) -> None:
    response = integration_client.post("/v1/products/enrich", json={"title": "  "})
    assert response.status_code == 422


def test_enrich_returns_ai_fields(integration_client, as_admin) -> None:
    use_case, _ = _use_case(
        {
            "short_description": "Corta",
            "long_description": "Larga",
            "telegram_text": "Post",
            "category_id": "cat-tv",
            "subcategory_id": "sub-tv",
        }
    )
    app.dependency_overrides[get_enrich_use_case] = lambda: use_case
    try:
        response = integration_client.post(
            "/v1/products/enrich",
            json={"title": "Samsung M70H", "description": "Tele", "brand": "Samsung", "category_hint": "Televisores"},
        )
    finally:
        app.dependency_overrides.pop(get_enrich_use_case, None)
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "short_description": "Corta",
        "long_description": "Larga",
        "telegram_text": "Post",
        "category_id": "cat-tv",
        "subcategory_id": "sub-tv",
    }
