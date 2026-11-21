"""Caso de uso: ranking «Top de la semana» (lateral de la portada).

Los chollos activos con más descuento publicados o reactivados en la semana
(`deals.domain.week`). Se calcula en cada petición: cada chollo nuevo con buen
descuento entra al momento y los que dejan de estar en oferta salen solos.
"""

from datetime import datetime, timezone

from app.modules.deals.domain.week import week_window

WEEKLY_TOP_MAX = 10


async def weekly_top(repo, limit: int = WEEKLY_TOP_MAX, now: datetime | None = None) -> list:
    window = week_window(now or datetime.now(timezone.utc))
    return await repo.get_top_discount_active_since(window.since, limit=min(limit, WEEKLY_TOP_MAX))
