from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.notifications.api.schemas import NotificationOut
from app.modules.notifications.infrastructure.repository import NotificationRepository

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _repo(db: AsyncSession = Depends(get_db)) -> NotificationRepository:
    return NotificationRepository(db)


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(get_current_user),
    repo: NotificationRepository = Depends(_repo),
):
    return await repo.get_by_user(str(current_user.id), limit=limit)


@router.get("/unread-count")
async def get_unread_count(
    current_user=Depends(get_current_user),
    repo: NotificationRepository = Depends(_repo),
) -> dict[str, int]:
    return {"count": await repo.count_unread(str(current_user.id))}


@router.post("/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(
    current_user=Depends(get_current_user),
    repo: NotificationRepository = Depends(_repo),
):
    await repo.mark_unread_as_read(str(current_user.id))
