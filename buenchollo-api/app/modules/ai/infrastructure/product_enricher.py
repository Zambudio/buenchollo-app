"""Product copywriting and categorization enricher using the unified AI engine."""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from app.modules.ai.domain.ports import LLMClientProtocol

logger = logging.getLogger(__name__)


class ProductAIEnricher:
    """Enriches product preview data with persuasive copywriting and automatic categorization."""

    def __init__(self, llm_client: LLMClientProtocol) -> None:
        self.llm_client = llm_client

    def enrich_product(self, product: Any, categories_prompt: str) -> dict[str, Any]:
        """Generate short description, markdown long description, telegram text and categories."""
        try:
            # Copywriting y categorización son independientes (no comparten datos de
            # salida): se lanzan en paralelo para no sumar sus latencias, ya que cada
            # llamada al motor de IA puede tardar varios segundos con modelos gratuitos.
            with ThreadPoolExecutor(max_workers=2) as executor:
                copy_future = executor.submit(self._get_copywriting, product)
                cat_future = executor.submit(
                    self._get_categorization, getattr(product, "title", ""), categories_prompt
                )
                copy_data = copy_future.result()
                cat_data = cat_future.result()

            return {**copy_data, **cat_data}

        except Exception as exc:
            logger.error("Error crítico en ProductAIEnricher: %s", exc)
            return {
                "short_description": f"⚠️ Error IA: {str(exc)[:50]}",
                "long_description": "Hubo un error al generar los textos. Revisa la configuración del motor de IA.",
            }

    def _get_copywriting(self, product: Any) -> dict[str, Any]:
        today = datetime.now().strftime("%Y-%m-%d")
        title = getattr(product, "title", "")
        description = getattr(product, "description", "")

        prompt = f"""
Eres un redactor y copywriter de ventas experto para el portal "BuenCholloTech". Hoy es {today}.
Genera un JSON con exactamente estos tres campos para el producto:

1. "short_description": eslogan corto y directo (máx 10 palabras, sin emojis). Ej: "Portátil gaming ultraligero con pantalla OLED de 165Hz".
2. "long_description": descripción detallada para la web en formato Markdown.
   - Usa negritas (**texto**) y viñetas (•) para destacar especificaciones y beneficios clave.
   - Máximo 4-6 puntos destacados y persuasivos.
3. "telegram_text": texto conciso para publicar en el canal de Telegram de ofertas.
   - Máximo 2-3 líneas.
   - Sin markdown, sin viñetas, sin listas.
   - Resume en tono de venta el producto y su beneficio principal (para qué sirve, qué lo hace bueno).
   - NO añadas frases de cierre tipo llamada a la acción ni de urgencia (prohibido: "hazte con el tuyo",
     "no te lo pierdas", "antes de que se agote", "cómpralo ya", "corre a por él", "consíguelo rápido",
     o cualquier variante). El precio, el enlace y la urgencia ya los añade la plantilla del post, no el texto.

PRODUCTO: {title}
INFORMACIÓN / CARACTERÍSTICAS: {description}

Responde SOLO un objeto JSON válido con las claves: "short_description", "long_description", "telegram_text".
"""
        messages = [
            {"role": "system", "content": "Eres un asistente experto en eCommerce y copywriting de chollos. Responde únicamente en formato JSON."},
            {"role": "user", "content": prompt},
        ]
        result = self.llm_client.generate_json(messages)

        # Normalizar claves si el modelo utilizó variantes
        if "telegram_description" in result and "telegram_text" not in result:
            result["telegram_text"] = result.pop("telegram_description")

        return result

    def _get_categorization(self, title: str, categories_prompt: str) -> dict[str, Any]:
        prompt = f"""
Analiza este producto y selecciona la CATEGORÍA y SUBCATEGORÍA más adecuadas de la lista disponible.

PRODUCTO: {title}

LISTA DISPONIBLE (ID | Nombre):
{categories_prompt}

Responde SOLO un objeto JSON con exactamente dos claves:
- "category_id": string o null (el ID exacto de la categoría principal)
- "subcategory_id": string o null (el ID exacto de la subcategoría si corresponde)
"""
        messages = [
            {"role": "system", "content": "Eres un clasificador taxonómico preciso de productos. Responde solo con JSON estructurado."},
            {"role": "user", "content": prompt},
        ]
        return self.llm_client.generate_json(messages)
