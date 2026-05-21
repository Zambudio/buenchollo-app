"""Tests for the product preview use case."""

import pytest

from app.modules.products.application.preview_product_from_url import (
    PreviewProductFromUrlUseCase,
    ProductNotFoundError,
)
from app.modules.products.domain.entities import ProductPreview


from unittest.mock import MagicMock


class FakeProductProvider:
    """Small fake provider for use case tests."""

    def __init__(self, product: ProductPreview | None) -> None:
        self.product = product

    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None:
        return self.product


def _make_use_case(product):
    category_client = MagicMock()
    category_client.get_categories_hierarchy.return_value = []
    category_client.format_categories_for_prompt.return_value = ""
    ai_assistant = MagicMock()
    ai_assistant.enrich_product.return_value = {}
    return PreviewProductFromUrlUseCase(FakeProductProvider(product), category_client, ai_assistant)


def test_preview_product_from_url_returns_product() -> None:
    product = ProductPreview(title="Producto Test", asin="B08TEST123")
    use_case = _make_use_case(product)

    result = use_case.execute("https://www.amazon.es/dp/B08TEST123")

    assert result is product


def test_preview_product_from_url_raises_not_found() -> None:
    use_case = _make_use_case(None)

    with pytest.raises(ProductNotFoundError):
        use_case.execute("https://www.amazon.es/dp/INVALID")

