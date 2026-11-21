"""Contador de «novedades desde tu última visita» (GET /v1/deals/new-count)."""

from datetime import datetime, timedelta, timezone

from app.main import app
from app.modules.deals.api.router import get_deal_repository
from app.modules.deals.application.new_deals import NEW_COUNT_MAX_DAYS


class FakeRepo:
    def __init__(self):
        self.since = None

    async def count_active_since(self, since):
        self.since = since
        return 7


def _get(client, repo, since: str):
    app.dependency_overrides[get_deal_repository] = lambda: repo
    try:
        return client.get("/v1/deals/new-count", params={"since": since})
    finally:
        app.dependency_overrides.pop(get_deal_repository, None)


def test_cuenta_los_nuevos_desde_la_ultima_visita(integration_client):
    repo = FakeRepo()
    since = datetime.now(timezone.utc) - timedelta(hours=5)
    resp = _get(integration_client, repo, since.isoformat())
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"count": 7}
    assert abs((repo.since - since).total_seconds()) < 1


def test_no_mira_mas_alla_de_30_dias(integration_client):
    repo = FakeRepo()
    resp = _get(integration_client, repo, "2020-01-01T00:00:00Z")
    assert resp.status_code == 200
    floor = datetime.now(timezone.utc) - timedelta(days=NEW_COUNT_MAX_DAYS)
    assert abs((repo.since - floor).total_seconds()) < 60


def test_fecha_invalida_da_422(integration_client):
    assert _get(integration_client, FakeRepo(), "ayer").status_code == 422
