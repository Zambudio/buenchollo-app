from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import require_admin
from app.modules.deals.api.schemas import DealDetailResponse
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.products.infrastructure.amazon_client import AmazonProductClient
from app.modules.scheduled_tasks.api.schemas import (
    BulkDeleteRunsRequest,
    BulkDeleteRunsResponse,
    CandidateSchema,
    ConfirmRequest,
    PreviewResponse,
    RunDetailResponse,
    RunResponse,
    ScheduledTaskResponse,
    ScheduledTaskUpdate,
)
from app.modules.scheduled_tasks.application.price_check_handler import PriceCheckHandler
from app.modules.scheduled_tasks.application.scheduled_task_service import ScheduledTaskService
from app.modules.scheduled_tasks.application.task_handler import Candidate
from app.modules.scheduled_tasks.domain.exceptions import ScheduledTaskRunNotFound
from app.modules.scheduled_tasks.infrastructure.repository import ScheduledTaskRepository

router = APIRouter(prefix="/admin/scheduled-tasks", tags=["scheduled-tasks"])


def get_scheduled_task_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ScheduledTaskService:
    repo = ScheduledTaskRepository(db)
    deal_repo = DealRepository(db)
    handler = PriceCheckHandler(AmazonProductClient(settings), deal_repo)
    return ScheduledTaskService(repo, deal_repo, {"price_check": handler}, db)


@router.get("", response_model=list[ScheduledTaskResponse])
async def list_scheduled_tasks(
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    return await service.list_tasks()


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: str,
    payload: ScheduledTaskUpdate,
    db: AsyncSession = Depends(get_db),
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    current_user=Depends(require_admin),
):
    changes = payload.model_dump(exclude_none=True)
    updated = await service.update_config(task_id, **changes)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="scheduled_task.update",
        target_type="scheduled_task",
        target_id=task_id,
        payload={"changed_fields": list(changes)},
    )
    return updated


@router.post("/{task_id}/preview", response_model=PreviewResponse)
async def preview_scheduled_task(
    task_id: str,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    result = await service.preview(task_id)
    return PreviewResponse(
        total_checked=result.total_checked,
        candidates=[CandidateSchema.model_validate(c.__dict__) for c in result.candidates],
    )


@router.post("/{task_id}/confirm", response_model=RunResponse)
async def confirm_scheduled_task(
    task_id: str,
    payload: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    current_user=Depends(require_admin),
):
    candidates = [Candidate(**c.model_dump()) for c in payload.candidates]
    return await service.confirm(task_id, payload.total_checked, candidates, str(current_user.id))


@router.get("/{task_id}/runs", response_model=list[RunResponse])
async def list_scheduled_task_runs(
    task_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    return await service.list_runs(task_id, limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_scheduled_task_run_detail(
    run_id: str,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    run = await service.get_run_detail(run_id)
    if run is None:
        raise ScheduledTaskRunNotFound(run_id)
    return run


@router.delete("/runs/{run_id}", status_code=204)
async def delete_scheduled_task_run(
    run_id: str,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    deleted = await service.delete_run(run_id)
    if not deleted:
        raise ScheduledTaskRunNotFound(run_id)


@router.post("/runs/bulk-delete", response_model=BulkDeleteRunsResponse)
async def bulk_delete_scheduled_task_runs(
    payload: BulkDeleteRunsRequest,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    _auth=Depends(require_admin),
):
    count = await service.bulk_delete_runs(payload.run_ids)
    return BulkDeleteRunsResponse(deleted=count)


@router.post("/runs/items/{item_id}/restore", response_model=DealDetailResponse)
async def restore_scheduled_task_run_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
    current_user=Depends(require_admin),
):
    deal = await service.restore_item(item_id)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="deal.restore_from_price_check",
        target_type="deal",
        target_id=deal.id,
    )
    return deal
