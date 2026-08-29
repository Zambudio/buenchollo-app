"""AI assistant adapter for product categorization and text generation."""

import logging
from typing import Any

from app.core.config import Settings
from app.modules.ai.infrastructure.llm_client import OpenAICompatibleLLMClient
from app.modules.ai.infrastructure.product_enricher import ProductAIEnricher
from app.modules.products.domain.entities import ProductPreview

logger = logging.getLogger(__name__)


class OpenAIAssistant:
    """Uses the unified AI engine (OmniRoute, free models, or OpenAI fallback) to enrich products."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._llm_client = OpenAICompatibleLLMClient(settings)
        self._enricher = ProductAIEnricher(self._llm_client)

    def enrich_product(
        self,
        product: ProductPreview,
        categories_prompt: str,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Enrich product preview with copywriting and categorization."""
        return self._enricher.enrich_product(product, categories_prompt, provider=provider)

