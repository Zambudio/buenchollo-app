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


def observed_day(now: datetime) -> date:
    """Día natural de la observación en España (la revisión corre de madrugada)."""
    return now.astimezone(MADRID).date()


@dataclass(frozen=True)
class PricePoint:
    observed_on: date
    price: Decimal
    low_price: Decimal
    store_id: str | None = None


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


_CENT = Decimal("0.01")


def compute_stats(points: list[PricePoint], today: date, window_days: int = DEFAULT_WINDOW_DAYS) -> PriceStats:
    """Mínimo histórico (con su fecha) y mínimo/máximo/media de la ventana.

    Con varias tiendas el mismo día, cada día cuenta con su precio más bajo:
    así la media no se sesga hacia la tienda que más puntos tenga.
    """
    if not points:
        return PriceStats(0, None, None, None, window_days, None, None, None)
    by_day: dict[date, Decimal] = {}
    for point in points:
        low = min(point.low_price, point.price)
        by_day[point.observed_on] = min(by_day.get(point.observed_on, low), low)
    days = sorted(by_day)
    low_on = min(days, key=lambda d: (by_day[d], -d.toordinal()))  # empate: el más reciente
    since = today - timedelta(days=window_days - 1)
    window = [by_day[d] for d in days if since <= d <= today]
    average = (sum(window) / len(window)).quantize(_CENT) if window else None
    return PriceStats(
        days_tracked=len(days),
        first_seen=days[0],
        all_time_low=by_day[low_on],
        all_time_low_on=low_on,
        window_days=window_days,
        window_low=min(window) if window else None,
        window_high=max(window) if window else None,
        window_average=average,
    )
