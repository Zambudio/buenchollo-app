from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.telegram.domain.models import TelegramPublication


class TelegramPublicationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, publication: TelegramPublication) -> TelegramPublication:
        self.session.add(publication)
        await self.session.flush()
        return publication

    async def list_for_deal(self, deal_id: str, limit: int = 20) -> list[TelegramPublication]:
        result = await self.session.execute(
            select(TelegramPublication)
            .where(TelegramPublication.deal_id == deal_id)
            .order_by(TelegramPublication.sent_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def latest_for_deal(self, deal_id: str) -> TelegramPublication | None:
        """Última publicación registrada del chollo, en cualquier canal: Pedro
        publica en el canal Admin y desde allí reenvía al oficial. Los avisos
        de la revisión de precios no se registran, así que no cuentan."""
        result = await self.session.execute(
            select(TelegramPublication)
            .where(TelegramPublication.deal_id == deal_id)
            .order_by(TelegramPublication.sent_at.desc())
            .limit(1)
        )
        return result.scalars().first()
