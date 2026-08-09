import logging
from decimal import Decimal, ROUND_HALF_UP

from app.modules.scheduled_tasks.application.task_handler import (
    Candidate,
    PreviewResult,
    ProductVerifier,
)

logger = logging.getLogger(__name__)

_DEFAULT_TOLERANCE_PERCENT = 10


class PriceCheckHandler:
    def __init__(self, product_verifier: ProductVerifier, deal_repo):
        self.product_verifier = product_verifier
        self.deal_repo = deal_repo

    def evaluate(self, deals: list, config: dict) -> PreviewResult:
        tolerance = Decimal(str(config.get("price_tolerance_percent", _DEFAULT_TOLERANCE_PERCENT)))
        candidates: list[Candidate] = []
        for deal in deals:
            product = self.product_verifier.get_product_preview(deal.external_id)
            if product is None:
                continue
            reason = self._evaluate_one(deal, product, tolerance)
            if reason is None:
                continue
            candidates.append(self._to_candidate(deal, product, reason))
        return PreviewResult(total_checked=len(deals), candidates=candidates)

    @staticmethod
    def _evaluate_one(deal, product, tolerance: Decimal) -> str | None:
        if not product.in_stock:
            return "out_of_stock"
        if product.original_price is None or product.discount_percentage is None:
            return "no_longer_deal"
        if product.current_price is None:
            return None
        old_price = Decimal(str(deal.current_price))
        current_price = Decimal(str(product.current_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        maximum_price = old_price * (Decimal("1") + tolerance / Decimal("100"))
        if current_price > maximum_price:
            return "price_increase"
        return None

    @staticmethod
    def _to_candidate(deal, product, reason: str) -> Candidate:
        new_price = None
        if reason == "price_increase":
            new_price = Decimal(str(product.current_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Candidate(
            deal_id=deal.id,
            title=deal.title,
            slug=deal.slug,
            image_url=deal.image_url,
            description=deal.description,
            store_id=deal.store_id,
            store_name=deal.store.name if deal.store else None,
            category_id=deal.category_id,
            subcategory_id=deal.subcategory_id,
            external_id=deal.external_id,
            affiliate_url=deal.affiliate_url,
            source_url=deal.source_url,
            old_price=Decimal(str(deal.current_price)),
            new_price=new_price,
            reason=reason,
        )

    async def execute(self, candidates: list[Candidate]) -> list[Candidate]:
        deleted: list[Candidate] = []
        for candidate in candidates:
            deal = await self.deal_repo.get_by_id(candidate.deal_id)
            if deal is None:
                continue
            await self.deal_repo.delete(deal)
            deleted.append(candidate)
        return deleted
