from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.stores.domain.models import Store


class StoreRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_active(self) -> list[Store]:
        result = await self.session.execute(
            select(Store).where(Store.is_active == True).order_by(Store.name)
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[Store]:
        result = await self.session.execute(select(Store).order_by(Store.name))
        return list(result.scalars().all())

    async def get_by_id(self, store_id: str) -> Store | None:
        result = await self.session.execute(select(Store).where(Store.id == store_id))
        return result.scalars().first()

    async def create(self, store: Store) -> Store:
        self.session.add(store)
        await self.session.flush()
        return store

    async def update(self, store: Store) -> Store:
        await self.session.flush()
        return store

    async def delete(self, store: Store) -> None:
        await self.session.delete(store)
        await self.session.flush()
