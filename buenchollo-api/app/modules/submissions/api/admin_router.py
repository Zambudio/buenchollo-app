import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.security import require_admin
from app.modules.deals.api.router import get_deal_service
from app.modules.deals.api.schemas import DealCreate, DealDetailResponse
from app.modules.deals.application.deal_service import DealService
from app.modules.submissions.api.dependencies import (
    get_submission_notifier,
    get_submission_repository,
)
from app.modules.submissions.api.schemas import (
    AdminSubmissionResponse,
    RejectRequest,
    to_admin_submission_response,
)
from app.modules.submissions.application.notifier import SubmissionNotifier
from app.modules.submissions.application.review_submission import ReviewSubmissionUseCase
from app.modules.submissions.domain.models import PENDING
from app.modules.submissions.infrastructure.repository import SubmissionRepository

router = APIRouter(prefix="/admin/submissions", tags=["admin-submissions"])

StatusFilter = Literal["pending", "approved", "rejected", "withdrawn"]


def get_review_use_case(
    repo: SubmissionRepository = Depends(get_submission_repository),
    service: DealService = Depends(get_deal_service),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
) -> ReviewSubmissionUseCase:
    async def audit(action: str, target_type: str, target_id: str, payload: dict) -> None:
        await audit_log(
            db,
            user_id=str(admin.id),
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
        )

    return ReviewSubmissionUseCase(repo, service, audit)


@router.get("", response_model=list[AdminSubmissionResponse])
async def list_submissions(
    status: StatusFilter = PENDING,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin=Depends(require_admin),
    repo: SubmissionRepository = Depends(get_submission_repository),
) -> list[AdminSubmissionResponse]:
    submissions = await repo.list_by_status(status, limit, offset)
    previously = await repo.expired_submission_ids(submissions)
    return [to_admin_submission_response(s, s.id in previously) for s in submissions]


@router.get("/count")
async def count_pending(
    _admin=Depends(require_admin),
    repo: SubmissionRepository = Depends(get_submission_repository),
) -> dict[str, int]:
    return {"pending": await repo.count_by_status(PENDING)}


@router.get("/{submission_id}", response_model=AdminSubmissionResponse)
async def get_submission(
    submission_id: str,
    _admin=Depends(require_admin),
    repo: SubmissionRepository = Depends(get_submission_repository),
) -> AdminSubmissionResponse:
    try:
        uuid.UUID(submission_id)
    except ValueError:
        raise NotFoundError("Propuesta no encontrada") from None
    submission = await repo.get(submission_id)
    if submission is None:
        raise NotFoundError("Propuesta no encontrada")
    previously = await repo.expired_submission_ids([submission])
    return to_admin_submission_response(submission, submission.id in previously)


@router.post("/{submission_id}/approve", response_model=DealDetailResponse)
async def approve_submission(
    submission_id: str,
    deal_in: DealCreate,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
    use_case: ReviewSubmissionUseCase = Depends(get_review_use_case),
    settings: Settings = Depends(get_settings),
    notifier: SubmissionNotifier = Depends(get_submission_notifier),
    db: AsyncSession = Depends(get_db),
):
    deal = await use_case.approve(
        submission_id, str(admin.id), deal_in, settings.amazon_affiliate_tag or ""
    )
    await audit_log(
        db,
        user_id=str(admin.id),
        action="submission.approve",
        target_type="submission",
        target_id=submission_id,
        payload={"deal_id": str(deal.id)},
    )
    # Las background tasks corren ANTES del commit de get_db: se confirma aquí
    # para que el notifier vea la decisión.
    await db.commit()
    background_tasks.add_task(notifier.notify_user_decision, submission_id)
    return deal


@router.post("/{submission_id}/reject", response_model=AdminSubmissionResponse)
async def reject_submission(
    submission_id: str,
    payload: RejectRequest,
    background_tasks: BackgroundTasks,
    admin=Depends(require_admin),
    use_case: ReviewSubmissionUseCase = Depends(get_review_use_case),
    notifier: SubmissionNotifier = Depends(get_submission_notifier),
    db: AsyncSession = Depends(get_db),
) -> AdminSubmissionResponse:
    submission = await use_case.reject(submission_id, str(admin.id), payload.reason)
    await audit_log(
        db,
        user_id=str(admin.id),
        action="submission.reject",
        target_type="submission",
        target_id=submission_id,
        payload={"reason": submission.rejection_reason},
    )
    await db.commit()
    background_tasks.add_task(notifier.notify_user_decision, submission_id)
    return to_admin_submission_response(submission)
