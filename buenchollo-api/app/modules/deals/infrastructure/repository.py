from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.modules.deals.domain.models import Deal, DealVote

class DealRepository:
    """Repository for managing deals in the database."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, deal_id: str) -> Deal | None:
        result = await self.session.execute(
            select(Deal)
            .options(selectinload(Deal.category), selectinload(Deal.subcategory), selectinload(Deal.store))
            .where(Deal.id == deal_id)
        )
        return result.scalars().first()

    async def get_by_slug(self, slug: str) -> Deal | None:
        result = await self.session.execute(
            select(Deal)
            .options(selectinload(Deal.category), selectinload(Deal.subcategory), selectinload(Deal.store))
            .where(Deal.slug == slug)
        )
        return result.scalars().first()
        
    async def get_latest_active(self, limit: int = 10) -> list[Deal]:
        result = await self.session.execute(
            select(Deal)
            .options(selectinload(Deal.category), selectinload(Deal.subcategory), selectinload(Deal.store))
            .where(Deal.status == "active")
            .order_by(Deal.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_popular_active(self, limit: int = 10) -> list[Deal]:
        result = await self.session.execute(
            select(Deal)
            .options(selectinload(Deal.category), selectinload(Deal.subcategory), selectinload(Deal.store))
            .where(Deal.status == "active")
            .order_by(Deal.temperature.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_active(self, category_id: str | None = None, store_id: str | None = None, search: str | None = None, limit: int = 20) -> list[Deal]:
        query = select(Deal).options(selectinload(Deal.category), selectinload(Deal.subcategory), selectinload(Deal.store)).where(Deal.status == "active")
        
        if category_id:
            query = query.where(Deal.category_id == category_id)
        if store_id:
            query = query.where(Deal.store_id == store_id)
        if search:
            query = query.where(Deal.title.ilike(f"%{search}%"))
            
        query = query.order_by(Deal.published_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
        
    async def get_all_admin(self, status: str | None = None, limit: int = 200) -> list[Deal]:
        query = select(Deal).options(selectinload(Deal.category), selectinload(Deal.subcategory), selectinload(Deal.store))
        if status and status != "all":
            query = query.where(Deal.status == status)
        query = query.order_by(Deal.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, deal: Deal) -> Deal:
        self.session.add(deal)
        await self.session.flush()
        return deal

    async def update(self, deal: Deal) -> Deal:
        # Ya que la sesión trackea el objeto, no hace falta hacer session.add o update explícito si fue modificado.
        # Pero flush() nos asegura los cambios.
        await self.session.flush()
        return deal

    async def delete(self, deal: Deal) -> None:
        await self.session.delete(deal)
        await self.session.flush()

    # --- Votos ---

    async def get_user_vote(self, deal_id: str, user_id: str) -> int | None:
        result = await self.session.execute(
            select(DealVote.vote).where(DealVote.deal_id == deal_id, DealVote.user_id == user_id)
        )
        return result.scalar()

    async def upsert_vote(self, deal_id: str, user_id: str, vote: int) -> None:
        stmt = pg_insert(DealVote).values(
            deal_id=deal_id, user_id=user_id, vote=vote
        ).on_conflict_do_update(
            index_elements=["deal_id", "user_id"],
            set_={"vote": vote}
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_vote(self, deal_id: str, user_id: str) -> None:
        result = await self.session.execute(
            select(DealVote).where(DealVote.deal_id == deal_id, DealVote.user_id == user_id)
        )
        vote_obj = result.scalars().first()
        if vote_obj:
            await self.session.delete(vote_obj)
            await self.session.flush()
