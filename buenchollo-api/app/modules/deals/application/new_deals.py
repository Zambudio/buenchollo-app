"""Caso de uso: «novedades desde tu última visita»."""

from datetime import datetime, timedelta, timezone

# Más allá de esto no tiene sentido contar «novedades».
NEW_COUNT_MAX_DAYS = 30


async def count_new_since(repo, since: datetime, now: datetime | None = None) -> int:
    """Chollos activos publicados (o reactivados) desde `since`. Una fecha sin
    zona horaria se toma como UTC y como mucho se mira 30 días atrás."""
    now = now or datetime.now(timezone.utc)
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    return await repo.count_active_since(max(since, now - timedelta(days=NEW_COUNT_MAX_DAYS)))
