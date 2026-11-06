from app.modules.catalog.domain.exceptions import ProductNotFound
from app.modules.catalog.infrastructure.top_repository import TopRepository
from app.modules.categories.domain.exceptions import CategoryNotFound


class TopService:
    def __init__(self, repo: TopRepository):
        self.repo = repo

    async def list_top(self, slug: str) -> list[dict]:
        category = await self.repo.get_category(slug)
        if category is None:
            raise CategoryNotFound()
        return await self.repo.ranked_products(category)

    async def toggle_vote(self, product_id: str, user_id: str) -> bool:
        if not await self.repo.product_exists(product_id):
            raise ProductNotFound()
        return await self.repo.toggle_vote(product_id, user_id)

    async def my_votes(self, product_ids: list[str], user_id: str) -> list[str]:
        return await self.repo.my_votes(product_ids, user_id)
