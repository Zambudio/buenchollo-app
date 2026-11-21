"""Ranking «Top de la semana» (GET /v1/deals/weekly-top)."""

from datetime import datetime, timezone

import pytest

from app.main import app
from app.modules.deals.api.router import get_deal_repository
from app.modules.deals.application.weekly_top import weekly_top


class FakeRepo:
    def __init__(self):
        self.args = None

    async def get_top_discount_active_since(self, since, limit):
        self.args = (since, limit)
        return []


@pytest.mark.asyncio
async def test_usa_la_semana_natural_en_hora_de_madrid_y_como_mucho_10():
    repo = FakeRepo()
    await weekly_top(repo, limit=50, now=datetime(2026, 11, 22, 21, 30, tzinfo=timezone.utc))
    since, limit = repo.args
    assert since.isoformat() == "2026-11-16T00:00:00+01:00"
    assert limit == 10


def test_endpoint_no_lo_captura_la_ruta_por_slug(integration_client):
    repo = FakeRepo()
    app.dependency_overrides[get_deal_repository] = lambda: repo
    try:
        resp = integration_client.get("/v1/deals/weekly-top", params={"limit": 5})
        too_many = integration_client.get("/v1/deals/weekly-top", params={"limit": 11})
    finally:
        app.dependency_overrides.pop(get_deal_repository, None)
    assert resp.status_code == 200 and resp.json() == []
    assert repo.args[1] == 5
    assert too_many.status_code == 422
