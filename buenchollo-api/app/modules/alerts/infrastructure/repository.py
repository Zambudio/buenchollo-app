from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.alerts.domain.models import Alert
from app.modules.alerts.application.matching import matches_alert
from app.modules.deals.domain.models import Deal


class AlertRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user(self, user_id: str) -> list[Alert]:
        result = await self.db.execute(
            select(Alert)
            .where(Alert.user_id == user_id)
            .options(selectinload(Alert.category), selectinload(Alert.store))
            .order_by(Alert.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, alert_id: str, user_id: str) -> Alert | None:
        result = await self.db.execute(
            select(Alert)
            .where(Alert.id == alert_id, Alert.user_id == user_id)
            .options(selectinload(Alert.category), selectinload(Alert.store))
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: str, data: dict) -> Alert:
        alert = Alert(user_id=user_id, **data)
        self.db.add(alert)
        await self.db.flush()
        return await self.get_by_id(alert.id, user_id)

    async def update(self, alert: Alert, data: dict) -> Alert:
        for k, v in data.items():
            setattr(alert, k, v)
        await self.db.flush()
        return await self.get_by_id(alert.id, alert.user_id)

    async def delete(self, alert: Alert) -> None:
        await self.db.delete(alert)
        await self.db.flush()

    # ── Matching ──────────────────────────────────────────────────────────────

    async def get_matching_for_deal(self, deal: Deal) -> list[Alert]:
        """Devuelve las alertas activas con notify_in_app=True que coinciden con el deal.

        El repositorio recupera todos los candidatos; el matching es una decisión
        de negocio y delega en `matching.matches_alert` (capa application)."""
        result = await self.db.execute(
            select(Alert).where(Alert.is_active.is_(True), Alert.notify_in_app.is_(True))
        )
        candidates = list(result.scalars().all())
        return [a for a in candidates if matches_alert(a, deal)]

    async def mark_triggered(self, alert: Alert) -> None:
        alert.last_triggered_at = datetime.now(timezone.utc)
        await self.db.flush()
