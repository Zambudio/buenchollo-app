from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.notifications.domain.models import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_unread(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Notification.id))
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return result.scalar_one()

    async def exists_for_alert_deal(self, alert_id: str, deal_id: str) -> bool:
        result = await self.db.execute(
            select(Notification.id)
            .where(
                Notification.type == "alert_match",
                Notification.alert_id == alert_id,
                Notification.deal_id == deal_id,
            )
            .limit(1)
        )
        return result.scalar() is not None

    async def create(self, data: dict) -> Notification:
        notification = Notification(**data)
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def mark_unread_as_read(self, user_id: str) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        await self.db.flush()
        return result.rowcount or 0
