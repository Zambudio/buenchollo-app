"""Port protocols and abstract interfaces for the AI module."""

from typing import Any, Protocol

from app.modules.ai.domain.entities import LLMGenerationResult


class LLMClientProtocol(Protocol):
    """Low-level protocol for communicating with an LLM provider or gateway."""

    def generate_text(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> LLMGenerationResult:
        """Synchronously generate text using the primary model with automatic fallback."""

    def generate_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Synchronously generate and parse structured JSON with automatic fallback and markdown stripping."""

    async def agenerate_text(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> LLMGenerationResult:
        """Asynchronously generate text using the primary model with automatic fallback."""

    async def agenerate_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Asynchronously generate and parse structured JSON with automatic fallback and markdown stripping."""


class TelegramAIServiceProtocol(Protocol):
    """Port for generating and selecting hashtags/categories for Telegram publications."""

    async def suggest_categories(
        self,
        title: str,
        description: str,
        available: list[str],
    ) -> list[str]:
        """Select 1-2 matching hashtags from the available list using the AI engine."""

    async def generate_copy(
        self,
        title: str,
        details: str,
        provider: str | None = None,
    ) -> str | None:
        """Write the short sales line of a Telegram post (None if the AI engine fails)."""

