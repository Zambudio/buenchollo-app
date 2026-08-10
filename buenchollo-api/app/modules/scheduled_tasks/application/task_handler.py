from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.modules.products.domain.entities import ProductPreview


@dataclass
class Candidate:
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


@dataclass
class PreviewResult:
    total_checked: int
    candidates: list[Candidate]


class ProductVerifier(Protocol):
    def get_product_preview(self, asin: str) -> ProductPreview | None: ...
    def get_product_previews(self, asins: list[str]) -> dict[str, ProductPreview | None]: ...


class TaskHandler(Protocol):
    def evaluate(self, deals: list, config: dict) -> PreviewResult: ...
    async def execute(self, candidates: list[Candidate]) -> list[Candidate]: ...
