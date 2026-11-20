"""Histórico de precios: reglas puras (sin BD).

Un punto por listing y día (hora de Madrid). Las estadísticas se calculan por
producto, juntando todas sus tiendas: el mínimo histórico de un producto es el
precio más bajo visto en cualquiera de ellas.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")

# Origen de cada observación.
SOURCE_PRICE_CHECK = "price_check"  # revisión diaria automática
SOURCE_DEAL = "deal"  # alta, reactivación o edición de un chollo
SOURCE_BACKFILL = "backfill"  # semilla inicial desde los listings existentes

DEFAULT_WINDOW_DAYS = 90

_CENT = Decimal("0.01")


def observed_day(now: datetime) -> date:
    """Día natural de la observación en España (la revisión corre de madrugada)."""
    return now.astimezone(MADRID).date()


def window_start(today: date, window_days: int) -> date:
    """Primer día incluido en una ventana de `window_days` que acaba hoy."""
    return today - timedelta(days=window_days - 1)


@dataclass(frozen=True)
class PriceObservation:
    """Un precio visto en un listing, listo para apuntarse en el histórico."""

    listing_id: str
    product_id: str
    store_id: str | None
    price: Decimal | float | None
    reference_price: Decimal | float | None
    in_stock: bool | None
    source: str
    observed_at: datetime


@dataclass(frozen=True)
class PricePoint:
    observed_on: date
    price: Decimal
    low_price: Decimal
    store_id: str | None = None


@dataclass(frozen=True)
class AllTimeSummary:
    """Lo que abarca todo el histórico (se calcula en SQL)."""

    days_tracked: int
    first_seen: date | None
    low: Decimal | None
    low_on: date | None


@dataclass(frozen=True)
class PriceStats:
    """Resumen del histórico de un producto. Todo None si no hay puntos."""

    days_tracked: int
    first_seen: date | None
    all_time_low: Decimal | None
    all_time_low_on: date | None
    window_days: int
    window_low: Decimal | None
    window_high: Decimal | None
    window_average: Decimal | None


def daily_lows(points: list[PricePoint]) -> dict[date, Decimal]:
    """El precio más bajo de cada día. Con varias tiendas el mismo día cuenta la
    más barata, para que la media no se sesgue hacia la tienda con más puntos."""
    by_day: dict[date, Decimal] = {}
    for point in points:
        low = min(point.low_price, point.price)
        by_day[point.observed_on] = min(by_day.get(point.observed_on, low), low)
    return by_day


def compute_stats(
    window_points: list[PricePoint], today: date, window_days: int, all_time: AllTimeSummary
) -> PriceStats:
    """Estadísticas de la ventana (mínimo, máximo y media) más el resumen total."""
    since = window_start(today, window_days)
    window = [low for day, low in daily_lows(window_points).items() if since <= day <= today]
    return PriceStats(
        days_tracked=all_time.days_tracked,
        first_seen=all_time.first_seen,
        all_time_low=all_time.low,
        all_time_low_on=all_time.low_on,
        window_days=window_days,
        window_low=min(window) if window else None,
        window_high=max(window) if window else None,
        window_average=(sum(window) / len(window)).quantize(_CENT) if window else None,
    )
