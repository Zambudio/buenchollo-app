from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.categories.domain.models import Category

class CategoryRepository:
    """Repository for managing categories in the database."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_active(self) -> list[Category]:
        result = await self.session.execute(
            select(Category).where(Category.is_active == True).order_by(Category.display_order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, category_id: str) -> Category | None:
        result = await self.session.execute(select(Category).where(Category.id == category_id))
        return result.scalars().first()

    async def get_by_slug(self, slug: str) -> Category | None:
        result = await self.session.execute(select(Category).where(Category.slug == slug))
        return result.scalars().first()

    async def get_all_admin(self) -> list[Category]:
        result = await self.session.execute(select(Category).order_by(Category.display_order))
        return list(result.scalars().all())

    async def create(self, category: Category) -> Category:
        self.session.add(category)
        await self.session.flush()
        return category

    async def delete(self, category: Category) -> None:
        await self.session.delete(category)
        await self.session.flush()
