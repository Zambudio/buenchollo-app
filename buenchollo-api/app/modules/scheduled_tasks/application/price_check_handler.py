"""Revisión diaria del catálogo (tarea programada `price_check`).

Ya no borra chollos: por cada listing de Amazon consulta precio y stock,
actualiza el listing y su deal principal y aplica las reglas de
`catalog.domain.offer_rules` (terminar / reactivar oferta). Solo elimina una
tienda del producto tras `purge_after_days` sin disponibilidad confirmada; si
el producto se queda sin tiendas, el repositorio elimina producto y deals.

Un fallo de Amazon en un lote (tras un reintento) deja ese lote intacto: ni
precio, ni disponibilidad, ni transiciones, ni purga. Las peticiones se
espacian (la Creators API admite ~1 por segundo y responde 429 si se excede) y
solo se consultan identificadores con formato ASIN: uno inválido haría que
Amazon rechazase el lote entero con un 400.
"""

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from starlette.concurrency import run_in_threadpool

from app.modules.catalog.domain.models import AVAILABLE
from app.modules.catalog.domain.offer_rules import (
    Observation,
    OfferState,
    availability_of,
    decide,
    rules_config_from,
)
from app.modules.products.infrastructure.amazon_client import MAX_ITEMS_PER_REQUEST
from app.modules.scheduled_tasks.application.task_handler import (
    Candidate,
    PreviewResult,
    ProductVerifier,
)

logger = logging.getLogger(__name__)

DEFAULT_PURGE_AFTER_DAYS = 30
_PURGE_RANGE = range(7, 366)
_CENT = Decimal("0.01")
# Patrón que la propia Creators API exige a cada itemId.
_ASIN = re.compile(r"^(?:[0-9]{9}[0-9X]|[A-Z][A-Z0-9]{9})$")
MIN_SECONDS_BETWEEN_REQUESTS = 1.1
RETRY_DELAY_SECONDS = 2.0
_NOT_FOUND = Observation(found=False, in_stock=False, price=None, reference_price=None, discount_percentage=None)


@dataclass
class ListingCheck:
    listing: object
    deal: object | None
    observation: Observation | None  # None = la consulta de su lote falló


@dataclass
class _Outcome:
    transition: str | None
    reason: str | None
    availability: str
    unavailable_since: datetime | None
    purge: bool


