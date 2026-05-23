import logging
from app.modules.deals.domain.models import Deal
from app.modules.deals.domain.utils import auto_slug
from app.modules.deals.infrastructure.repository import DealRepository

logger = logging.getLogger(__name__)


class DealService:
    def __init__(self, repo: DealRepository):
        self.repo = repo

    async def create_deal(self, deal_data: dict, user_id: str) -> Deal:
        if not deal_data.get("slug"):
            deal_data["slug"] = auto_slug(deal_data["title"])

        if await self.repo.user_has_profile(user_id):
            deal_data["created_by"] = user_id
            logger.debug("created_by asignado a user_id=%s", user_id)
        else:
            deal_data.pop("created_by", None)
            logger.warning("Perfil no encontrado para user_id=%s; created_by quedará NULL", user_id)

        new_deal = Deal(**deal_data)
        created = await self.repo.create(new_deal)
        return await self.repo.get_by_id(created.id)

    async def update_deal(self, deal_id: str, update_data: dict) -> Deal | None:
        deal = await self.repo.get_by_id(deal_id)
        if not deal:
            return None
        for field, value in update_data.items():
            setattr(deal, field, value)
        await self.repo.update(deal)
        return await self.repo.get_by_id(deal_id)

    async def delete_deal(self, deal_id: str) -> bool:
        deal = await self.repo.get_by_id(deal_id)
        if not deal:
            return False
        await self.repo.delete(deal)
        return True

    async def process_vote(self, deal_id: str, user_id: str, vote: int) -> dict:
        """Aplica el voto (toggle si es el mismo) y devuelve los contadores actualizados."""
        current_vote = await self.repo.get_user_vote(deal_id, user_id)

        if current_vote == vote:
            await self.repo.delete_vote(deal_id, user_id)
            my_vote = 0
        else:
            await self.repo.upsert_vote(deal_id, user_id, vote)
            my_vote = vote

        counters = await self.repo.recalculate_votes(deal_id)
        return {**counters, "my_vote": my_vote}
