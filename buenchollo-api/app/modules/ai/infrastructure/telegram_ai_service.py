"""Telegram publication AI assistant for category/hashtag suggestion."""

import logging
import re
import unicodedata
from app.modules.ai.domain.ports import LLMClientProtocol

logger = logging.getLogger(__name__)


def _normalize_tag(tag: str) -> str:
    """Normaliza un hashtag para comparación insensible a mayúsculas, acentos y almohadilla."""
    clean = tag.strip().lstrip("#").lower()
    return "".join(c for c in unicodedata.normalize("NFD", clean) if unicodedata.category(c) != "Mn")


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

        # Mapa de búsqueda normalizada -> Categoría canónica oficial con su # y mayúsculas
        lookup = {_normalize_tag(cat): cat for cat in available}
        selected: list[str] = []
        seen: set[str] = set()

        try:
            cats_str = " ".join(available)
            prompt = (
                "Eres un clasificador taxonómico para un canal de ofertas tecnológicas en Telegram.\n"
                "Elige exactamente 1 o 2 hashtags que mejor describan el producto, seleccionando ÚNICAMENTE de la lista permitida.\n"
                "Responde únicamente con los 1 o 2 hashtags elegidos de la lista separados por un espacio (ejemplo: #Gaming #Auriculares).\n\n"
                f"LISTA DISPONIBLE:\n{cats_str}\n\n"
                f"PRODUCTO:\nTítulo: {title}\nDetalles: {description}"
            )
            messages = [
                {
                    "role": "system",
                    "content": "Eres un clasificador taxonómico conciso. Responde únicamente con 1 o 2 hashtags de la lista disponible, sin explicaciones ni texto adicional.",
                },
                {"role": "user", "content": prompt},
            ]

            result = await self.llm_client.agenerate_text(messages, temperature=0.2, max_tokens=200)
            raw = result.content.strip()

            # Extraer todas las palabras / hashtags devueltos por el modelo de forma tolerante
            tokens = re.findall(r"#?[A-Za-z0-9áéíóúÁÉÍÓÚñÑüÜ]+", raw)
            for token in tokens:
                norm = _normalize_tag(token)
                if norm in lookup:
                    canonical = lookup[norm]
                    if canonical not in seen:
                        seen.add(canonical)
                        selected.append(canonical)
                        if len(selected) >= 2:
                            break

        except Exception as exc:
            logger.warning("Error en TelegramAIService al sugerir categorías con IA: %s", exc)

        # Fallback de rescate heurístico si la IA no encontró coincidencias o falló
        if not selected:
            text_to_search = f"{title} {description}"
            title_norm = _normalize_tag(text_to_search)
            for norm_key, canonical in lookup.items():
                if len(norm_key) >= 4 and norm_key in title_norm:
                    if canonical not in seen:
                        seen.add(canonical)
                        selected.append(canonical)
                        if len(selected) >= 2:
                            break

        return selected
