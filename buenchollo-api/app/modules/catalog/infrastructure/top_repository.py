from sqlalchemy import case, delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.models import Product, ProductTopVote
from app.modules.categories.domain.models import Category
from app.modules.deals.domain.models import Deal

# Un producto es público mientras tenga alguna oferta visible en la web.
PUBLIC_DEAL_STATUSES = ("active", "expired")
TOP_SIZE = 10


def _has_public_deal():
    return exists().where(Deal.product_id == Product.id, Deal.status.in_(PUBLIC_DEAL_STATUSES))


def _has_active_deal():
    return exists().where(Deal.product_id == Product.id, Deal.status == "active")


class TopRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_category(self, slug: str) -> Category | None:
        return (await self.session.execute(
            select(Category).where(Category.slug == slug, Category.is_active.is_(True))
        )).scalar_one_or_none()

    async def ranked_products(self, category: Category, limit: int = TOP_SIZE) -> list[dict]:
        votes = func.count(ProductTopVote.id).label("vote_count")
        category_filter = (
            Product.subcategory_id == category.id if category.parent_id else Product.category_id == category.id
        )
        rows = (await self.session.execute(
            select(Product, votes)
            .outerjoin(ProductTopVote, ProductTopVote.product_id == Product.id)
            .where(category_filter, Product.status == "active", _has_public_deal())
            .group_by(Product.id)
            .order_by(votes.desc(), _has_active_deal().desc(), Product.created_at.asc(), Product.id.asc())
            .limit(limit)
        )).all()
        if not rows:
            return []

        # Oferta representativa: la activa más reciente; si no hay, la caducada más reciente.
        deals = (await self.session.execute(
            select(Deal)
            .where(Deal.product_id.in_([product.id for product, _ in rows]), Deal.status.in_(PUBLIC_DEAL_STATUSES))
            .order_by(case((Deal.status == "active", 0), else_=1), Deal.published_at.desc(), Deal.id.asc())
        )).scalars().all()
        representative: dict[str, Deal] = {}
        for deal in deals:
            representative.setdefault(deal.product_id, deal)

        ranked = []
        for position, (product, vote_count) in enumerate(rows, 1):
            deal = representative.get(product.id)
            ranked.append({
                "id": product.id,
                "title": product.title,
                "image_url": product.image_url,
                "deal_slug": deal.slug if deal else None,
                "deal_status": deal.status if deal else None,
                "current_price": float(deal.current_price) if deal and deal.status == "active" else None,
                "vote_count": vote_count,
                "position": position,
            })
        return ranked

    async def product_exists(self, product_id: str) -> bool:
        return (await self.session.execute(
            select(Product.id).where(Product.id == product_id, Product.status == "active", _has_public_deal())
        )).scalar_one_or_none() is not None

    async def toggle_vote(self, product_id: str, user_id: str) -> bool:
        removed = (await self.session.execute(
            delete(ProductTopVote)
            .where(ProductTopVote.product_id == product_id, ProductTopVote.user_id == user_id)
            .returning(ProductTopVote.id)
        )).scalar_one_or_none()
        if removed is None:
            await self.session.execute(
                insert(ProductTopVote).values(product_id=product_id, user_id=user_id)
                .on_conflict_do_nothing(constraint="uq_product_top_votes_product_user")
            )
        await self.session.commit()
        # Ante una carrera de dos inserciones simultáneas el voto queda registrado igualmente.
        return removed is None

    async def my_votes(self, product_ids: list[str], user_id: str) -> list[str]:
        if not product_ids:
            return []
        return list((await self.session.execute(
            select(ProductTopVote.product_id).where(
                ProductTopVote.product_id.in_(product_ids), ProductTopVote.user_id == user_id
            )
        )).scalars())
