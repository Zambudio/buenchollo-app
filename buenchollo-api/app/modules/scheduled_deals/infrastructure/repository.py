from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.scheduled_deals.domain.models import ScheduledDeal, ScheduledDealStatus


class ScheduledDealRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _base_query():
        return select(ScheduledDeal).options(
            selectinload(ScheduledDeal.deal),
            selectinload(ScheduledDeal.category),
        )

    async def list_between(self, start: datetime, end: datetime) -> list[ScheduledDeal]:
        result = await self.session.execute(
            self._base_query()
            .where(ScheduledDeal.scheduled_at >= start, ScheduledDeal.scheduled_at < end)
            .order_by(ScheduledDeal.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, scheduled_id: str) -> ScheduledDeal | None:
        result = await self.session.execute(
            self._base_query().where(ScheduledDeal.id == scheduled_id)
        )
        return result.scalars().first()

    async def get_by_deal_id(self, deal_id: str) -> ScheduledDeal | None:
        result = await self.session.execute(
            self._base_query().where(ScheduledDeal.deal_id == deal_id)
        )
        return result.scalars().first()

    async def get_pending_until_for_update(self, horizon: datetime) -> list[ScheduledDeal]:
        result = await self.session.execute(
            self._base_query()
            .where(
                ScheduledDeal.status == ScheduledDealStatus.SCHEDULED,
                ScheduledDeal.scheduled_at <= horizon,
            )
            .order_by(ScheduledDeal.scheduled_at.asc())
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def create(self, scheduled: ScheduledDeal) -> ScheduledDeal:
        self.session.add(scheduled)
        await self.session.flush()
        return scheduled

    async def update(self, scheduled: ScheduledDeal) -> ScheduledDeal:
        await self.session.flush()
        return scheduled

    async def delete(self, scheduled: ScheduledDeal) -> None:
        await self.session.delete(scheduled)
        await self.session.flush()
