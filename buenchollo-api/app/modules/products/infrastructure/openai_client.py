"""OpenAI client for product categorization and text generation."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from openai import OpenAI
from app.core.config import Settings
from app.modules.products.domain.entities import ProductPreview

logger = logging.getLogger(__name__)

class OpenAIAssistant:
    """Uses GPT-4o to enrich product data and categorize it."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of the OpenAI client."""
        if self._client is None:
            if not self.settings.openai_api_key:
                raise ValueError("Falta OPENAI_API_KEY en la configuración.")
            self._client = OpenAI(api_key=self.settings.openai_api_key)
        return self._client

    def enrich_product(self, product: ProductPreview, categories_prompt: str) -> dict[str, Any]:
        """
        Specialized enrichment process.
        """
        try:
            # 1. Fase de Copywriting (Descripciones)
            copy_data = self._get_copywriting(product)
            
            # 2. Fase de Categorización
            cat_data = self._get_categorization(product.title, categories_prompt)
            
            # Combinar resultados
            return {**copy_data, **cat_data}
            
        except Exception as exc:
            logger.error("Error crítico en OpenAIAssistant: %s", exc)
            return {
                "short_description": f"⚠️ Error IA: {str(exc)[:50]}",
                "long_description": "Hubo un error al generar los textos. Revisa tu OPENAI_API_KEY."
            }

    def _get_copywriting(self, product: ProductPreview) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""
        Eres un copywriter de ventas para "BuenCholloTech". Hoy es {today}.
        Genera un JSON con:
        1. 'short_description': Un eslogan corto con un emoji (máx 10 palabras).
        2. 'long_description': Descripción en Markdown con negritas y puntos (•).
        3. 'telegram_text': Post para Telegram con emojis.
        
        PRODUCTO: {product.title}
        INFO: {product.description}
        """
        return self._ask_json(prompt)

    def _get_categorization(self, title: str, categories_prompt: str) -> dict:
        prompt = f"""
        Analiza este producto y elige la CATEGORÍA y SUBCATEGORÍA correctas de la lista.
        PRODUCTO: {title}
        
        LISTA DISPONIBLE (ID | Nombre):
        {categories_prompt}
        
        Responde SOLO un JSON con 'category_id' y 'subcategory_id'.
        """
        return self._ask_json(prompt)

    def _ask_json(self, prompt: str) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            return json.loads(response.choices[0].message.content or "{}")
        except Exception as e:
            logger.warning(f"Error en llamada parcial a OpenAI: {e}")
            return {}
