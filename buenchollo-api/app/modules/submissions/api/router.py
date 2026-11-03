from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.core.security import AuthenticatedUser, _clean_supabase_url, get_supabase_client
from app.modules.categories.infrastructure.repository import CategoryRepository
from app.modules.products.api.router import get_amazon_client
from app.modules.products.application.preview_product_from_url import ProductPreviewProvider
from app.modules.products.infrastructure.amazon_client import extract_asin_from_url
from app.modules.submissions.api.dependencies import (
    get_submission_notifier,
    get_submission_repository,
    require_complete_profile,
)
from app.modules.submissions.api.schemas import (
    CheckLinkRequest,
    ImageFromUrlRequest,
    ImageUploadResponse,
    LinkCheckResponse,
    SubmissionCreate,
    SubmissionResponse,
    is_allowed_image,
    to_submission_response,
)
from app.modules.submissions.application.check_link import CheckLinkUseCase
from app.modules.submissions.application.create_submission import CreateSubmissionUseCase
from app.modules.submissions.application.notifier import SubmissionNotifier
from app.modules.submissions.application.image_processing import MAX_IMAGE_BYTES
from app.modules.submissions.application.ingest_image import IngestImageUseCase
from app.modules.submissions.application.user_submissions import (
    ListMySubmissionsUseCase,
    WithdrawSubmissionUseCase,
)
from app.modules.submissions.domain.exceptions import InvalidImageError
from app.modules.submissions.infrastructure.image_fetcher import ImageFetcher
from app.modules.submissions.infrastructure.repository import SubmissionRepository
from app.modules.submissions.infrastructure.storage import SubmissionImageStorage

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


def get_category_repository(db: AsyncSession = Depends(get_db)) -> CategoryRepository:
    return CategoryRepository(db)


def get_create_submission_use_case(
    repo: SubmissionRepository = Depends(get_submission_repository),
    category_repo: CategoryRepository = Depends(get_category_repository),
) -> CreateSubmissionUseCase:
    return CreateSubmissionUseCase(repo, category_repo, asin_resolver=extract_asin_from_url)


def get_list_my_submissions_use_case(
    repo: SubmissionRepository = Depends(get_submission_repository),
) -> ListMySubmissionsUseCase:
    return ListMySubmissionsUseCase(repo)


def get_withdraw_submission_use_case(
    repo: SubmissionRepository = Depends(get_submission_repository),
) -> WithdrawSubmissionUseCase:
    return WithdrawSubmissionUseCase(repo)


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_submission(
    request: Request,
    payload: SubmissionCreate,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(require_complete_profile),
    use_case: CreateSubmissionUseCase = Depends(get_create_submission_use_case),
    settings: Settings = Depends(get_settings),
    notifier: SubmissionNotifier = Depends(get_submission_notifier),
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    submission = await use_case.execute(user.id, payload, settings.amazon_affiliate_tag or "")
    # Las background tasks se ejecutan ANTES del commit de get_db (teardown de la
    # dependencia): sin este commit el notifier no vería la propuesta.
    await db.commit()
    background_tasks.add_task(notifier.notify_admin_new, submission.id)
    return to_submission_response(submission)


@router.get("/mine", response_model=list[SubmissionResponse])
async def list_my_submissions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(require_complete_profile),
    use_case: ListMySubmissionsUseCase = Depends(get_list_my_submissions_use_case),
) -> list[SubmissionResponse]:
    return [to_submission_response(s) for s in await use_case.execute(user.id, limit, offset)]


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_submission(
    submission_id: str,
    user: AuthenticatedUser = Depends(require_complete_profile),
    use_case: WithdrawSubmissionUseCase = Depends(get_withdraw_submission_use_case),
) -> Response:
    await use_case.execute(user.id, submission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def get_image_fetcher() -> ImageFetcher:
    return ImageFetcher()


def get_image_storage(settings: Settings = Depends(get_settings)) -> SubmissionImageStorage:
    return SubmissionImageStorage(
        lambda: get_supabase_client(settings), _clean_supabase_url(settings)
    )


def get_ingest_image_use_case(
    fetcher: ImageFetcher = Depends(get_image_fetcher),
    storage: SubmissionImageStorage = Depends(get_image_storage),
) -> IngestImageUseCase:
    return IngestImageUseCase(fetcher, storage, is_trusted_url=is_allowed_image)


async def _read_limited(file: UploadFile) -> bytes:
    buffer = bytearray()
    while len(buffer) <= MAX_IMAGE_BYTES:
        chunk = await file.read(min(64 * 1024, MAX_IMAGE_BYTES + 1 - len(buffer)))
        if not chunk:
            return bytes(buffer)
        buffer.extend(chunk)
    raise InvalidImageError("La imagen supera el máximo de 5 MB")


@router.post("/images", response_model=ImageUploadResponse)
@limiter.limit("30/minute")
async def upload_image(
    request: Request,
    file: UploadFile,
    user: AuthenticatedUser = Depends(require_complete_profile),
    use_case: IngestImageUseCase = Depends(get_ingest_image_use_case),
) -> ImageUploadResponse:
    url, width, height = await use_case.from_bytes(user.id, await _read_limited(file))
    return ImageUploadResponse(url=url, width=width, height=height)


@router.post("/images/from-url", response_model=ImageUploadResponse)
@limiter.limit("30/minute")
async def upload_image_from_url(
    request: Request,
    payload: ImageFromUrlRequest,
    user: AuthenticatedUser = Depends(require_complete_profile),
    use_case: IngestImageUseCase = Depends(get_ingest_image_use_case),
) -> ImageUploadResponse:
    url, width, height = await use_case.from_url(user.id, payload.url)
    return ImageUploadResponse(url=url, width=width, height=height)
