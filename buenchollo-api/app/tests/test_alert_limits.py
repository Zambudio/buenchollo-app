"""Tests unitarios (sin BD) de los límites de alertas: tope por usuario,
rate limit de creación y validación de longitudes en AlertUpdate."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.security import get_current_user
from app.main import app
from app.modules.alerts.api.router import _repo
from app.modules.alerts.api.schemas import AlertCreate, AlertUpdate
from app.modules.alerts.application.service import MAX_ALERTS_PER_USER, create_alert_for_user
from app.modules.alerts.domain.exceptions import AlertLimitReached


class FakeUser:
    id = "dbe6e006-4f3e-4be8-8351-7e264ed3acb6"


async def _fake_user():
    return FakeUser()


def _alert_obj():
    return {
        "id": "a1", "name": "Mi alerta", "keyword": None, "brand": None,
        "category_id": None, "store_id": None, "min_price": None, "max_price": None,
        "min_discount": None, "is_active": True, "last_triggered_at": None,
        "created_at": datetime.now(timezone.utc), "category": None, "store": None,
    }


def _repo_mock(count: int):
    repo = MagicMock()
    repo.count_by_user = AsyncMock(return_value=count)
    repo.create = AsyncMock(return_value=_alert_obj())
    return repo


@pytest.mark.asyncio
async def test_crea_alerta_por_debajo_del_tope():
    repo = _repo_mock(MAX_ALERTS_PER_USER - 1)
    await create_alert_for_user(repo, "u1", {"name": "x"})
    repo.create.assert_awaited_once_with("u1", {"name": "x"})


@pytest.mark.asyncio
async def test_rechaza_alerta_al_alcanzar_el_tope():
    repo = _repo_mock(MAX_ALERTS_PER_USER)
    with pytest.raises(AlertLimitReached):
        await create_alert_for_user(repo, "u1", {"name": "x"})
    repo.create.assert_not_awaited()


def test_tope_de_alertas_se_traduce_a_429_con_mensaje_en_espanol():
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[_repo] = lambda: _repo_mock(MAX_ALERTS_PER_USER)
    try:
        r = TestClient(app).post("/v1/alerts", json={"name": "Otra alerta"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 429
    assert "máximo de 50 alertas" in r.json()["detail"]


def test_post_alertas_tiene_rate_limit_10_por_minuto():
    from app.core.rate_limit import limiter

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[_repo] = lambda: _repo_mock(0)
    limiter.reset()
    try:
        client = TestClient(app)
        codes = [client.post("/v1/alerts", json={"name": "Alerta"}).status_code for _ in range(11)]
    finally:
        app.dependency_overrides.clear()
        limiter.reset()
    assert codes[:10] == [201] * 10
    assert codes[10] == 429


@pytest.mark.parametrize("field,limit", [("keyword", 200), ("brand", 100), ("name", 100)])
def test_alert_update_tiene_los_mismos_max_length_que_create(field, limit):
    AlertUpdate(**{field: "a" * limit})
    with pytest.raises(ValidationError):
        AlertUpdate(**{field: "a" * (limit + 1)})
    with pytest.raises(ValidationError):
        AlertCreate(**{"name": "ok", field: "a" * (limit + 1)})
