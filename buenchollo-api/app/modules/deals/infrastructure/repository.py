from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.modules.deals.domain.models import Deal, DealVote, Favorite

class DealRepository:
    """Repository for managing deals in the database."""
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _base_deal_query():
        """Select(Deal) con las relaciones que casi todo endpoint necesita precargadas
        (category, subcategory, store). Centraliza el selectinload para evitar
        repetirlo en cada query."""
        return select(Deal).options(
            selectinload(Deal.category),
            selectinload(Deal.subcategory),
            selectinload(Deal.store),
        )

    async def get_by_id(self, deal_id: str) -> Deal | None:
        result = await self.session.execute(
            self._base_deal_query().where(Deal.id == deal_id)
        )
        return result.scalars().first()

    async def get_by_slug(self, slug: str) -> Deal | None:
        result = await self.session.execute(
            self._base_deal_query().where(Deal.slug == slug)
        )
        return result.scalars().first()

    async def find_by_external_id(
        self, external_id: str, *, exclude_id: str | None = None
    ) -> Deal | None:
        """Busca un deal por su `external_id` (ASIN en el caso de Amazon).

        `exclude_id` permite ignorar el propio deal al validar duplicados
        en un UPDATE (no auto-colisión).
        """
        stmt = select(Deal).where(Deal.external_id == external_id)
        if exclude_id:
            stmt = stmt.where(Deal.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_latest_active(self, limit: int = 10) -> list[Deal]:
        result = await self.session.execute(
            self._base_deal_query()
            .where(Deal.status == "active")
            .order_by(Deal.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_popular_active(self, limit: int = 10) -> list[Deal]:
        result = await self.session.execute(
            self._base_deal_query()
            .where(Deal.status == "active")
            .order_by(Deal.temperature.desc(), Deal.published_at.desc(), Deal.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def _apply_active_filters(
        query,
        category_id: str | None = None,
        subcategory_id: str | None = None,
        store_id: str | None = None,
        search: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_discount: int | None = None,
    ):
        query = query.where(Deal.status == "active")
        if category_id:
            query = query.where(Deal.category_id == category_id)
        if subcategory_id:
            query = query.where(Deal.subcategory_id == subcategory_id)
        if store_id:
            query = query.where(Deal.store_id == store_id)
        if search:
            query = query.where(Deal.title.ilike(f"%{search}%"))
        if min_price is not None:
            query = query.where(Deal.current_price >= min_price)
        if max_price is not None:
            query = query.where(Deal.current_price <= max_price)
        if min_discount is not None:
            query = query.where(Deal.discount_percentage >= min_discount)
        return query

    async def count_active(
        self,
        category_id: str | None = None,
        subcategory_id: str | None = None,
        store_id: str | None = None,
        search: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_discount: int | None = None,
    ) -> int:
        query = self._apply_active_filters(
            select(func.count(Deal.id)),
            category_id=category_id,
            subcategory_id=subcategory_id,
            store_id=store_id,
            search=search,
            min_price=min_price,
            max_price=max_price,
            min_discount=min_discount,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def search_active(
        self,
        category_id: str | None = None,
        subcategory_id: str | None = None,
        store_id: str | None = None,
        search: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_discount: int | None = None,
        sort: str = "recent",
        limit: int = 20,
        offset: int = 0,
    ) -> list[Deal]:
        query = self._apply_active_filters(
            self._base_deal_query(),
            category_id=category_id,
            subcategory_id=subcategory_id,
            store_id=store_id,
            search=search,
            min_price=min_price,
            max_price=max_price,
            min_discount=min_discount,
        )

        # Cada orden incluye desempates estables. Sin ellos, PostgreSQL puede
        # devolver en distinto orden dos filas con la misma temperatura (muy
        # habitual con 0 votos), haciendo que se repitan o salten entre paginas.
        order_by = {
            "recent": (Deal.published_at.desc(), Deal.id.desc()),
            "popular": (Deal.temperature.desc(), Deal.published_at.desc(), Deal.id.desc()),
            "discount": (
                Deal.discount_percentage.desc().nullslast(),
                Deal.published_at.desc(),
                Deal.id.desc(),
            ),
            "price_asc": (Deal.current_price.asc(), Deal.published_at.desc(), Deal.id.desc()),
        }[sort]
        query = query.order_by(*order_by).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_admin(self, status: str | None = None, limit: int = 200) -> list[Deal]:
        query = self._base_deal_query()
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

    async def get_user_votes_bulk(self, deal_ids: list[str], user_id: str) -> dict[str, int]:
        """Votos del usuario para un lote de chollos (p.ej. los de una grid),
        en una sola query en vez de una petición por tarjeta."""
        if not deal_ids:
            return {}
        result = await self.session.execute(
            select(DealVote.deal_id, DealVote.vote).where(
                DealVote.deal_id.in_(deal_ids), DealVote.user_id == user_id
            )
        )
        return {str(deal_id): vote for deal_id, vote in result.all()}

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

    async def recalculate_votes(self, deal_id: str) -> dict:
        """Recalcula votes_up, votes_down y temperature desde deal_votes y actualiza el deal."""
        row = (await self.session.execute(
            text("""
                UPDATE deals SET
                    votes_up    = (SELECT COUNT(*) FROM deal_votes WHERE deal_id = CAST(:id AS uuid) AND vote = 1),
                    votes_down  = (SELECT COUNT(*) FROM deal_votes WHERE deal_id = CAST(:id AS uuid) AND vote = -1),
                    temperature = (SELECT COALESCE(SUM(vote), 0) FROM deal_votes WHERE deal_id = CAST(:id AS uuid))
                WHERE id = CAST(:id AS uuid)
                RETURNING temperature, votes_up, votes_down
            """),
            {"id": deal_id},
        )).mappings().first()
        return dict(row) if row else {"temperature": 0, "votes_up": 0, "votes_down": 0}

    async def get_many_by_ids(self, deal_ids: list[str]) -> list[Deal]:
        """Resuelve varios deals por id en una sola query (p.ej. bloques de
        producto recomendado del blog referenciando chollos existentes)."""
        if not deal_ids:
            return []
        result = await self.session.execute(
            self._base_deal_query().where(Deal.id.in_(deal_ids))
        )
        return list(result.scalars().all())

    async def get_due_scheduled(self) -> list[Deal]:
        """Devuelve los chollos con status='scheduled' cuyo scheduled_for ya ha llegado."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Deal)
            .where(Deal.status == "scheduled")
            .where(Deal.scheduled_for <= now)
        )
        return list(result.scalars().all())

    async def user_has_profile(self, user_id: str) -> bool:
        """Comprueba si existe un perfil en la tabla profiles para el user_id dado."""
        result = await self.session.execute(
            text("SELECT 1 FROM profiles WHERE user_id::text = :uid LIMIT 1"),
            {"uid": user_id},
        )
        return result.scalar() is not None

    async def increment_click_count(self, deal_id: str) -> int | None:
        """Incrementa atómicamente click_count y devuelve el nuevo valor.
        Devuelve None si el deal no existe."""
        row = (
            await self.session.execute(
                text(
                    "UPDATE deals SET click_count = COALESCE(click_count, 0) + 1 "
                    "WHERE id = CAST(:id AS uuid) RETURNING click_count"
                ),
                {"id": deal_id},
            )
        ).first()
        await self.session.flush()
        return row[0] if row else None

    # --- Favoritos ---

    async def get_favorites(self, user_id: str) -> list[Deal]:
        result = await self.session.execute(
            self._base_deal_query()
            .join(Favorite, Favorite.deal_id == Deal.id)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
        )
        return list(result.scalars().all())

    async def is_favorite(self, deal_id: str, user_id: str) -> bool:
        result = await self.session.execute(
            select(Favorite.id).where(Favorite.deal_id == deal_id, Favorite.user_id == user_id)
        )
        return result.scalar() is not None

    async def add_favorite(self, deal_id: str, user_id: str) -> None:
        fav = Favorite(deal_id=deal_id, user_id=user_id)
        self.session.add(fav)
        await self.session.flush()

    async def remove_favorite(self, deal_id: str, user_id: str) -> None:
        result = await self.session.execute(
            select(Favorite).where(Favorite.deal_id == deal_id, Favorite.user_id == user_id)
        )
        fav = result.scalars().first()
        if fav:
            await self.session.delete(fav)
            await self.session.flush()
