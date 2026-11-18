"""Unified OpenAI-compatible LLM client with automatic fallback and resilient JSON parsing."""

import json
import logging
import re
from dataclasses import dataclass
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

    Provides automatic multi-model fallback when free models hit rate limits, return empty responses,
    or encounter errors, routing to official OpenAI API after a configured threshold of empty/failed attempts.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._sync_client: OpenAI | None = None
        self._async_client: AsyncOpenAI | None = None
        self._openai_sync_client: OpenAI | None = None
        self._openai_async_client: AsyncOpenAI | None = None

    @property
    def sync_client(self) -> OpenAI:
        """Lazy initialization of the primary synchronous OpenAI-compatible client.
        
        Uses max_retries=0 and a short timeout so that failing free models immediately
        cascade to the next model or trigger OpenAI fallback instead of stalling the request.
        """
        if self._sync_client is None:
            fast_free_timeout = min(self.settings.ai_timeout_seconds, 3.5)
            self._sync_client = OpenAI(
                base_url=self.settings.effective_ai_base_url,
                api_key=self.settings.effective_ai_api_key,
                timeout=fast_free_timeout,
                max_retries=0,
            )
        return self._sync_client

    @property
    def async_client(self) -> AsyncOpenAI:
        """Lazy initialization of the primary asynchronous OpenAI-compatible client."""
        if self._async_client is None:
            fast_free_timeout = min(self.settings.ai_timeout_seconds, 3.5)
            self._async_client = AsyncOpenAI(
                base_url=self.settings.effective_ai_base_url,
                api_key=self.settings.effective_ai_api_key,
                timeout=fast_free_timeout,
                max_retries=0,
            )
        return self._async_client

    @property
    def openai_sync_client(self) -> OpenAI:
        """Lazy initialization of the official OpenAI synchronous fallback client."""
        if self._openai_sync_client is None:
            self._openai_sync_client = OpenAI(
                base_url="https://api.openai.com/v1",
                api_key=self.settings.openai_api_key,
                timeout=self.settings.ai_timeout_seconds,
                max_retries=1,
            )
        return self._openai_sync_client

    @property
    def openai_async_client(self) -> AsyncOpenAI:
        """Lazy initialization of the official OpenAI asynchronous fallback client."""
        if self._openai_async_client is None:
            self._openai_async_client = AsyncOpenAI(
                base_url="https://api.openai.com/v1",
                api_key=self.settings.openai_api_key,
                timeout=self.settings.ai_timeout_seconds,
                max_retries=1,
            )
        return self._openai_async_client

    @property
    def has_openai_fallback(self) -> bool:
        """Indicates whether official OpenAI fallback is available."""
        if not self.settings.openai_api_key:
            return False
        is_already_openai_direct = (
            self.settings.ai_provider == "openai"
            or "api.openai.com" in self.settings.effective_ai_base_url
        )
        return not is_already_openai_direct

    def _get_model_cascade(self, requested_model: str | None = None) -> list[str]:
        """Calcula la secuencia de modelos en cascada: [principal] + [fallbacks]."""
        primary = requested_model or self.settings.effective_ai_model
        cascade = [primary]
        for fallback in self.settings.ai_fallback_models:
            if fallback and fallback not in cascade:
                cascade.append(fallback)
        return cascade

    def _plan(self, model: str | None, provider: str | None) -> tuple[list["_Attempt"], str]:
        """Intentos en orden y modelo a informar si todos fallan.

        - provider="openai": solo OpenAI oficial; nunca la cascada gratuita.
        - Resto: cascada de modelos gratuitos hasta `ai_max_empty_responses`
          fallos/respuestas vacías y, si hay clave de OpenAI y no se pidió
          provider="omniroute", un último intento con OpenAI oficial.
        """
        if provider == "openai":
            target = model or self.settings.openai_model
            return [_Attempt(target, official=True)], f"openai/{target}"

        cascade = self._get_model_cascade(model)
        limit = max(self.settings.ai_max_empty_responses, 0)
        attempts = [_Attempt(m, official=False) for m in cascade[:limit]]
        if self.has_openai_fallback and provider != "omniroute":
            attempts.append(_Attempt(self.settings.openai_model, official=True))
        return attempts, cascade[0] if cascade else "none"

    def _steps(self, messages, model, temperature, max_tokens, provider, json_mode):
        """Algoritmo de cascada sin E/S, compartido por la variante síncrona y la
        asíncrona: produce `(oficial, kwargs)` de cada llamada a hacer y recibe
        la respuesta con `send` o el error con `throw`. El resultado final sale
        en `StopIteration.value`."""
        attempts, label = self._plan(model, provider)
        last_error: Exception | None = None
        for position, attempt in enumerate(attempts):
            if attempt.official and position > 0:
                logger.warning(
                    "Modelos gratuitos fallaron o devolvieron respuestas vacías (%d). "
                    "Enrutando a OpenAI oficial con modelo '%s'...",
                    position,
                    attempt.model,
                )
            try:
                response = yield from self._call(attempt, messages, temperature, max_tokens, json_mode)
                result = self._accept(attempt, response, json_mode)
            except Exception as exc:
                last_error = exc
                logger.warning("Error al invocar el modelo '%s': %s", attempt.label, exc)
                continue
            if result is not None:
                if attempt.official:
                    logger.info("OpenAI oficial completó la llamada con '%s'.", attempt.model)
                return result

        logger.error("Todos los modelos de IA configurados fallaron (%s): %s", label, last_error)
        if json_mode:
            return {}
        return LLMGenerationResult(content="", model=label, raw_response={"error": str(last_error)})

    def _call(self, attempt: "_Attempt", messages, temperature, max_tokens, json_mode: bool):
        kwargs: dict[str, Any] = {
            "model": attempt.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.settings.ai_temperature,
        }
        # Texto: max_tokens siempre (también None). JSON: solo si viene informado.
        if not json_mode or max_tokens:
            kwargs["max_tokens"] = max_tokens
        if not json_mode:
            return (yield attempt.official, kwargs)
        with_format = {**kwargs, "response_format": {"type": "json_object"}}
        if attempt.official:
            return (yield attempt.official, with_format)
        try:
            return (yield attempt.official, with_format)
        except Exception:
            # Algunos modelos de la pasarela no aceptan response_format.
            return (yield attempt.official, kwargs)

    @staticmethod
    def _accept(attempt: "_Attempt", response: Any, json_mode: bool) -> LLMGenerationResult | dict[str, Any] | None:
        """Resultado de una respuesta útil, o None si viene vacía / sin JSON."""
        raw = response.choices[0].message.content or ""
        if json_mode:
            parsed = extract_json_payload(raw)
            if isinstance(parsed, dict) and parsed:
                return parsed
            if isinstance(parsed, list) and parsed:
                return {"items": parsed}
            logger.warning("Modelo '%s' devolvió JSON vacío o no parseable: '%s'", attempt.label, raw[:100])
            return None
        content = raw.strip()
        if not content:
            logger.warning("Modelo '%s' devolvió contenido vacío.", attempt.label)
            return None
        return LLMGenerationResult(
            content=content,
            model=attempt.label,
            raw_response={"id": getattr(response, "id", "")},
        )

    def _run_sync(self, *args):
        steps = self._steps(*args)
        try:
            official, kwargs = next(steps)
            while True:
                client = self.openai_sync_client if official else self.sync_client
                try:
                    response = client.chat.completions.create(**kwargs)
                except Exception as exc:
                    official, kwargs = steps.throw(exc)
                else:
                    official, kwargs = steps.send(response)
        except StopIteration as done:
            return done.value

    async def _run_async(self, *args):
        steps = self._steps(*args)
        try:
            official, kwargs = next(steps)
            while True:
                client = self.openai_async_client if official else self.async_client
                try:
                    response = await client.chat.completions.create(**kwargs)
                except Exception as exc:
                    official, kwargs = steps.throw(exc)
                else:
                    official, kwargs = steps.send(response)
        except StopIteration as done:
            return done.value

    # ── API pública ────────────────────────────────────────────────────────────

    def generate_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Genera un JSON estructurado con selección de proveedor, fallback y extracción tolerante."""
        return self._run_sync(messages, model, temperature, max_tokens, provider, True)

    async def agenerate_text(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> LLMGenerationResult:
        """Genera texto de forma asíncrona con selección de proveedor y fallback a OpenAI."""
        return await self._run_async(messages, model, temperature, max_tokens, provider, False)


@dataclass(frozen=True)
class _Attempt:
    model: str
    official: bool  # True: api.openai.com; False: pasarela (OmniRoute u otra compatible)

    @property
    def label(self) -> str:
        return f"openai/{self.model}" if self.official else self.model
