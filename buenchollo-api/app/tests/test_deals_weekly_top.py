"""Ranking «Top de la semana» (GET /v1/deals/weekly-top)."""

from datetime import datetime, timezone
from types import SimpleNamespace

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
    since, _ = repo.args
    assert since.isoformat() == "2026-11-16T00:00:00+01:00"


@pytest.mark.asyncio
async def test_omite_los_de_redes_que_no_cumplen_las_reglas_y_corta_en_el_limite():
    class Repo(FakeRepo):
        async def get_top_discount_active_since(self, since, limit):
            self.args = (since, limit)
            return [
                SimpleNamespace(slug="awin", affiliate_url="https://www.awin1.com/cread.php?a=1", data_source="awin"),
                *[SimpleNamespace(slug=f"amz-{i}", affiliate_url=f"https://amzn.to/{i}") for i in range(12)],
            ]

    class Guard:
        async def blockers_for(self, data):
            return ["affiliate_program"]

    deals = await weekly_top(Repo(), Guard(), limit=10)
    assert [d.slug for d in deals] == [f"amz-{i}" for i in range(10)]


def test_endpoint_no_lo_captura_la_ruta_por_slug(integration_client):
    repo = FakeRepo()
    app.dependency_overrides[get_deal_repository] = lambda: repo
    try:
        resp = integration_client.get("/v1/deals/weekly-top", params={"limit": 5})
        too_many = integration_client.get("/v1/deals/weekly-top", params={"limit": 11})
    finally:
        app.dependency_overrides.pop(get_deal_repository, None)
    assert resp.status_code == 200 and resp.json() == []
    assert repo.args is not None  # consultó el ranking (25 candidatos para poder filtrar)
    assert too_many.status_code == 422


@pytest.mark.asyncio
async def test_la_semana_se_mide_por_la_primera_publicacion_no_por_la_reactivacion():
    """Un chollo antiguo reactivado (published_at renovado) no es «de la semana»."""
    from app.modules.deals.infrastructure.repository import DealRepository

    class Session:
        statement = None

        async def execute(self, statement):
            Session.statement = statement
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))

    await DealRepository(Session()).get_top_discount_active_since(datetime(2026, 11, 18, tzinfo=timezone.utc))
    where = str(Session.statement.whereclause)
    assert "deals.first_published_at >=" in where
    assert "deals.published_at >=" not in where
