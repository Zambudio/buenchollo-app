from fastapi import APIRouter, Depends, Request

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.core.security import AuthenticatedUser
from app.modules.products.api.router import get_amazon_client
from app.modules.products.application.preview_product_from_url import ProductPreviewProvider
from app.modules.products.infrastructure.amazon_client import extract_asin_from_url
from app.modules.submissions.api.dependencies import (
    get_submission_repository,
    require_complete_profile,
)
from app.modules.submissions.api.schemas import CheckLinkRequest, LinkCheckResponse
from app.modules.submissions.application.check_link import CheckLinkUseCase
from app.modules.submissions.infrastructure.repository import SubmissionRepository

router = APIRouter(prefix="/submissions", tags=["submissions"])


def get_product_provider(provider=Depends(get_amazon_client)) -> ProductPreviewProvider:
    return provider


def get_check_link_use_case(
    repo: SubmissionRepository = Depends(get_submission_repository),
    provider: ProductPreviewProvider = Depends(get_product_provider),
    settings: Settings = Depends(get_settings),
) -> CheckLinkUseCase:
    return CheckLinkUseCase(
        repo,
        provider,
        amazon_tag=settings.amazon_affiliate_tag or "",
        asin_resolver=extract_asin_from_url,
    )


@router.post("/check-link", response_model=LinkCheckResponse)
@limiter.limit("20/minute")
async def check_link(
    request: Request,
    payload: CheckLinkRequest,
    _user: AuthenticatedUser = Depends(require_complete_profile),
    use_case: CheckLinkUseCase = Depends(get_check_link_use_case),
) -> LinkCheckResponse:
    result = await use_case.execute(payload.url)
    return LinkCheckResponse.model_validate(result, from_attributes=True)
