from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.alerts.api.schemas import AlertCreate, AlertUpdate, AlertOut
from app.modules.alerts.domain.exceptions import AlertNotFound
from app.modules.alerts.infrastructure.repository import AlertRepository

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _repo(db: AsyncSession = Depends(get_db)) -> AlertRepository:
    return AlertRepository(db)


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    current_user=Depends(get_current_user),
    repo: AlertRepository = Depends(_repo),
):
    return await repo.get_by_user(str(current_user.id))


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreate,
    current_user=Depends(get_current_user),
    repo: AlertRepository = Depends(_repo),
):
    return await repo.create(str(current_user.id), body.model_dump())


@router.put("/{alert_id}", response_model=AlertOut)
async def update_alert(
    alert_id: str,
    body: AlertUpdate,
    current_user=Depends(get_current_user),
    repo: AlertRepository = Depends(_repo),
):
    alert = await repo.get_by_id(alert_id, str(current_user.id))
    if not alert:
        raise AlertNotFound()
    return await repo.update(alert, body.model_dump(exclude_unset=True))


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: str,
    current_user=Depends(get_current_user),
    repo: AlertRepository = Depends(_repo),
):
    alert = await repo.get_by_id(alert_id, str(current_user.id))
    if not alert:
        raise AlertNotFound()
    await repo.delete(alert)
