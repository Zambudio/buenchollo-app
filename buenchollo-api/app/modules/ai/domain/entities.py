"""Domain entities for the unified AI engine."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AIProductEnrichment:
    """Structured result of product copywriting and categorization."""

    short_description: str = ""
    long_description: str = ""
    telegram_text: str = ""
    category_id: str | None = None
    subcategory_id: str | None = None
    expires_at: str | None = None
    model_used: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AIChatMessage:
    """Single message in a conversational LLM interaction."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True, slots=True)
class AIChatResponse:
    """Response returned by conversational assistants (such as the deal recommender chatbot)."""

    content: str
    suggested_deals: list[dict[str, Any]] = field(default_factory=list)
    model_used: str = ""
    finish_reason: str = "stop"


@dataclass(frozen=True, slots=True)
class LLMGenerationResult:
    """Low-level result returned by the LLM client."""

    content: str
    model: str
    parsed_json: dict[str, Any] | list[Any] | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
