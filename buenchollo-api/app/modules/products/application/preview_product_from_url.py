"""Use case that builds a product preview from an Amazon URL or ASIN."""

from typing import Any, Protocol

from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.modules.products.domain.entities import ProductPreview


class ProductNotFoundError(NotFoundError):
    """Raised when the product cannot be resolved from the provided URL."""


class ProductProviderUnavailableError(ServiceUnavailableError):
    """Raised when the external product provider is not configured or unavailable."""


# ── Puertos (abstracciones del dominio/aplicación) ───────────────────────────

class ProductPreviewProvider(Protocol):
    """Port implemented by infrastructure adapters that fetch product previews."""

    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None:
        """Fetch and normalize product information."""


class CategoryClient(Protocol):
    """Port for fetching and formatting the category hierarchy."""

    def get_categories_hierarchy(self) -> list[dict[str, Any]]:
        """Return flat list of category dicts with id, name, parent_id."""

    def format_categories_for_prompt(self, categories: list[dict[str, Any]]) -> str:
        """Render the hierarchy as a human-readable string for an LLM prompt."""


class AIEnricher(Protocol):
    """Port for enriching product data with AI-generated text and categorization."""

    def enrich_product(self, product: ProductPreview, categories_prompt: str) -> dict[str, Any]:
        """Return a dict with AI-generated fields (short_description, category_id, …)."""


# ── Caso de uso ───────────────────────────────────────────────────────────────

class PreviewProductFromUrlUseCase:
    """Coordinate fetching product data, categorizing with AI and preparing response."""

    def __init__(
        self,
        product_provider: ProductPreviewProvider,
        category_client: CategoryClient,
        ai_assistant: AIEnricher,
    ) -> None:
        self.product_provider = product_provider
        self.category_client = category_client
        self.ai_assistant = ai_assistant

    def execute(self, url: str) -> ProductPreview:
        """Fetch from provider, then enrich with AI categorization."""
        product = self.product_provider.get_product_preview(url)
        if product is None:
            raise ProductNotFoundError("No se ha encontrado el producto de Amazon.")

        # Asegurarnos de que tenemos texto para que la IA trabaje
        if not product.description and product.features:
            product.description = " - ".join(product.features)

        # Sync categories from Supabase for the AI context
        categories = self.category_client.get_categories_hierarchy()
        categories_prompt = self.category_client.format_categories_for_prompt(categories)

        # Categorize and enrich with AI
        ai_data = self.ai_assistant.enrich_product(product, categories_prompt)
        
        # Merge AI data into the product entity
        if ai_data:
            # Categorización
            product.category_id = ai_data.get("category_id") or product.category_id
            product.subcategory_id = ai_data.get("subcategory_id") or product.subcategory_id
            
            # Textos persuasivos
            product.short_description = ai_data.get("short_description") or product.short_description
            product.long_description = ai_data.get("long_description") or ai_data.get("description") or product.long_description
            product.telegram_text = ai_data.get("telegram_text") or product.telegram_text
            
            # Metadatos
            if ai_data.get("expires_at"):
                product.expires_at = ai_data.get("expires_at")

        return product

