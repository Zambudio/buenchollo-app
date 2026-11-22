"""Use case that builds a product preview from an Amazon URL or ASIN."""

import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.modules.ai.domain.entities import COPY_FALLBACK_KEY
from app.modules.products.domain.entities import ProductPreview


class ProductNotFoundError(NotFoundError):
    """Raised when the product cannot be resolved from the provided URL."""


class ProductProviderUnavailableError(ServiceUnavailableError):
    """Raised when the external product provider is not configured or unavailable."""


# ── Puertos (abstracciones del dominio/aplicación) ───────────────────────────

class ProductPreviewProvider(Protocol):
    """Port implemented by infrastructure adapters that fetch product previews."""

    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None:
        """Fetch and normalize product information."""


class CategoryClient(Protocol):
    """Port for fetching and formatting the category hierarchy."""

    def get_categories_hierarchy(self) -> list[dict[str, Any]]:
        """Return flat list of category dicts with id, name, parent_id."""

    def format_categories_for_prompt(self, categories: list[dict[str, Any]]) -> str:
        """Render the hierarchy as a human-readable string for an LLM prompt."""


class AIEnricher(Protocol):
    """Port for enriching product data with AI-generated text and categorization."""

    def enrich_product(
        self,
        product: ProductPreview,
        categories_prompt: str,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Return a dict with AI-generated fields (short_description, category_id, …)."""


# ── Casos de uso ──────────────────────────────────────────────────────────────

class EnrichProductUseCase:
    """Copywriting y categorización con IA de un producto ya conocido.

    Lo usa el autocompletado de Amazon y también el de las redes de afiliación
    (Awin / Tradedoubler), que traen los datos del catálogo pero no los textos
    de venta ni la categoría de la web.
    """

    def __init__(self, category_client: CategoryClient, ai_assistant: AIEnricher) -> None:
        self.category_client = category_client
        self.ai_assistant = ai_assistant

    def execute(
        self,
        *,
        title: str,
        description: str = "",
        brand: str = "",
        category_hint: str = "",
        provider: str | None = None,
    ) -> "EnrichedProduct":
        """Enriquece un producto importado a partir de sus datos.

        A diferencia de Amazon, aquí no se inventa nada si la IA cae: sin copy
        real (`copy_ok=False`) los textos van vacíos y la descripción larga es un
        resumen del catálogo; sin clasificación de la IA no hay categoría (nada
        de «Varios» por defecto). El editor decide.
        """
        context = description.strip()
        if category_hint.strip():
            context = f"Categoría en la tienda: {category_hint.strip()}\n{context}".strip()
        product = ProductPreview(title=title.strip(), brand=brand.strip(), description=context)
        categories = self.category_client.get_categories_hierarchy()
        categories_prompt = self.category_client.format_categories_for_prompt(categories)
        ai_data = self.ai_assistant.enrich_product(product, categories_prompt, provider=provider) or {}

        copy_ok = not ai_data.get(COPY_FALLBACK_KEY) and bool(
            ai_data.get("short_description") or ai_data.get("telegram_text")
        )
        long_text = (ai_data.get("long_description") or ai_data.get("description") or "") if copy_ok else ""
        result = EnrichedProduct(
            short_description=(ai_data.get("short_description") or "") if copy_ok else "",
            long_description=long_text or summarize_text(description),
            telegram_text=(ai_data.get("telegram_text") or "") if copy_ok else "",
            copy_ok=copy_ok,
        )
        category_id = ai_data.get("category_id")
        if category_id and any(c.get("id") == category_id and not c.get("parent_id") for c in categories):
            subcategory_id = ai_data.get("subcategory_id")
            valid_sub = any(
                c.get("id") == subcategory_id and c.get("parent_id") == category_id for c in categories
            )
            if not valid_sub:
                first = next((c for c in categories if c.get("parent_id") == category_id), None)
                subcategory_id = first["id"] if first else None
            result.category_id, result.subcategory_id = category_id, subcategory_id
        return result

    def enrich(self, product: ProductPreview, provider: str | None = None) -> ProductPreview:
        """Aplica la IA sobre `product` y garantiza una categoría (Varios si no)."""
        # Sync categories from Supabase for the AI context
        categories = self.category_client.get_categories_hierarchy()
        categories_prompt = self.category_client.format_categories_for_prompt(categories)

        # Categorize and enrich with AI
        ai_data = self.ai_assistant.enrich_product(product, categories_prompt, provider=provider)

        # Merge AI data into the product entity
        if ai_data:
            # Categorización
            product.category_id = ai_data.get("category_id") or product.category_id
            product.subcategory_id = ai_data.get("subcategory_id") or product.subcategory_id

            # Textos persuasivos
            product.short_description = ai_data.get("short_description") or product.short_description
            product.long_description = (
                ai_data.get("long_description") or ai_data.get("description") or product.long_description
            )
            product.telegram_text = ai_data.get("telegram_text") or product.telegram_text

            # Metadatos
            if ai_data.get("expires_at"):
                product.expires_at = ai_data.get("expires_at")

        _ensure_category(product, categories)
        return product


@dataclass(slots=True)
class EnrichedProduct:
    """Propuesta de la IA para un producto importado (Awin / Tradedoubler)."""

    short_description: str = ""
    long_description: str = ""
    telegram_text: str = ""
    category_id: str | None = None
    subcategory_id: str | None = None
    # False: la IA no escribió los textos (caída o vacía); van vacíos salvo el
    # resumen de la descripción, y el editor no debe tratarlos como propuesta.
    copy_ok: bool = False


SUMMARY_MAX_CHARS = 500


def summarize_text(text: str, max_len: int = SUMMARY_MAX_CHARS) -> str:
    """Resumen con frases completas del propio texto (sin inventar nada).

    Se usa cuando la IA no responde: mejor dos o tres frases de la tienda que la
    ficha entera. Si la primera frase ya no cabe, se corta por palabra.
    """
    flat = re.sub(r"\s+", " ", text or "").strip()
    if len(flat) <= max_len:
        return flat
    out = ""
    for sentence in re.split(r"(?<=[.!?])\s+", flat):
        candidate = f"{out} {sentence}".strip()
        if len(candidate) > max_len:
            break
        out = candidate
    if out:
        return out
    # Reserva un carácter para «…»: el resultado nunca pasa de `max_len`.
    return flat[: max_len - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _ensure_category(product: ProductPreview, categories: list[dict[str, Any]]) -> None:
    """Fallback de categorización garantizado si la IA no clasificó o dejó incompleta la taxonomía."""
    if product.category_id and product.subcategory_id:
        return
    varios_cat = next(
        (
            c for c in categories
            if not c.get("parent_id") and (
                c.get("name", "").strip().lower() == "varios" or c.get("slug") == "varios-xly2"
            )
        ),
        None,
    )
    varios_cat_id = varios_cat["id"] if varios_cat else "99b72435-42f6-4628-a1af-3f66af5e4a88"
    varios_sub = next(
        (
            c for c in categories
            if c.get("parent_id") == varios_cat_id and (
                c.get("name", "").strip().lower() == "varios" or c.get("slug") == "varios-y175"
            )
        ),
        None,
    )
    varios_sub_id = varios_sub["id"] if varios_sub else "970d38ab-20e8-43e8-97a1-5c84dfd391c5"

    if not product.category_id:
        product.category_id = varios_cat_id
        product.subcategory_id = varios_sub_id
    elif not product.subcategory_id:
        first_sub = next((c for c in categories if c.get("parent_id") == product.category_id), None)
        product.subcategory_id = first_sub["id"] if first_sub else varios_sub_id


class PreviewProductFromUrlUseCase:
    """Coordinate fetching product data, categorizing with AI and preparing response."""

    def __init__(
        self,
        product_provider: ProductPreviewProvider,
        category_client: CategoryClient,
        ai_assistant: AIEnricher,
    ) -> None:
        self.product_provider = product_provider
        self.category_client = category_client
        self.ai_assistant = ai_assistant

    def execute(self, url: str, provider: str | None = None) -> ProductPreview:
        """Fetch from provider, then enrich with AI categorization."""
        product = self.product_provider.get_product_preview(url)
        if product is None:
            raise ProductNotFoundError("No se ha encontrado el producto de Amazon.")

        # Asegurarnos de que tenemos texto para que la IA trabaje
        if not product.description and product.features:
            product.description = " - ".join(product.features)

        return EnrichProductUseCase(self.category_client, self.ai_assistant).enrich(product, provider)
