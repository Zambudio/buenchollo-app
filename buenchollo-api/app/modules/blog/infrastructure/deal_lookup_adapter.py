from app.modules.blog.domain.ports import DealSummary
from app.modules.deals.infrastructure.repository import DealRepository


class DealLookupAdapter:
    """Implementación de `DealLookupPort` sobre el repositorio de `deals`.

    Único punto donde `blog` toca infraestructura de `deals`; la capa de
    aplicación de blog solo conoce el Protocol.
    """

    def __init__(self, deal_repo: DealRepository):
        self.deal_repo = deal_repo

    async def get_many(self, deal_ids: list[str]) -> dict[str, DealSummary]:
        if not deal_ids:
            return {}
        deals = await self.deal_repo.get_many_by_ids(deal_ids)
        return {
            str(deal.id): DealSummary(
                id=str(deal.id),
                title=deal.title,
                slug=deal.slug,
                image_url=deal.image_url,
                affiliate_url=deal.affiliate_url,
                store_name=deal.store.name if deal.store else None,
                current_price=float(deal.current_price) if deal.status == "active" else None,
                previous_price=float(deal.previous_price) if deal.status == "active" and deal.previous_price else None,
                discount_percentage=deal.discount_percentage if deal.status == "active" else None,
                is_active=deal.status == "active",
            )
            for deal in deals
        }
