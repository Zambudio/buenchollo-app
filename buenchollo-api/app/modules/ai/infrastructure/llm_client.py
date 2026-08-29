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

    # ── Métodos Síncronos ──────────────────────────────────────────────────────

    def generate_text(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> LLMGenerationResult:
        """Genera texto con selección de proveedor, reintento automático y fallback a OpenAI."""
        eff_temp = temperature if temperature is not None else self.settings.ai_temperature

        # 1. Si se solicita explícitamente OpenAI directo
        if provider == "openai":
            target_model = model or self.settings.openai_model or "gpt-4o"
            try:
                response = self.openai_sync_client.chat.completions.create(
                    model=target_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=eff_temp,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                content = (choice.message.content or "").strip()
                if content:
                    logger.info("Llamada directa a OpenAI oficial completada con éxito usando '%s'.", target_model)
                    return LLMGenerationResult(
                        content=content,
                        model=f"openai/{target_model}",
                        raw_response={"id": getattr(response, "id", "")},
                    )
            except Exception as exc:
                logger.error("Error al invocar OpenAI directo en generate_text: %s", exc)
                return LLMGenerationResult(content="", model=f"openai/{target_model}", raw_response={"error": str(exc)})

        # 2. Cascada estándar (OmniRoute / modelos gratuitos)
        models_to_try = self._get_model_cascade(model)
        max_empty_allowed = getattr(self.settings, "ai_max_empty_responses", 3)
        failure_count = 0
        last_exception: Exception | None = None

        for current_model in models_to_try:
            if failure_count >= max_empty_allowed:
                logger.warning(
                    "Se alcanzaron %d fallos/respuestas vacías con modelos gratuitos. Activando enrutamiento a OpenAI.",
                    failure_count,
                )
                break

            try:
                response = self.sync_client.chat.completions.create(
                    model=current_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=eff_temp,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                content = (choice.message.content or "").strip()

                if not content:
                    failure_count += 1
                    logger.warning(
                        "Modelo '%s' devolvió contenido vacío (%d/%d fallos/vacíos). Probando siguiente...",
                        current_model,
                        failure_count,
                        max_empty_allowed,
                    )
                    continue

                return LLMGenerationResult(
                    content=content,
                    model=current_model,
                    raw_response={"id": getattr(response, "id", "")},
                )
            except Exception as exc:
                failure_count += 1
                last_exception = exc
                logger.warning(
                    "Error al invocar modelo '%s' en generate_text (%d/%d fallos): %s. Probando siguiente...",
                    current_model,
                    failure_count,
                    max_empty_allowed,
                    exc,
                )

        # ── Fallback a OpenAI Oficial (si no está deshabilitado por provider="omniroute") ────────
        if self.has_openai_fallback and provider != "omniroute":
            target_model = self.settings.openai_model or "gpt-4o"
            logger.warning(
                "Modelos gratuitos fallaron o devolvieron respuestas vacías (%d fallos/vacíos). "
                "Enrutando llamada a OpenAI oficial con modelo '%s'...",
                failure_count,
                target_model,
            )
            try:
                response = self.openai_sync_client.chat.completions.create(
                    model=target_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=eff_temp,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                content = (choice.message.content or "").strip()
                if content:
                    logger.info("Llamada síncrona a OpenAI oficial completada con éxito usando '%s'.", target_model)
                    return LLMGenerationResult(
                        content=content,
                        model=f"openai/{target_model}",
                        raw_response={"id": getattr(response, "id", "")},
                    )
                logger.error("OpenAI oficial también devolvió respuesta vacía.")
            except Exception as exc:
                last_exception = exc
                logger.error("Error en fallback a OpenAI oficial: %s", exc)

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
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Genera un JSON estructurado con selección de proveedor, fallback y extracción tolerante."""
        eff_temp = temperature if temperature is not None else self.settings.ai_temperature

        # 1. Si se solicita explícitamente OpenAI directo
        if provider == "openai":
            target_model = model or self.settings.openai_model or "gpt-4o"
            try:
                kwargs: dict[str, Any] = {
                    "model": target_model,
                    "messages": messages,
                    "temperature": eff_temp,
                    "response_format": {"type": "json_object"},
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                response = self.openai_sync_client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                parsed = extract_json_payload(content)
                if isinstance(parsed, dict) and bool(parsed):
                    logger.info("Generación de JSON directo vía OpenAI oficial completada con éxito usando '%s'.", target_model)
                    return parsed
                if isinstance(parsed, list) and bool(parsed):
                    return {"items": parsed}
            except Exception as exc:
                logger.error("Error al generar JSON con OpenAI directo: %s", exc)
                return {}

        # 2. Cascada estándar (OmniRoute / modelos gratuitos)
        models_to_try = self._get_model_cascade(model)
        max_empty_allowed = getattr(self.settings, "ai_max_empty_responses", 3)
        failure_count = 0
        last_exception: Exception | None = None

        for current_model in models_to_try:
            if failure_count >= max_empty_allowed:
                logger.warning(
                    "Se alcanzaron %d fallos/JSONs vacíos con modelos gratuitos. Activando enrutamiento a OpenAI.",
                    failure_count,
                )
                break

            try:
                kwargs = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": eff_temp,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                try:
                    response = self.sync_client.chat.completions.create(
                        **kwargs,
                        response_format={"type": "json_object"},
                    )
                except Exception:
                    response = self.sync_client.chat.completions.create(**kwargs)

                content = response.choices[0].message.content or ""
                parsed = extract_json_payload(content)

                if isinstance(parsed, dict) and bool(parsed):
                    return parsed
                if isinstance(parsed, list) and bool(parsed):
                    return {"items": parsed}

                failure_count += 1
                logger.warning(
                    "Modelo '%s' devolvió texto no parseable a JSON o vacío: '%s' (%d/%d fallos). Intentando siguiente...",
                    current_model,
                    content[:100],
                    failure_count,
                    max_empty_allowed,
                )
            except Exception as exc:
                failure_count += 1
                last_exception = exc
                logger.warning(
                    "Error al generar JSON con modelo '%s' (%d/%d fallos): %s. Intentando siguiente...",
                    current_model,
                    failure_count,
                    max_empty_allowed,
                    exc,
                )

        # ── Fallback a OpenAI Oficial (si no está deshabilitado por provider="omniroute") ────────
        if self.has_openai_fallback and provider != "omniroute":
            target_model = self.settings.openai_model or "gpt-4o"
            logger.warning(
                "Modelos gratuitos fallaron o devolvieron JSON vacío (%d fallos/vacíos). "
                "Enrutando generación JSON a OpenAI oficial con modelo '%s'...",
                failure_count,
                target_model,
            )
            try:
                kwargs = {
                    "model": target_model,
                    "messages": messages,
                    "temperature": eff_temp,
                    "response_format": {"type": "json_object"},
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                response = self.openai_sync_client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                parsed = extract_json_payload(content)
                if isinstance(parsed, dict) and bool(parsed):
                    logger.info("Generación de JSON vía OpenAI oficial completada con éxito usando '%s'.", target_model)
                    return parsed
                if isinstance(parsed, list) and bool(parsed):
                    return {"items": parsed}
                logger.error("OpenAI oficial devolvió JSON no válido o vacío: '%s'", content[:100])
            except Exception as exc:
                last_exception = exc
                logger.error("Error en fallback JSON a OpenAI oficial: %s", exc)

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
        provider: str | None = None,
    ) -> LLMGenerationResult:
        """Genera texto de forma asíncrona con selección de proveedor y fallback a OpenAI."""
        eff_temp = temperature if temperature is not None else self.settings.ai_temperature

        # 1. Si se solicita explícitamente OpenAI directo
        if provider == "openai":
            target_model = model or self.settings.openai_model or "gpt-4o"
            try:
                response = await self.openai_async_client.chat.completions.create(
                    model=target_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=eff_temp,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                content = (choice.message.content or "").strip()
                if content:
                    logger.info("Llamada async directa a OpenAI oficial completada con éxito usando '%s'.", target_model)
                    return LLMGenerationResult(
                        content=content,
                        model=f"openai/{target_model}",
                        raw_response={"id": getattr(response, "id", "")},
                    )
            except Exception as exc:
                logger.error("Error al invocar OpenAI directo async en agenerate_text: %s", exc)
                return LLMGenerationResult(content="", model=f"openai/{target_model}", raw_response={"error": str(exc)})

        # 2. Cascada estándar (OmniRoute / modelos gratuitos)
        models_to_try = self._get_model_cascade(model)
        max_empty_allowed = getattr(self.settings, "ai_max_empty_responses", 3)
        failure_count = 0
        last_exception: Exception | None = None

        for current_model in models_to_try:
            if failure_count >= max_empty_allowed:
                logger.warning(
                    "Se alcanzaron %d fallos/respuestas vacías async con modelos gratuitos. Activando enrutamiento a OpenAI.",
                    failure_count,
                )
                break

            try:
                response = await self.async_client.chat.completions.create(
                    model=current_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=eff_temp,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                content = (choice.message.content or "").strip()

                if not content:
                    failure_count += 1
                    logger.warning(
                        "Modelo async '%s' devolvió contenido vacío (%d/%d fallos/vacíos). Probando siguiente...",
                        current_model,
                        failure_count,
                        max_empty_allowed,
                    )
                    continue

                return LLMGenerationResult(
                    content=content,
                    model=current_model,
                    raw_response={"id": getattr(response, "id", "")},
                )
            except Exception as exc:
                failure_count += 1
                last_exception = exc
                logger.warning(
                    "Error async al invocar modelo '%s' (%d/%d fallos): %s. Probando siguiente...",
                    current_model,
                    failure_count,
                    max_empty_allowed,
                    exc,
                )

        # ── Fallback a OpenAI Oficial (si no está deshabilitado por provider="omniroute") ────────
        if self.has_openai_fallback and provider != "omniroute":
            target_model = self.settings.openai_model or "gpt-4o"
            logger.warning(
                "Modelos gratuitos fallaron o devolvieron respuestas vacías async (%d fallos/vacíos). "
                "Enrutando llamada async a OpenAI oficial con modelo '%s'...",
                failure_count,
                target_model,
            )
            try:
                response = await self.openai_async_client.chat.completions.create(
                    model=target_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=eff_temp,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                content = (choice.message.content or "").strip()
                if content:
                    logger.info("Llamada async a OpenAI oficial completada con éxito usando '%s'.", target_model)
                    return LLMGenerationResult(
                        content=content,
                        model=f"openai/{target_model}",
                        raw_response={"id": getattr(response, "id", "")},
                    )
                logger.error("OpenAI oficial async también devolvió respuesta vacía.")
            except Exception as exc:
                last_exception = exc
                logger.error("Error async en fallback a OpenAI oficial: %s", exc)

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
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Genera JSON de forma asíncrona con selección de proveedor, fallback y extracción tolerante."""
        eff_temp = temperature if temperature is not None else self.settings.ai_temperature

        # 1. Si se solicita explícitamente OpenAI directo
        if provider == "openai":
            target_model = model or self.settings.openai_model or "gpt-4o"
            try:
                kwargs: dict[str, Any] = {
                    "model": target_model,
                    "messages": messages,
                    "temperature": eff_temp,
                    "response_format": {"type": "json_object"},
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                response = await self.openai_async_client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                parsed = extract_json_payload(content)
                if isinstance(parsed, dict) and bool(parsed):
                    logger.info("Generación JSON async directa vía OpenAI oficial completada con éxito usando '%s'.", target_model)
                    return parsed
                if isinstance(parsed, list) and bool(parsed):
                    return {"items": parsed}
            except Exception as exc:
                logger.error("Error async al generar JSON con OpenAI directo: %s", exc)
                return {}

        # 2. Cascada estándar (OmniRoute / modelos gratuitos)
        models_to_try = self._get_model_cascade(model)
        max_empty_allowed = getattr(self.settings, "ai_max_empty_responses", 3)
        failure_count = 0
        last_exception: Exception | None = None

        for current_model in models_to_try:
            if failure_count >= max_empty_allowed:
                logger.warning(
                    "Se alcanzaron %d fallos/JSONs vacíos async con modelos gratuitos. Activando enrutamiento a OpenAI.",
                    failure_count,
                )
                break

            try:
                kwargs = {
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

                if isinstance(parsed, dict) and bool(parsed):
                    return parsed
                if isinstance(parsed, list) and bool(parsed):
                    return {"items": parsed}

                failure_count += 1
                logger.warning(
                    "Modelo async '%s' devolvió texto no parseable a JSON o vacío: '%s' (%d/%d fallos). Intentando siguiente...",
                    current_model,
                    content[:100],
                    failure_count,
                    max_empty_allowed,
                )
            except Exception as exc:
                failure_count += 1
                last_exception = exc
                logger.warning(
                    "Error async al generar JSON con modelo '%s' (%d/%d fallos): %s. Intentando siguiente...",
                    current_model,
                    failure_count,
                    max_empty_allowed,
                    exc,
                )

        # ── Fallback a OpenAI Oficial (si no está deshabilitado por provider="omniroute") ────────
        if self.has_openai_fallback and provider != "omniroute":
            target_model = self.settings.openai_model or "gpt-4o"
            logger.warning(
                "Modelos gratuitos fallaron o devolvieron JSON vacío async (%d fallos/vacíos). "
                "Enrutando generación JSON async a OpenAI oficial con modelo '%s'...",
                failure_count,
                target_model,
            )
            try:
                kwargs = {
                    "model": target_model,
                    "messages": messages,
                    "temperature": eff_temp,
                    "response_format": {"type": "json_object"},
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                response = await self.openai_async_client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                parsed = extract_json_payload(content)
                if isinstance(parsed, dict) and bool(parsed):
                    logger.info("Generación JSON async vía OpenAI oficial completada con éxito usando '%s'.", target_model)
                    return parsed
                if isinstance(parsed, list) and bool(parsed):
                    return {"items": parsed}
                logger.error("OpenAI oficial async devolvió JSON no válido o vacío: '%s'", content[:100])
            except Exception as exc:
                last_exception = exc
                logger.error("Error async en fallback JSON a OpenAI oficial: %s", exc)

        logger.error("Todos los modelos fallaron al generar JSON async: %s", last_exception)
        return {}
