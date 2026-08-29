import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.modules.products.infrastructure.amazon_client import MAX_ITEMS_PER_REQUEST
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
        raw_tolerance = config.get("price_tolerance_percent", _DEFAULT_TOLERANCE_PERCENT)
        try:
            tolerance = Decimal(str(raw_tolerance))
            if tolerance < 0 or tolerance > 100:
                tolerance = Decimal(str(_DEFAULT_TOLERANCE_PERCENT))
        except (InvalidOperation, ValueError):
            tolerance = Decimal(str(_DEFAULT_TOLERANCE_PERCENT))

        candidates: list[Candidate] = []
        # Se consulta Amazon en lotes de MAX_ITEMS_PER_REQUEST en vez de una
        # llamada HTTP por deal: con cientos de candidatos, ir uno a uno tarda
        # minutos y agota el timeout del navegador/proxy. El try/except es
        # por lote (no por deal) para que un fallo de red en un lote no
        # aborte el resto — mismo criterio que antes, ahora a nivel de lote.
        for i in range(0, len(deals), MAX_ITEMS_PER_REQUEST):
            batch = deals[i : i + MAX_ITEMS_PER_REQUEST]
            asins = [deal.external_id for deal in batch]
            try:
                products = self.product_verifier.get_product_previews(asins)
            except Exception:
                logger.warning(
                    "Fallo consultando Amazon para el lote %s; se omite del ciclo",
                    asins, exc_info=True,
                )
                continue
            for deal in batch:
                product = products.get(deal.external_id)
                if product is None:
                    continue
                try:
                    reason = self._evaluate_one(deal, product, tolerance)
                except Exception:
                    logger.warning(
                        "Fallo evaluando el deal %s (asin=%s); se omite de este ciclo",
                        deal.id, deal.external_id, exc_info=True,
                    )
                    continue
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
        prev_price = Decimal(str(deal.previous_price)) if getattr(deal, "previous_price", None) is not None else None
        return Candidate(
            deal_id=deal.id,
            title=deal.title,
            slug=deal.slug,
            image_url=deal.image_url,
            description=deal.description,
            short_description=getattr(deal, "short_description", None),
            store_id=deal.store_id,
            store_name=deal.store.name if deal.store else None,
            category_id=deal.category_id,
            subcategory_id=deal.subcategory_id,
            external_id=deal.external_id,
            affiliate_url=deal.affiliate_url,
            source_url=deal.source_url,
            old_price=Decimal(str(deal.current_price)),
            previous_price=prev_price,
            discount_percentage=getattr(deal, "discount_percentage", None),
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
