"""Enriquecimiento con IA de un producto ya importado (Awin / Tradedoubler).

Mismo copywriting y categorización que el autocompletado de Amazon, pero a
partir de los datos del catálogo: sin llamar a Amazon ni a la tienda.
"""

from unittest.mock import MagicMock

import pytest

from app.core.security import require_admin
from app.main import app
from app.modules.ai.domain.entities import COPY_FALLBACK_KEY
from app.modules.products.api.router import get_enrich_use_case
from app.modules.products.application.preview_product_from_url import (
    SUMMARY_MAX_CHARS,
    EnrichProductUseCase,
    summarize_text,
)

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
        assert product.copy_ok is True
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

    def test_real_enricher_fallback_is_not_used_as_copy(self):
        # Lo que devuelve de verdad ProductAIEnricher cuando la IA cae: título
        # recortado y la descripción tal cual, con la marca de rescate.
        use_case, ai = _use_case({})
        ai.enrich_product.side_effect = lambda product, *_a, **_k: {
            "short_description": product.title[:80],
            "telegram_text": product.title[:140],
            "long_description": product.description,
            COPY_FALLBACK_KEY: True,
        }
        sentence = "El panel Mini LED ofrece un contraste muy alto y colores vivos en cualquier escena. "
        product = use_case.execute(title="Samsung M70H", description=sentence * 30, category_hint="Televisores")
        assert product.copy_ok is False
        assert product.short_description == ""
        assert product.telegram_text == ""
        assert len(product.long_description) <= SUMMARY_MAX_CHARS
        assert product.long_description.startswith("El panel Mini LED")  # sin la pista de categoría
        assert product.long_description.endswith(".")

    def test_exception_fallback_is_not_used_as_copy(self):
        use_case, _ = _use_case(
            {
                "short_description": "Gran oferta tecnológica",
                "long_description": "Detalles y especificaciones en la tienda oficial.",
                "telegram_text": "Oferta destacada en Amazon",
                COPY_FALLBACK_KEY: True,
            }
        )
        product = use_case.execute(title="X", description="Tele 4K")
        assert product.copy_ok is False
        assert product.long_description == "Tele 4K"
        assert "Amazon" not in product.telegram_text

    def test_no_category_when_ai_does_not_classify(self):
        # Nada de «Varios» por defecto: el editor elige.
        use_case, _ = _use_case({"short_description": "Algo", "telegram_text": "Algo"})
        product = use_case.execute(title="Cosa rara", description="")
        assert (product.category_id, product.subcategory_id) == (None, None)

    def test_unknown_category_is_dropped_and_missing_subcategory_is_completed(self):
        use_case, _ = _use_case({"short_description": "A", "category_id": "no-existe"})
        assert use_case.execute(title="X").category_id is None
        use_case, _ = _use_case({"short_description": "A", "category_id": "cat-tv", "subcategory_id": "otra"})
        product = use_case.execute(title="X")
        assert (product.category_id, product.subcategory_id) == ("cat-tv", "sub-tv")

    def test_summarize_never_exceeds_the_limit(self):
        assert len(summarize_text("palabra " * 200, max_len=50)) <= 50
        long_word = "x" * 600  # una URL o un código sin espacios
        out = summarize_text(long_word, max_len=500)
        assert len(out) <= 500
        assert out.endswith("…")

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
        "copy_ok": True,
    }
