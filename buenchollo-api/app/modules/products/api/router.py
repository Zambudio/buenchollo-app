"""HTTP routes for product preview operations."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.modules.products.api.schemas import ProductPreviewFromUrlRequest, ProductPreviewResponse
from app.modules.products.application.preview_product_from_url import (
    PreviewProductFromUrlUseCase,
    ProductNotFoundError,
    ProductProviderUnavailableError,
)
from app.modules.products.infrastructure.amazon_client import AmazonProductClient
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
def preview_from_url(
    payload: ProductPreviewFromUrlRequest,
    use_case: PreviewProductFromUrlUseCase = Depends(get_preview_use_case),
) -> ProductPreviewResponse:
    """Generate a normalized product preview from an Amazon URL or ASIN."""
    try:
        product = use_case.execute(payload.url)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProductProviderUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return ProductPreviewResponse.model_validate(product)

