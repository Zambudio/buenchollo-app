"""HTTP routes for product preview operations."""

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.modules.deals.api.router import get_deal_repository
from app.modules.deals.domain.exceptions import DuplicateDealError
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.products.api.schemas import ProductPreviewFromUrlRequest, ProductPreviewResponse
from app.modules.products.application.preview_product_from_url import (
    PreviewProductFromUrlUseCase,
)
from app.modules.products.infrastructure.amazon_client import (
    AmazonProductClient,
    extract_asin_from_url,
)
from app.modules.products.infrastructure.openai_client import OpenAIAssistant
from app.modules.products.infrastructure.supabase_client import SupabaseCategoryClient

router = APIRouter(prefix="/products", tags=["products"])


def get_amazon_client(settings: Settings = Depends(get_settings)) -> AmazonProductClient:
    """Build the Amazon adapter dependency."""
    return AmazonProductClient(settings)


def get_category_client(settings: Settings = Depends(get_settings)) -> SupabaseCategoryClient:
    """Build the Supabase category client dependency."""
    return SupabaseCategoryClient(settings)


def get_ai_assistant(settings: Settings = Depends(get_settings)) -> OpenAIAssistant:
    """Build the OpenAI assistant dependency."""
    return OpenAIAssistant(settings)


def get_preview_use_case(
    amazon_client: AmazonProductClient = Depends(get_amazon_client),
    category_client: SupabaseCategoryClient = Depends(get_category_client),
    ai_assistant: OpenAIAssistant = Depends(get_ai_assistant),
) -> PreviewProductFromUrlUseCase:
    """Build the use case dependency with all sub-services."""
    return PreviewProductFromUrlUseCase(amazon_client, category_client, ai_assistant)


@router.post("/preview-from-url", response_model=ProductPreviewResponse)
@limiter.limit("10/minute")  # caro: hace HTTP a Amazon Creators + OpenAI
async def preview_from_url(
    request: Request,
    payload: ProductPreviewFromUrlRequest,
    use_case: PreviewProductFromUrlUseCase = Depends(get_preview_use_case),
    deal_repo: DealRepository = Depends(get_deal_repository),
) -> ProductPreviewResponse:
    """Generate a normalized product preview from an Amazon URL or ASIN.

    Antes de invocar el caso de uso (que hace fetch a Amazon y llama a
    OpenAI) comprobamos si el ASIN ya tiene un chollo asociado, para no
    gastar en IA generando una preview que el admin no podrá guardar.

    Excepciones del caso de uso (`ProductNotFoundError`,
    `ProductProviderUnavailableError`) heredan de `DomainError` y son
    traducidas a HTTP por el handler global en `main.py`.
    """
    asin = await run_in_threadpool(extract_asin_from_url, payload.url)
    if asin:
        existing = await deal_repo.find_by_external_id(asin)
        if existing is not None:
            raise DuplicateDealError(existing.id, existing.slug, existing.title)

    product = await run_in_threadpool(use_case.execute, payload.url, payload.provider)
    return ProductPreviewResponse.model_validate(product)

