from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.models import Product, ProductTopVote
from app.modules.categories.domain.models import Category
from app.modules.deals.domain.models import Deal


class TopRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_category(self, slug: str) -> Category | None:
        return (await self.session.execute(
            select(Category).where(Category.slug == slug, Category.is_active.is_(True))
        )).scalar_one_or_none()

    async def ranked_products(self, category: Category, limit: int = 10) -> list[dict]:
        votes = func.count(ProductTopVote.id).label("vote_count")
        active_offer = exists().where(Deal.product_id == Product.id, Deal.status == "active")
        category_filter = (
            Product.subcategory_id == category.id if category.parent_id else Product.category_id == category.id
        )
        rows = (await self.session.execute(
            select(Product, votes)
            .outerjoin(ProductTopVote, ProductTopVote.product_id == Product.id)
            .where(
                category_filter,
                Product.status == "active",
                exists().where(Deal.product_id == Product.id, Deal.status.in_(("active", "expired"))),
            )
            .group_by(Product.id)
            .order_by(votes.desc(), active_offer.desc(), Product.created_at.asc(), Product.id.asc())
            .limit(limit)
        )).all()
        if not rows:
            return []
        products = [row[0] for row in rows]
        deals = (await self.session.execute(
            select(Deal)
            .where(Deal.product_id.in_([product.id for product in products]), Deal.status.in_(("active", "expired")))
            .order_by(Deal.status.asc(), Deal.published_at.desc(), Deal.id.asc())
        )).scalars().all()
        representative: dict[str, Deal] = {}
        for deal in deals:
            representative.setdefault(deal.product_id, deal)
        return [
            {
                "id": product.id,
                "title": product.title,
                "image_url": product.image_url,
                "deal_slug": representative[product.id].slug if product.id in representative else None,
                "deal_status": representative[product.id].status if product.id in representative else None,
                "current_price": float(representative[product.id].current_price)
                if product.id in representative and representative[product.id].status == "active" else None,
                "vote_count": count,
                "position": index,
            }
            for index, (product, count) in enumerate(rows, 1)
        ]

    async def product_exists(self, product_id: str) -> bool:
        return (await self.session.execute(
            select(Product.id).where(
                Product.id == product_id,
                Product.status == "active",
                exists().where(Deal.product_id == Product.id, Deal.status.in_(("active", "expired"))),
            )
        )).scalar_one_or_none() is not None

    async def toggle_vote(self, product_id: str, user_id: str) -> bool:
        existing = (await self.session.execute(
            select(ProductTopVote.id).where(
                ProductTopVote.product_id == product_id, ProductTopVote.user_id == user_id
            )
        )).scalar_one_or_none()
        if existing:
            await self.session.execute(delete(ProductTopVote).where(ProductTopVote.id == existing))
            voted = False
        else:
            result = await self.session.execute(
                insert(ProductTopVote).values(product_id=product_id, user_id=user_id)
                .on_conflict_do_nothing(constraint="uq_product_top_votes_product_user")
            )
            voted = result.rowcount > 0
        await self.session.commit()
        return voted

    async def my_votes(self, product_ids: list[str], user_id: str) -> list[str]:
        if not product_ids:
            return []
        return list((await self.session.execute(
            select(ProductTopVote.product_id).where(
                ProductTopVote.product_id.in_(product_ids), ProductTopVote.user_id == user_id
            )
        )).scalars())
