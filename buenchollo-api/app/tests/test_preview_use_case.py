"""
Tests unitarios para PreviewProductFromUrlUseCase.

Todos los colaboradores externos (Amazon, Supabase, OpenAI) están mockeados
mediante unittest.mock — no se realiza ninguna llamada de red.
"""

import unittest
from unittest.mock import MagicMock

from app.modules.products.application.preview_product_from_url import (
    PreviewProductFromUrlUseCase,
    ProductNotFoundError,
)
from app.modules.products.domain.entities import ProductPreview


def _make_use_case(product=None, categories=None, ai_data=None):
    """Construye el use case con mocks configurables."""
    provider = MagicMock()
    provider.get_product_preview.return_value = product

    category_client = MagicMock()
    category_client.get_categories_hierarchy.return_value = categories or []
    category_client.format_categories_for_prompt.return_value = "cat_prompt"

    ai_assistant = MagicMock()
    ai_assistant.enrich_product.return_value = ai_data or {}

    return PreviewProductFromUrlUseCase(provider, category_client, ai_assistant), provider, category_client, ai_assistant


class TestPreviewProductFromUrlUseCase(unittest.TestCase):

    def test_raises_product_not_found_when_provider_returns_none(self):
        use_case, _, _, _ = _make_use_case(product=None)

        with self.assertRaises(ProductNotFoundError):
            use_case.execute("https://amazon.es/dp/B000INVALID")

    def test_returns_product_when_provider_succeeds(self):
        product = ProductPreview(asin="B001234567", title="Teclado mecánico", current_price=49.99)
        use_case, _, _, _ = _make_use_case(product=product)

        result = use_case.execute("https://amazon.es/dp/B001234567")

        self.assertEqual(result.title, "Teclado mecánico")
        self.assertEqual(result.current_price, 49.99)

    def test_ai_enrichment_sets_category_and_descriptions(self):
        product = ProductPreview(asin="B001234567", title="Ratón gaming")
        ai_data = {
            "category_id": "cat-123",
            "subcategory_id": "sub-456",
            "short_description": "Ratón gaming RGB",
            "long_description": "Descripcion larga del raton",
            "telegram_text": "🔥 Oferta: Ratón gaming",
        }
        use_case, _, _, _ = _make_use_case(product=product, ai_data=ai_data)

        result = use_case.execute("https://amazon.es/dp/B001234567")

        self.assertEqual(result.category_id, "cat-123")
        self.assertEqual(result.subcategory_id, "sub-456")
        self.assertEqual(result.short_description, "Ratón gaming RGB")
        self.assertEqual(result.long_description, "Descripcion larga del raton")
        self.assertEqual(result.telegram_text, "🔥 Oferta: Ratón gaming")

    def test_existing_description_preserved_when_ai_returns_empty(self):
        product = ProductPreview(asin="B001234567", title="SSD", short_description="Original")
        use_case, _, _, _ = _make_use_case(product=product, ai_data={})

        result = use_case.execute("https://amazon.es/dp/B001234567")

        self.assertEqual(result.short_description, "Original")

    def test_features_joined_as_description_when_description_empty(self):
        product = ProductPreview(
            asin="B001234567",
            title="Monitor 4K",
            description="",
            features=["4K UHD", "144Hz", "1ms"],
        )
        use_case, provider, _, _ = _make_use_case(product=product)

        use_case.execute("https://amazon.es/dp/B001234567")

        # El use case modifica product.description antes de llamar al enricher
        enriched_product = provider.get_product_preview.return_value
        self.assertEqual(enriched_product.description, "4K UHD - 144Hz - 1ms")

    def test_categories_are_fetched_and_passed_to_ai(self):
        product = ProductPreview(asin="B001234567", title="Auriculares")
        categories = [{"id": "cat-1", "name": "Sonido", "parent_id": None}]
        use_case, _, category_client, ai_assistant = _make_use_case(
            product=product, categories=categories
        )

        use_case.execute("https://amazon.es/dp/B001234567")

        category_client.get_categories_hierarchy.assert_called_once()
        category_client.format_categories_for_prompt.assert_called_once_with(categories)
        ai_assistant.enrich_product.assert_called_once()

    def test_ai_expires_at_is_applied(self):
        product = ProductPreview(asin="B001234567", title="Oferta Flash")
        ai_data = {"expires_at": "2026-12-31T23:59:59"}
        use_case, _, _, _ = _make_use_case(product=product, ai_data=ai_data)

        result = use_case.execute("https://amazon.es/dp/B001234567")

        self.assertEqual(result.expires_at, "2026-12-31T23:59:59")

    def test_provider_is_called_with_original_url(self):
        product = ProductPreview(asin="B001234567", title="Webcam")
        use_case, provider, _, _ = _make_use_case(product=product)
        url = "https://amazon.es/dp/B001234567?tag=buenchollo0b-21"

        use_case.execute(url)

        provider.get_product_preview.assert_called_once_with(url)
