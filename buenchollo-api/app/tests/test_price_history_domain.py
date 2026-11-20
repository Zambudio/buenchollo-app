"""Reglas puras del histórico de precios: día de observación y estadísticas."""

from datetime import date, datetime, timezone
from decimal import Decimal

from app.modules.catalog.domain.price_history import PricePoint, compute_stats, observed_day


def _p(day: str, price: str, low: str | None = None, store: str | None = None) -> PricePoint:
    return PricePoint(date.fromisoformat(day), Decimal(price), Decimal(low or price), store)


def test_observed_day_usa_hora_de_madrid():
    # 23:30 UTC del 20 es ya día 21 en Madrid (UTC+1 en invierno).
    assert observed_day(datetime(2026, 11, 20, 23, 30, tzinfo=timezone.utc)) == date(2026, 11, 21)
    assert observed_day(datetime(2026, 11, 20, 22, 30, tzinfo=timezone.utc)) == date(2026, 11, 20)


def test_sin_puntos_todo_vacio():
    stats = compute_stats([], date(2026, 11, 20))
    assert stats.days_tracked == 0 and stats.all_time_low is None and stats.window_average is None


def test_minimo_historico_y_ventana():
    points = [
        _p("2026-06-01", "60"),  # fuera de la ventana de 90 días, pero es el mínimo histórico
        _p("2026-10-01", "100"),
        _p("2026-11-01", "90", low="85"),  # bajó a 85 durante el día
        _p("2026-11-20", "95"),
    ]
    stats = compute_stats(points, date(2026, 11, 20), window_days=90)
    assert stats.days_tracked == 4
    assert stats.first_seen == date(2026, 6, 1)
    assert stats.all_time_low == Decimal("60") and stats.all_time_low_on == date(2026, 6, 1)
    assert stats.window_low == Decimal("85")
    assert stats.window_high == Decimal("100")
    assert stats.window_average == Decimal("93.33")


def test_varias_tiendas_el_mismo_dia_cuenta_la_mas_barata():
    points = [_p("2026-11-19", "100", store="a"), _p("2026-11-19", "80", store="b"), _p("2026-11-20", "90", store="a")]
    stats = compute_stats(points, date(2026, 11, 20))
    assert stats.days_tracked == 2
    assert stats.window_average == Decimal("85.00")
    assert stats.all_time_low == Decimal("80")


def test_empate_en_minimo_devuelve_la_fecha_mas_reciente():
    points = [_p("2026-11-01", "50"), _p("2026-11-10", "50"), _p("2026-11-15", "70")]
    assert compute_stats(points, date(2026, 11, 20)).all_time_low_on == date(2026, 11, 10)
