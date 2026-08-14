"""Conversational deal and product recommender assistant (Web Chatbot core)."""

import json
import logging
from typing import Any

from app.modules.ai.domain.entities import AIChatMessage, AIChatResponse
from app.modules.ai.domain.ports import LLMClientProtocol

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = """
Eres el Asistente Virtual Inteligente de "BuenCholloTech", una plataforma líder en España en detección de ofertas y chollos verificados.
Tu misión es asesorar y recomendar a los usuarios las mejores ofertas disponibles según sus necesidades, gustos y presupuesto.

Pautas de comportamiento:
1. Sé amable, conciso, cercano y profesional.
2. Si el usuario te pide una recomendación (ej: "un móvil por menos de 300€", "auriculares con cancelación de ruido"), analiza las ofertas disponibles en el contexto y recomiéndale las 2-3 mejores opciones explicando brevemente por qué son un chollo.
3. Si en el contexto hay ofertas relevantes, menciona claramente el nombre del producto, el precio rebajado y el porcentaje de descuento o ahorro.
4. Si no hay ofertas exactas en el contexto, sugiere pautas útiles de compra y anima al usuario a crear una alerta de precio en la web.
5. Mantén respuestas estructuradas, fáciles de leer en dispositivos móviles (usa viñetas y negritas).
"""


class DealRecommenderAssistant:
    """Conversational assistant powering the web chatbot for intelligent deal recommendations."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self.llm_client = llm_client
        self.system_prompt = system_prompt

    async def chat(
        self,
        messages: list[AIChatMessage],
        deals_context: list[dict[str, Any]] | None = None,
    ) -> AIChatResponse:
        """Process conversational history and generate a tailored recommendation."""
        system_content = self.system_prompt

        if deals_context:
            serialized_deals = json.dumps(deals_context[:10], ensure_ascii=False)
            system_content += f"\n\nOFERTAS Y CHOLLOS ACTIVOS EN LA WEB DISPONIBLES:\n{serialized_deals}"

        payload_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_content},
        ]

        for msg in messages:
            payload_messages.append({"role": msg.role, "content": msg.content})

        try:
            result = await self.llm_client.agenerate_text(payload_messages, temperature=0.3)
            return AIChatResponse(
                content=result.content,
                model_used=result.model,
                suggested_deals=deals_context[:5] if deals_context else [],
            )
        except Exception as exc:
            logger.error("Error en DealRecommenderAssistant: %s", exc)
            return AIChatResponse(
                content="Lo siento, en este momento no puedo procesar tu consulta. Por favor, intenta de nuevo en unos instantes.",
                model_used="error",
                finish_reason="error",
            )