def _money(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def purge_after_days_from(config: dict) -> int:
    try:
        days = int(config.get("purge_after_days", DEFAULT_PURGE_AFTER_DAYS))
    except (TypeError, ValueError):
        return DEFAULT_PURGE_AFTER_DAYS
    return days if days in _PURGE_RANGE else DEFAULT_PURGE_AFTER_DAYS


class PriceCheckHandler:
    def __init__(self, product_verifier: ProductVerifier, catalog_repo, sleep=time.sleep):
        self.product_verifier = product_verifier
        self.catalog_repo = catalog_repo
        self._sleep = sleep
        self._last_request: float | None = None

    async def collect(self, between=None) -> list[ListingCheck]:
        """Carga los listings y consulta Amazon. `between` (p. ej. el commit de
        la sesión) se llama entre ambas cosas para no tener una transacción
        abierta durante las llamadas HTTP."""
        pairs = await self.catalog_repo.get_checkable()
        if between is not None:
            await between()
        return await run_in_threadpool(self.fetch, pairs)

    def fetch(self, pairs: list[tuple]) -> list[ListingCheck]:
        valid = [(listing, deal) for listing, deal in pairs if _ASIN.match(listing.external_id or "")]
        invalid = [(listing, deal) for listing, deal in pairs if not _ASIN.match(listing.external_id or "")]
        if invalid:
            logger.warning(
                "%d listing(s) con identificador que no es un ASIN válido; no se consultan: %s",
                len(invalid), [listing.external_id for listing, _ in invalid][:10],
            )
        checks = [ListingCheck(listing, deal, None) for listing, deal in invalid]
        for i in range(0, len(valid), MAX_ITEMS_PER_REQUEST):
            batch = valid[i : i + MAX_ITEMS_PER_REQUEST]
            products = self._fetch_batch([listing.external_id for listing, _ in batch])
            for listing, deal in batch:
                # Ausente del resultado = desconocido (no se toca); None = no existe.
                if products is None or listing.external_id not in products:
                    observation = None
                else:
                    observation = self._observe(products[listing.external_id])
                checks.append(ListingCheck(listing, deal, observation))
        return checks

    def _fetch_batch(self, asins: list[str]) -> dict | None:
        """Una petición espaciada respecto a la anterior, con un reintento. None
        si Amazon falla las dos veces."""
        for attempt in (1, 2):
            self._pace(RETRY_DELAY_SECONDS if attempt == 2 else MIN_SECONDS_BETWEEN_REQUESTS)
            try:
                return self.product_verifier.get_product_previews(asins)
            except Exception:
                logger.warning(
                    "Fallo consultando Amazon (intento %d/2) para %d ASIN", attempt, len(asins),
                    exc_info=attempt == 2,
                )
        return None

    def _pace(self, min_interval: float) -> None:
        if self._last_request is not None:
            wait = min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = time.monotonic()

    @staticmethod
    def _observe(product) -> Observation:
        if product is None:
            return _NOT_FOUND
        return Observation(
            found=True,
            in_stock=bool(product.in_stock),
            price=_money(product.current_price),
            reference_price=_money(product.original_price),
            discount_percentage=product.discount_percentage,
        )

    def evaluate(self, checks: list[ListingCheck], config: dict, now: datetime) -> PreviewResult:
        candidates = []
        for check in checks:
            outcome = self._outcome(check, config, now)
            if outcome is None or check.deal is None:
                continue
            if outcome.purge:
                candidates.append(self._candidate(check, "purged", "listing_purged"))
            elif outcome.transition:
                candidates.append(self._candidate(check, outcome.transition, outcome.reason))
        return PreviewResult(total_checked=len(checks), candidates=candidates)

    async def apply(self, checks: list[ListingCheck], config: dict, now: datetime) -> list[Candidate]:
        removed = await self.catalog_repo.delete_orphan_products()
        if removed:
            logger.info("Catálogo: %d producto(s) sin chollos eliminados", removed)
        applied: list[Candidate] = []
        for check in checks:
            outcome = self._outcome(check, config, now)
            if outcome is None:
                continue
            self._write_observation(check, outcome, now)
            if outcome.purge:
                candidate = self._candidate(check, "purged", "listing_purged") if check.deal else None
                deleted = await self.catalog_repo.purge_listing(check.listing)
                if candidate:
                    candidate.reason = "product_purged" if deleted else "listing_purged"
                    applied.append(candidate)
                continue
            if outcome.transition:
                candidate = self._candidate(check, outcome.transition, outcome.reason)
                self._write_transition(check, outcome, now)
                applied.append(candidate)
        return applied

    def _outcome(self, check: ListingCheck, config: dict, now: datetime) -> _Outcome | None:
        obs = check.observation
        if obs is None:
            return None
        availability = availability_of(obs)
        since = None if availability == AVAILABLE else (check.listing.unavailable_since or now)
        purge = since is not None and since <= now - timedelta(days=purge_after_days_from(config))
        transition = reason = None
        if check.deal is not None and not purge:
            decision, reason = decide(self._state(check.deal), obs, rules_config_from(config), now=now)
            if decision == "end":
                transition = "offer_ended"
            elif decision == "reactivate":
                transition, reason = "reactivated", "deal_again"
            elif decision == "drop":
                transition = "price_dropped"
        return _Outcome(transition, reason, availability, since, purge)

    @staticmethod
    def _state(deal) -> OfferState:
        return OfferState(
            status=deal.status,
            offer_end_reason=deal.offer_end_reason,
            offer_price=_money(deal.offer_price),
            previous_price=_money(deal.previous_price),
            expires_at=getattr(deal, "expires_at", None),
            notified_price=_money(getattr(deal, "admin_notified_price", None)),
        )

    @staticmethod
    def _write_observation(check: ListingCheck, outcome: _Outcome, now: datetime) -> None:
        obs, listing, deal = check.observation, check.listing, check.deal
        listing.availability = outcome.availability
        listing.unavailable_since = outcome.unavailable_since
        listing.in_stock = obs.in_stock if obs.found else None
        listing.last_checked_at = now
        if obs.price is not None:
            listing.current_price = obs.price
        if obs.reference_price is not None:
            listing.reference_price = obs.reference_price
        if obs.found:
            listing.discount_percentage = obs.discount_percentage
        if deal is None:
            return
        deal.last_price_check_at = now
        if obs.price is None:
            return
        deal.current_price = obs.price
        if obs.reference_price is not None:
            deal.previous_price = obs.reference_price
        if obs.discount_percentage is not None:
            deal.discount_percentage = obs.discount_percentage
        previous = _money(deal.previous_price)
        deal.savings_amount = previous - obs.price if previous is not None and previous > obs.price else None

    @staticmethod
    def _write_transition(check: ListingCheck, outcome: _Outcome, now: datetime) -> None:
        deal = check.deal
        if outcome.transition == "offer_ended":
            deal.status = "expired"
            deal.offer_end_reason = outcome.reason
        elif outcome.transition == "price_dropped":
            # Sigue en oferta; offer_price no cambia (la bajada se mide contra el
            # precio del último aviso, que guarda el notificador).
            pass
        else:
            deal.status = "active"
            deal.offer_end_reason = None
            deal.published_at = now
            deal.offer_price = check.observation.price

    @staticmethod
    def _candidate(check: ListingCheck, transition: str, reason: str) -> Candidate:
        deal, obs = check.deal, check.observation
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
            external_id=deal.external_id or check.listing.external_id,
            affiliate_url=deal.affiliate_url,
            source_url=deal.source_url,
            old_price=_money(deal.offer_price if deal.offer_price is not None else deal.current_price),
            previous_price=_money(deal.previous_price),
            discount_percentage=deal.discount_percentage,
            new_price=obs.price if obs is not None else None,
            reason=reason,
            transition=transition,
        )
