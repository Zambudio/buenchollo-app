"""Tests for the product preview use case."""

import pytest

from app.modules.products.application.preview_product_from_url import (
    PreviewProductFromUrlUseCase,
    ProductNotFoundError,
)
from app.modules.products.domain.entities import ProductPreview


class FakeProductProvider:
    """Small fake provider for use case tests."""

    def __init__(self, product: ProductPreview | None) -> None:
        self.product = product

    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None:
        return self.product


def test_preview_product_from_url_returns_product() -> None:
    product = ProductPreview(title="Producto Test", asin="B08TEST123")
    use_case = PreviewProductFromUrlUseCase(FakeProductProvider(product))

    result = use_case.execute("https://www.amazon.es/dp/B08TEST123")

    assert result is product


def test_preview_product_from_url_raises_not_found() -> None:
    use_case = PreviewProductFromUrlUseCase(FakeProductProvider(None))

    with pytest.raises(ProductNotFoundError):
        use_case.execute("https://www.amazon.es/dp/INVALID")

