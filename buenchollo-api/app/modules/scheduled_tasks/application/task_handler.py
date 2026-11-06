from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol

from app.modules.products.domain.entities import ProductPreview

Transition = Literal["offer_ended", "reactivated", "purged"]


@dataclass
class Candidate:
    """Una transición de oferta (terminada, reactivada o tienda purgada), con la
    foto del deal que se guarda en el registro de ejecuciones."""

    deal_id: str
    title: str
    slug: str
    image_url: str | None
    description: str | None
    store_id: str | None
    store_name: str | None
    category_id: str | None
    subcategory_id: str | None
    external_id: str
    affiliate_url: str
    source_url: str | None
    old_price: Decimal
    new_price: Decimal | None
    reason: str
    transition: Transition = "offer_ended"
    previous_price: Decimal | None = None
    discount_percentage: int | None = None
    short_description: str | None = None


@dataclass
class PreviewResult:
    total_checked: int
    candidates: list[Candidate]


class ProductVerifier(Protocol):
    def get_product_previews(self, asins: list[str]) -> dict[str, ProductPreview | None]: ...


class TaskHandler(Protocol):
    async def collect(self, between=None) -> list: ...
    def evaluate(self, checks: list, config: dict, now: datetime) -> PreviewResult: ...
    async def apply(self, checks: list, config: dict, now: datetime) -> list[Candidate]: ...
