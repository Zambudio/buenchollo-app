"""Tests unitarios para AlertMatcher.

Los repositorios se mockean. Verifican que sólo se crean notificaciones cuando
el deal está activo y se evita notificar alertas ya disparadas previamente.
"""
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.modules.alerts.application.alert_matcher import AlertMatcher
from app.modules.deals.domain.models import Deal


def _make_deal(status: str = "active") -> Deal:
    return Deal(
        id="deal-1",
        title="Producto X",
        slug="producto-x",
        current_price=10.0,
        affiliate_url="https://example.com",
        status=status,
    )


def _make_alert(alert_id: str, user_id: str = "user-1", name: str = "Mi alerta"):
    """Stub mínimo con los atributos que usa el matcher."""
    alert = MagicMock()
    alert.id = alert_id
    alert.user_id = user_id
    alert.name = name
    return alert


def _build_matcher(matching_alerts: list, already_notified: dict[str, bool] | None = None):
    already_notified = already_notified or {}
    alerts_repo = MagicMock()
    alerts_repo.get_matching_for_deal = AsyncMock(return_value=matching_alerts)
    alerts_repo.mark_triggered = AsyncMock()

    notifications_repo = MagicMock()
    notifications_repo.exists_for_alert_deal = AsyncMock(
        side_effect=lambda alert_id, _deal_id: already_notified.get(alert_id, False)
    )
    notifications_repo.create = AsyncMock()

    matcher = AlertMatcher(alerts_repo, notifications_repo)
    return matcher, alerts_repo, notifications_repo


@pytest.mark.asyncio
async def test_no_notifica_si_el_deal_no_esta_activo():
    matcher, alerts_repo, notifications_repo = _build_matcher([_make_alert("a1")])

    created = await matcher.notify_matching_alerts(_make_deal(status="draft"))

    assert created == 0
    alerts_repo.get_matching_for_deal.assert_not_called()
    notifications_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_crea_una_notificacion_por_alerta_coincidente():
    matcher, alerts_repo, notifications_repo = _build_matcher(
        [_make_alert("a1"), _make_alert("a2")]
    )

    created = await matcher.notify_matching_alerts(_make_deal())

    assert created == 2
    assert notifications_repo.create.await_count == 2
    assert alerts_repo.mark_triggered.await_count == 2


@pytest.mark.asyncio
async def test_omite_alertas_ya_notificadas_para_el_mismo_deal():
    matcher, _, notifications_repo = _build_matcher(
        [_make_alert("a1"), _make_alert("a2")],
        already_notified={"a1": True},
    )

    created = await matcher.notify_matching_alerts(_make_deal())

    assert created == 1
    notifications_repo.create.assert_awaited_once()
    payload = notifications_repo.create.await_args.args[0]
    assert payload["alert_id"] == "a2"
    assert payload["deal_id"] == "deal-1"
    assert payload["link_url"] == "/chollo/producto-x"


@pytest.mark.asyncio
async def test_devuelve_cero_si_no_hay_coincidencias():
    matcher, _, notifications_repo = _build_matcher([])

    created = await matcher.notify_matching_alerts(_make_deal())

    assert created == 0
    notifications_repo.create.assert_not_called()
