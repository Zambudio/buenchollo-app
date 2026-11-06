"""Reglas del ciclo de vida de una oferta (dominio puro, sin I/O).

Una oferta ya no se borra: termina (`end`) o se reactiva (`reactivate`) según
lo que la tienda informa en la revisión diaria. Fin de oferta = las reglas que
ya aplicaba `PriceCheckHandler`. Reactivación, con histéresis según por qué
terminó (para no alternar terminar/reactivar cada día):

- subió de precio → solo si vuelve a su precio de oferta (`offer_price`);
- agotado / retirado → si vuelve con stock dentro de la tolerancia;
- dejó de estar rebajado → si la tienda vuelve a marcar descuento ≥
  `min_discount_percent` y el precio está dentro de la tolerancia.

El descuento que informa la tienda es frente a SU precio de referencia: por sí
solo no prueba que el precio haya vuelto a bajar (datos reales: un producto
que subió de 114,15 a 123,29 € seguía marcado con un 10 %).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from app.modules.catalog.domain.models import AVAILABLE, NOT_FOUND, UNAVAILABLE

Decision = Literal["keep", "end", "reactivate", "none"]

DEFAULT_TOLERANCE_PERCENT = Decimal("10")
DEFAULT_MIN_DISCOUNT_PERCENT = 5

# Motivos de fin que la revisión diaria puede deshacer. Los fines por fecha
# (`expired_date`) o manuales los decidió una persona: no se reactivan solos.
REACTIVATABLE_REASONS = frozenset({"price_increase", "no_longer_deal", "out_of_stock", "not_found"})


@dataclass(frozen=True)
class Observation:
    """Lo que devolvió la tienda para un listing en una revisión correcta."""

    found: bool
    in_stock: bool
    price: Decimal | None
    reference_price: Decimal | None
    discount_percentage: int | None


@dataclass(frozen=True)
class OfferState:
    status: str
    offer_end_reason: str | None
    offer_price: Decimal | None
    previous_price: Decimal | None
    # Fin de oferta fijado a mano: pasado, no se reactiva (mark_expired_deals
    # la volvería a caducar por fecha a los pocos minutos).
    expires_at: datetime | None = None


@dataclass(frozen=True)
class RulesConfig:
    tolerance_percent: Decimal = DEFAULT_TOLERANCE_PERCENT
    min_discount_percent: int = DEFAULT_MIN_DISCOUNT_PERCENT


def rules_config_from(config: dict) -> RulesConfig:
    try:
        tolerance = Decimal(str(config.get("price_tolerance_percent", DEFAULT_TOLERANCE_PERCENT)))
        if not Decimal("0") <= tolerance <= Decimal("100"):
            tolerance = DEFAULT_TOLERANCE_PERCENT
    except (InvalidOperation, ValueError):
        tolerance = DEFAULT_TOLERANCE_PERCENT
    try:
        min_discount = int(config.get("min_discount_percent", DEFAULT_MIN_DISCOUNT_PERCENT))
        if not 0 <= min_discount <= 100:
            min_discount = DEFAULT_MIN_DISCOUNT_PERCENT
    except (TypeError, ValueError):
        min_discount = DEFAULT_MIN_DISCOUNT_PERCENT
    return RulesConfig(tolerance, min_discount)


def availability_of(obs: Observation) -> str:
    if not obs.found:
        return NOT_FOUND
    return AVAILABLE if obs.in_stock else UNAVAILABLE


def decide(
    state: OfferState, obs: Observation, cfg: RulesConfig, now: datetime | None = None
) -> tuple[Decision, str | None]:
    if state.status == "active":
        reason = _end_reason(state, obs, cfg)
        return ("end", reason) if reason else ("keep", None)
    if state.status == "expired" and state.offer_end_reason in REACTIVATABLE_REASONS:
        if state.expires_at is not None and now is not None and state.expires_at <= now:
            return ("none", None)
        return ("reactivate", None) if _is_deal_again(state, obs, cfg) else ("none", None)
    return ("none", None)


def _end_reason(state: OfferState, obs: Observation, cfg: RulesConfig) -> str | None:
    if not obs.found:
        return "not_found"
    if not obs.in_stock:
        return "out_of_stock"
    if obs.price is None:
        return None
    if state.offer_price is not None:
        maximum = state.offer_price * (Decimal("1") + cfg.tolerance_percent / Decimal("100"))
        if obs.price > maximum:
            return "price_increase"
    if obs.discount_percentage is not None and obs.discount_percentage <= 0:
        return "no_longer_deal"
    if (
        state.previous_price is not None
        and state.offer_price is not None
        and state.previous_price > state.offer_price
        and obs.price >= state.previous_price
    ):
        return "no_longer_deal"
    return None


def _is_deal_again(state: OfferState, obs: Observation, cfg: RulesConfig) -> bool:
    if not (obs.found and obs.in_stock) or obs.price is None:
        return False
    discounted = obs.discount_percentage is not None and obs.discount_percentage >= cfg.min_discount_percent
    if state.offer_price is None:
        return discounted
    if _end_reason(state, obs, cfg) is not None:
        return False
    if obs.price <= state.offer_price:
        return True
    if state.offer_end_reason == "price_increase":
        return False
    within_tolerance = obs.price <= state.offer_price * (Decimal("1") + cfg.tolerance_percent / Decimal("100"))
    if not within_tolerance:
        return False
    return discounted if state.offer_end_reason == "no_longer_deal" else True
