"""Use case that builds a product preview from an Amazon URL or ASIN."""

from typing import Protocol

from app.modules.products.domain.entities import ProductPreview


class ProductNotFoundError(Exception):
    """Raised when the product cannot be resolved from the provided URL."""


class ProductProviderUnavailableError(Exception):
    """Raised when the external product provider is not configured or unavailable."""


class ProductPreviewProvider(Protocol):
    """Port implemented by infrastructure adapters that fetch product previews."""

    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None:
        """Fetch and normalize product information."""


class PreviewProductFromUrlUseCase:
    """Coordinate fetching product data and preparing the response model."""

    def __init__(self, product_provider: ProductPreviewProvider) -> None:
        self.product_provider = product_provider

    def execute(self, url: str) -> ProductPreview:
        """Return a product preview or raise a domain-level error."""
        product = self.product_provider.get_product_preview(url)
        if product is None:
            raise ProductNotFoundError("No se ha encontrado el producto de Amazon.")
        return product

