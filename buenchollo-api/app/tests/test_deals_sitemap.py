"""Sitemap de chollos servido por la API (catálogo permanente: activos y sin oferta).

Antes el sitemap web leía `deals` con supabaseAdmin desde el Worker y, al fallar,
lo silenciaba: producción no publicaba ninguna URL de chollo.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.main import app
from app.modules.deals.api.router import get_deal_repository
from app.modules.deals.infrastructure.repository import DealRepository

WHEN = datetime(2026, 11, 5, 4, 0, tzinfo=timezone.utc)


class FakeRepo:
    async def get_sitemap_entries(self, limit: int = 5000):
        return [
            SimpleNamespace(slug="monitor", status="active", updated_at=WHEN, published_at=WHEN),
            SimpleNamespace(slug="ssd", status="expired", updated_at=None, published_at=WHEN),
        ]


def test_endpoint_sitemap_no_lo_captura_la_ruta_por_slug(integration_client):
    app.dependency_overrides[get_deal_repository] = lambda: FakeRepo()
    try:
        resp = integration_client.get("/v1/deals/sitemap")
    finally:
        app.dependency_overrides.pop(get_deal_repository, None)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [(e["slug"], e["status"]) for e in body] == [("monitor", "active"), ("ssd", "expired")]
    assert body[1]["updated_at"] is None


@pytest.mark.asyncio
async def test_repositorio_solo_activos_y_sin_oferta_y_solo_columnas_necesarias():
    result = Mock()
    result.all.return_value = []
    session = Mock()
    session.execute = AsyncMock(return_value=result)

    await DealRepository(session).get_sitemap_entries(limit=10)

    sql = str(session.execute.await_args.args[0].compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    ))
    assert "deals.status IN ('active', 'expired')" in sql
    assert "LIMIT 10" in sql
    assert "deals.description" not in sql
