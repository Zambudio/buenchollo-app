from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.database import get_db
from app.core.security import require_admin
from app.modules.deals.application.deal_service import DealService
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.scheduled_deals.api.schemas import (
    NextScheduleResponse,
    ScheduledDateUpdate,
    ScheduledDealCreate,
    ScheduledDealResponse,
    ScheduledDealUpdate,
)
from app.modules.scheduled_deals.application.schedule_service import ScheduleService
from app.modules.scheduled_deals.infrastructure.repository import ScheduledDealRepository

router = APIRouter(prefix="/scheduled-deals", tags=["scheduled-deals"])


def get_schedule_service(db: AsyncSession = Depends(get_db)) -> ScheduleService:
    return ScheduleService(
        ScheduledDealRepository(db),
        DealService(DealRepository(db)),
    )


@router.get("/admin", response_model=list[ScheduledDealResponse])
async def list_scheduled_deals(
    start: datetime = Query(...),
    end: datetime = Query(...),
    service: ScheduleService = Depends(get_schedule_service),
    _auth=Depends(require_admin),
):
    return await service.repo.list_between(start, end)


@router.get("/admin/next-slot", response_model=NextScheduleResponse)
async def get_next_schedule_slot(
    service: ScheduleService = Depends(get_schedule_service),
    _auth=Depends(require_admin),
):
    return {"scheduled_at": await service.get_next_slot()}


@router.get("/admin/by-deal/{deal_id}", response_model=ScheduledDealResponse)
async def get_scheduled_deal_by_deal_id(
    deal_id: str,
    service: ScheduleService = Depends(get_schedule_service),
    _auth=Depends(require_admin),
):
    return await service.get_by_deal_id(deal_id)


@router.post("/admin", response_model=ScheduledDealResponse, status_code=201)
async def create_scheduled_deal(
    payload: ScheduledDealCreate,
    db: AsyncSession = Depends(get_db),
    service: ScheduleService = Depends(get_schedule_service),
    current_user=Depends(require_admin),
):
    scheduled = await service.create(payload.model_dump(), str(current_user.id))
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="scheduled_deal.create",
        target_type="scheduled_deal",
        target_id=scheduled.id,
        payload={"asin": scheduled.asin, "scheduled_at": scheduled.scheduled_at.isoformat()},
    )
    return scheduled


@router.put("/admin/{scheduled_id}", response_model=ScheduledDealResponse)
async def update_scheduled_deal(
    scheduled_id: str,
    payload: ScheduledDealUpdate,
    db: AsyncSession = Depends(get_db),
    service: ScheduleService = Depends(get_schedule_service),
    current_user=Depends(require_admin),
):
    changes = payload.model_dump(exclude_unset=True)
    scheduled = await service.update(scheduled_id, changes)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="scheduled_deal.update",
        target_type="scheduled_deal",
        target_id=scheduled_id,
        payload={"changed_fields": list(changes)},
    )
    return scheduled


@router.patch("/admin/{scheduled_id}/schedule", response_model=ScheduledDealResponse)
async def reschedule_deal(
    scheduled_id: str,
    payload: ScheduledDateUpdate,
    db: AsyncSession = Depends(get_db),
    service: ScheduleService = Depends(get_schedule_service),
    current_user=Depends(require_admin),
):
    scheduled = await service.reschedule(scheduled_id, payload.scheduled_at)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="scheduled_deal.reschedule",
        target_type="scheduled_deal",
        target_id=scheduled_id,
        payload={"scheduled_at": scheduled.scheduled_at.isoformat()},
    )
    return scheduled


@router.delete("/admin/{scheduled_id}", status_code=204)
async def delete_scheduled_deal(
    scheduled_id: str,
    db: AsyncSession = Depends(get_db),
    service: ScheduleService = Depends(get_schedule_service),
    current_user=Depends(require_admin),
):
    await service.delete(scheduled_id)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="scheduled_deal.delete",
        target_type="scheduled_deal",
        target_id=scheduled_id,
    )
