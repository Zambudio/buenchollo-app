"""Caso de uso: el ranking de la semana.

Los chollos activos con más descuento publicados o reactivados en la semana
(`deals.domain.week`). Lo usan el lateral «Top de la semana» de la portada y el
resumen «Los chollos de la semana» de los domingos, así que ambos muestran
siempre la misma lista. Se calcula en cada petición: cada chollo nuevo con
buen descuento entra al momento y los que dejan de estar en oferta salen solos.

Los chollos de Awin/Tradedoubler solo entran si siguen cumpliendo sus reglas
de publicación (programa aprobado, datos no caducados…), como en
`/telegram/notify`.
"""

import logging
from datetime import datetime, timezone

from app.modules.affiliates.application.programs import needs_network_rules
from app.modules.deals.domain.week import week_window

logger = logging.getLogger(__name__)

WEEKLY_TOP_MAX = 10
# Se piden más de los que se muestran por si alguno no pasa las reglas de afiliación.
_CANDIDATES = 25


async def _publishable(deal, guard) -> bool:
    if guard is None:
        return True
    from app.modules.deals.application.deal_service import _GUARD_FIELDS

    data = {column: getattr(deal, column, None) for column in _GUARD_FIELDS}
    data["status"] = "active"
    if not needs_network_rules(data):
        return True
    blockers = await guard.blockers_for(data)
    if blockers:
        logger.info("Ranking semanal: se omite %s (%s)", getattr(deal, "slug", "?"), ", ".join(blockers))
    return not blockers


async def weekly_top(repo, guard=None, limit: int = WEEKLY_TOP_MAX, now: datetime | None = None) -> list:
    window = week_window(now or datetime.now(timezone.utc))
    limit = min(limit, WEEKLY_TOP_MAX)
    deals = []
    for deal in await repo.get_top_discount_active_since(window.since, limit=_CANDIDATES):
        if await _publishable(deal, guard):
            deals.append(deal)
            if len(deals) == limit:
                break
    return deals
