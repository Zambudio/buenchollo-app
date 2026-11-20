"""Caso de uso: consultar el histórico de precios de un producto."""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.modules.catalog.domain.price_history import (
    PricePoint,
    PriceStats,
    compute_stats,
    observed_day,
    window_start,
)


@dataclass(frozen=True)
class PriceHistoryView:
    product_id: str
    stats: PriceStats
    points: list[PricePoint]


class PriceHistoryService:
    def __init__(self, repo):
        self.repo = repo

    async def get(self, product_id: str, window_days: int, now: datetime | None = None) -> PriceHistoryView:
        """Puntos de la ventana y estadísticas; el mínimo histórico abarca todo
        el histórico pero se calcula en SQL, sin cargar los puntos antiguos."""
        today = observed_day(now or datetime.now(timezone.utc))
        points = await self.repo.price_points(product_id, since=window_start(today, window_days))
        all_time = await self.repo.all_time_summary(product_id)
        return PriceHistoryView(product_id, compute_stats(points, today, window_days, all_time), points)
