from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.stores.domain.models import Store

class StoreRepository:
    """Repository for managing stores in the database."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_active(self) -> list[Store]:
        result = await self.session.execute(
            select(Store).where(Store.is_active == True)
        )
        return list(result.scalars().all())

    async def get_by_id(self, store_id: str) -> Store | None:
        result = await self.session.execute(select(Store).where(Store.id == store_id))
        return result.scalars().first()
