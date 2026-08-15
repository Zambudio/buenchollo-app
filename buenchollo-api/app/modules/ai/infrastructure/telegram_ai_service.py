"""Telegram publication AI assistant for category/hashtag suggestion."""

import logging
from app.modules.ai.domain.ports import LLMClientProtocol

logger = logging.getLogger(__name__)


class TelegramAIService:
    """Provides AI-powered hashtag and categorization suggestions for Telegram deals."""

    def __init__(self, llm_client: LLMClientProtocol) -> None:
        self.llm_client = llm_client

    async def suggest_categories(
        self,
        title: str,
        description: str,
        available: list[str],
    ) -> list[str]:
        """Llama al motor de IA para elegir 1-2 hashtags pertinentes del catálogo disponible."""
        if not available:
            return []

        try:
            cats_str = " ".join(available)
            prompt = (
                "Elige 1 o 2 hashtags de esta lista que mejor describan el producto.\n"
                "Solo puedes usar hashtags de la lista. Responde solo con los hashtags separados por espacio.\n\n"
                f"Lista disponible: {cats_str}\n"
                f"Producto: {title}\n{description}"
            )
            messages = [
                {"role": "system", "content": "Solo puedes responder con las categorías proporcionadas de la lista. No incluyas explicaciones."},
                {"role": "user", "content": prompt},
            ]

            result = await self.llm_client.agenerate_text(messages, temperature=0.2, max_tokens=500)
            raw = result.content.strip()
            tokens = raw.replace(",", " ").split()
            allowed = set(available)
            selected = [t for t in tokens if t in allowed][:2]
            return selected

        except Exception as exc:
            logger.warning("Error en TelegramAIService al sugerir categorías: %s", exc)
            return []
