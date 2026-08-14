"""Port protocols and abstract interfaces for the AI module."""

from typing import Any, Protocol

from app.modules.ai.domain.entities import (
    AIChatMessage,
    AIChatResponse,
    AIProductEnrichment,
    LLMGenerationResult,
)


class LLMClientProtocol(Protocol):
    """Low-level protocol for communicating with an LLM provider or gateway."""

    def generate_text(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMGenerationResult:
        """Synchronously generate text using the primary model with automatic fallback."""

    def generate_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Synchronously generate and parse structured JSON with automatic fallback and markdown stripping."""

    async def agenerate_text(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMGenerationResult:
        """Asynchronously generate text using the primary model with automatic fallback."""

    async def agenerate_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Asynchronously generate and parse structured JSON with automatic fallback and markdown stripping."""


class ProductEnricherProtocol(Protocol):
    """Port for generating copywriting and assigning categories to a product."""

    def enrich_product(
        self,
        product: Any,
        categories_prompt: str,
    ) -> dict[str, Any]:
        """Generate short_description, long_description, telegram_text, category_id, subcategory_id."""


class TelegramAIServiceProtocol(Protocol):
    """Port for generating and selecting hashtags/categories for Telegram publications."""

    async def suggest_categories(
        self,
        title: str,
        description: str,
        available: list[str],
    ) -> list[str]:
        """Select 1-2 matching hashtags from the available list using the AI engine."""


class DealRecommenderProtocol(Protocol):
    """Port for conversational product and deal recommendation (Chatbot)."""

    async def chat(
        self,
        messages: list[AIChatMessage],
        deals_context: list[dict[str, Any]] | None = None,
    ) -> AIChatResponse:
        """Generate conversational recommendation response with contextual deal matches."""
