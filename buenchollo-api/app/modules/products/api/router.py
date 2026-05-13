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

router = APIRouter(prefix="/products", tags=["products"])


def get_amazon_client(settings: Settings = Depends(get_settings)) -> AmazonProductClient:
    """Build the Amazon adapter dependency."""
    return AmazonProductClient(settings)


def get_preview_use_case(
    amazon_client: AmazonProductClient = Depends(get_amazon_client),
) -> PreviewProductFromUrlUseCase:
    """Build the use case dependency."""
    return PreviewProductFromUrlUseCase(amazon_client)


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

