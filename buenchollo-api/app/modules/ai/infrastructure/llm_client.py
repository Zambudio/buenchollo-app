"""Unified OpenAI-compatible LLM client with automatic fallback and resilient JSON parsing."""

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI, OpenAI

from app.core.config import Settings
from app.modules.ai.domain.entities import LLMGenerationResult

logger = logging.getLogger(__name__)

# Regex para extraer bloques de código JSON o llaves JSON
_JSON_CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_JSON_OBJECT_PATTERN = re.compile(r"(\{[\s\S]*\})", re.DOTALL)
_JSON_ARRAY_PATTERN = re.compile(r"(\[[\s\S]*\])", re.DOTALL)


def extract_json_payload(raw_text: str) -> dict[str, Any] | list[Any] | None:
    """Extrae y parsea un objeto o array JSON de forma tolerante a fallos.

    Maneja markdown codeblocks (```json ... ```), texto explicativo antes/después,
    y comas finales sobrantes (trailing commas).
    """
    if not raw_text or not raw_text.strip():
        return None

    cleaned = raw_text.strip()

    # 1. Intentar parseo directo si ya es JSON puro
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 2. Extraer de bloque de código markdown ```json ... ```
    match_code = _JSON_CODE_BLOCK_PATTERN.search(cleaned)
    if match_code:
        candidate = match_code.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            cleaned = candidate  # Continuar saneando el contenido interior

    # 3. Extraer primer objeto {...} o array [...]
    match_obj = _JSON_OBJECT_PATTERN.search(cleaned)
    match_arr = _JSON_ARRAY_PATTERN.search(cleaned)

    target_str: str | None = None
    if match_obj and match_arr:
        # Elegir el que empiece antes
        target_str = match_obj.group(1) if match_obj.start() < match_arr.start() else match_arr.group(1)
    elif match_obj:
        target_str = match_obj.group(1)
    elif match_arr:
        target_str = match_arr.group(1)

    if target_str:
        try:
            return json.loads(target_str)
        except Exception:
            # 4. Limpieza defensiva de trailing commas: ,} o ,]
            sanitized = re.sub(r",\s*([\}\]])", r"\1", target_str)
            try:
                return json.loads(sanitized)
            except Exception:
                pass

    return None


