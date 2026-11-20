"""Reglas puras del histórico de precios y el caso de uso de consulta."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.modules.catalog.application.price_history_service import PriceHistoryService
from app.modules.catalog.domain.price_history import (
    AllTimeSummary,
    PricePoint,
    compute_stats,
    observed_day,
    window_start,
)

TODAY = date(2026, 11, 20)
NONE_SUMMARY = AllTimeSummary(0, None, None, None)


def _p(day: str, price: str, low: str | None = None, store: str | None = None) -> PricePoint:
    return PricePoint(date.fromisoformat(day), Decimal(price), Decimal(low or price), store)


def test_observed_day_usa_hora_de_madrid():
    # 23:30 UTC del 20 es ya día 21 en Madrid (UTC+1 en invierno).
    assert observed_day(datetime(2026, 11, 20, 23, 30, tzinfo=timezone.utc)) == date(2026, 11, 21)
    assert observed_day(datetime(2026, 11, 20, 22, 30, tzinfo=timezone.utc)) == date(2026, 11, 20)


def test_window_start_incluye_hoy():
    assert window_start(TODAY, 7) == date(2026, 11, 14)


def test_sin_puntos_todo_vacio():
    stats = compute_stats([], TODAY, 90, NONE_SUMMARY)
    assert stats.days_tracked == 0 and stats.all_time_low is None and stats.window_average is None


def test_ventana_usa_el_minimo_de_cada_dia_y_el_resumen_total():
    points = [_p("2026-10-01", "100"), _p("2026-11-01", "90", low="85"), _p("2026-11-20", "95")]
    summary = AllTimeSummary(4, date(2026, 6, 1), Decimal("60"), date(2026, 6, 1))
    stats = compute_stats(points, TODAY, 90, summary)
    assert (stats.days_tracked, stats.first_seen) == (4, date(2026, 6, 1))
    assert (stats.all_time_low, stats.all_time_low_on) == (Decimal("60"), date(2026, 6, 1))
    assert (stats.window_low, stats.window_high) == (Decimal("85"), Decimal("100"))
    assert stats.window_average == Decimal("93.33")


def test_varias_tiendas_el_mismo_dia_cuenta_la_mas_barata():
    points = [_p("2026-11-19", "100", store="a"), _p("2026-11-19", "80", store="b"), _p("2026-11-20", "90", store="a")]
    assert compute_stats(points, TODAY, 90, NONE_SUMMARY).window_average == Decimal("85.00")


def test_puntos_fuera_de_la_ventana_se_ignoran():
    points = [_p("2026-08-01", "10"), _p("2026-11-20", "90")]
    assert compute_stats(points, TODAY, 30, NONE_SUMMARY).window_low == Decimal("90")


class FakeRepo:
    def __init__(self):
        self.since = None

    async def price_points(self, product_id, since=None):
        self.since = since
        return [_p("2026-11-20", "90")]

    async def all_time_summary(self, product_id):
        return AllTimeSummary(1, TODAY, Decimal("90"), TODAY)


@pytest.mark.asyncio
async def test_servicio_pide_solo_la_ventana_y_combina_el_resumen():
    repo = FakeRepo()
    view = await PriceHistoryService(repo).get("p-1", 30, now=datetime(2026, 11, 20, 12, tzinfo=timezone.utc))
    assert repo.since == date(2026, 10, 22)
    assert view.stats.all_time_low == Decimal("90") and view.stats.window_average == Decimal("90.00")
    assert len(view.points) == 1
