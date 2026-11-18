"""Domain entities for the unified AI engine."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LLMGenerationResult:
    """Low-level result returned by the LLM client."""

    content: str
    model: str
    parsed_json: dict[str, Any] | list[Any] | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