class OpenAICompatibleLLMClient:
    """Agnostic LLM client connecting to OmniRoute, OpenCode, Groq, Ollama, OpenRouter or OpenAI.

    Provides automatic multi-model fallback when free models hit rate limits or encounter errors.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._sync_client: OpenAI | None = None
        self._async_client: AsyncOpenAI | None = None

    @property
    def sync_client(self) -> OpenAI:
        """Lazy initialization of the synchronous OpenAI-compatible client."""
        if self._sync_client is None:
            self._sync_client = OpenAI(
                base_url=self.settings.effective_ai_base_url,
                api_key=self.settings.effective_ai_api_key,
                timeout=self.settings.ai_timeout_seconds,
            )
        return self._sync_client

    @property
    def async_client(self) -> AsyncOpenAI:
        """Lazy initialization of the asynchronous OpenAI-compatible client."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                base_url=self.settings.effective_ai_base_url,
                api_key=self.settings.effective_ai_api_key,
                timeout=self.settings.ai_timeout_seconds,
            )
        return self._async_client

    def _get_model_cascade(self, requested_model: str | None = None) -> list[str]:
        """Calcula la secuencia de modelos en cascada: [principal] + [fallbacks]."""
        primary = requested_model or self.settings.effective_ai_model
        cascade = [primary]
        for fallback in self.settings.ai_fallback_models:
            if fallback and fallback not in cascade:
                cascade.append(fallback)
        return cascade

    # ── Métodos Síncronos ──────────────────────────────────────────────────────

    def generate_text(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMGenerationResult:
        """Genera texto con reintento automático en cascada entre modelos gratuitos."""
        models_to_try = self._get_model_cascade(model)
        eff_temp = temperature if temperature is not None else self.settings.ai_temperature
        last_exception: Exception | None = None

        for current_model in models_to_try:
            try:
                response = self.sync_client.chat.completions.create(
                    model=current_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=eff_temp,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                content = choice.message.content or ""
                return LLMGenerationResult(
                    content=content,
                    model=current_model,
                    raw_response={"id": getattr(response, "id", "")},
                )
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Error al invocar modelo '%s' en generate_text: %s. Probando siguiente fallback...",
                    current_model,
                    exc,
                )

        logger.error("Todos los modelos de IA configurados fallaron en generate_text: %s", last_exception)
        return LLMGenerationResult(
            content="",
            model=models_to_try[0] if models_to_try else "none",
            raw_response={"error": str(last_exception)},
        )

    def generate_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Genera un JSON estructurado con fallback automático y extracción tolerante."""
        models_to_try = self._get_model_cascade(model)
        eff_temp = temperature if temperature is not None else self.settings.ai_temperature
        last_exception: Exception | None = None

        for current_model in models_to_try:
            try:
                # Intentamos con response_format json_object si el modelo lo soporta,
                # si no, el parser extract_json_payload rescatará el resultado
                kwargs: dict[str, Any] = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": eff_temp,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                # Algunos endpoints / modelos gratuitos no aceptan response_format estricto,
                # pero los gateways como OmniRoute o Groq sí. Si falla con json_object,
                # el bloque except probará sin él o con el siguiente modelo.
                try:
                    response = self.sync_client.chat.completions.create(
                        **kwargs,
                        response_format={"type": "json_object"},
                    )
                except Exception:
                    response = self.sync_client.chat.completions.create(**kwargs)

                content = response.choices[0].message.content or ""
                parsed = extract_json_payload(content)
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list):
                    return {"items": parsed}

                logger.warning(
                    "Modelo '%s' devolvió texto no parseable a JSON: '%s'. Intentando fallback...",
                    current_model,
                    content[:100],
                )
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Error al generar JSON con modelo '%s': %s. Intentando fallback...",
                    current_model,
                    exc,
                )

        logger.error("Todos los modelos fallaron al generar JSON estructurado: %s", last_exception)
        return {}

    # ── Métodos Asíncronos ─────────────────────────────────────────────────────

    async def agenerate_text(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMGenerationResult:
        """Genera texto de forma asíncrona con reintento automático en cascada."""
        models_to_try = self._get_model_cascade(model)
        eff_temp = temperature if temperature is not None else self.settings.ai_temperature
        last_exception: Exception | None = None

        for current_model in models_to_try:
            try:
                response = await self.async_client.chat.completions.create(
                    model=current_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=eff_temp,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                content = choice.message.content or ""
                return LLMGenerationResult(
                    content=content,
                    model=current_model,
                    raw_response={"id": getattr(response, "id", "")},
                )
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Error async al invocar modelo '%s': %s. Probando siguiente fallback...",
                    current_model,
                    exc,
                )

        logger.error("Todos los modelos fallaron en agenerate_text: %s", last_exception)
        return LLMGenerationResult(
            content="",
            model=models_to_try[0] if models_to_try else "none",
            raw_response={"error": str(last_exception)},
        )

    async def agenerate_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Genera JSON de forma asíncrona con fallback automático y extracción tolerante."""
        models_to_try = self._get_model_cascade(model)
        eff_temp = temperature if temperature is not None else self.settings.ai_temperature
        last_exception: Exception | None = None

        for current_model in models_to_try:
            try:
                kwargs: dict[str, Any] = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": eff_temp,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                try:
                    response = await self.async_client.chat.completions.create(
                        **kwargs,
                        response_format={"type": "json_object"},
                    )
                except Exception:
                    response = await self.async_client.chat.completions.create(**kwargs)

                content = response.choices[0].message.content or ""
                parsed = extract_json_payload(content)
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list):
                    return {"items": parsed}

                logger.warning(
                    "Modelo async '%s' devolvió texto no parseable a JSON: '%s'. Intentando fallback...",
                    current_model,
                    content[:100],
                )
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Error async al generar JSON con modelo '%s': %s. Intentando fallback...",
                    current_model,
                    exc,
                )

        logger.error("Todos los modelos fallaron al generar JSON async: %s", last_exception)
        return {}
