"""Puerto de resolución de chollos referenciados desde bloques de producto.

`blog` no debe acoplarse a los servicios internos de `deals` (contextos
distintos: contenido editorial vs. comercio). Este Protocol define el
único contrato que `blog` necesita; el adaptador concreto vive en
`infrastructure/deal_lookup_adapter.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DealSummary:
    id: str
    title: str
    slug: str
    image_url: str | None
    affiliate_url: str
    store_name: str | None
    current_price: float | None
    previous_price: float | None
    discount_percentage: int | None
    is_active: bool


class DealLookupPort(Protocol):
    async def get_many(self, deal_ids: list[str]) -> dict[str, DealSummary]:
        """Resuelve varios deal_id en una única operación (evita N+1)."""
        ...
