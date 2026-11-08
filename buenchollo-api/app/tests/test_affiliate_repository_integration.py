"""AffiliateRepository contra PostgreSQL real (transacción revertida, FIXTURES).

Requiere DATABASE_URL con el esquema aplicado (local-env). Excluido del CI con
-m "not integration".
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.modules.affiliates.domain.models import AffiliateProgram
from app.modules.affiliates.domain.offers import normalize_product_url
from app.modules.affiliates.infrastructure.repository import AffiliateRepository

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(get_settings().database_url, connect_args={"statement_cache_size": 0})
    conn = await engine.connect()
    trans = await conn.begin()
    try:
        yield AsyncSession(bind=conn, expire_on_commit=False)
    finally:
        await trans.rollback()
        await conn.close()
        await engine.dispose()


def _row(program_id, generation, key, url, title, ean=None):
    return {
        "id": str(uuid.uuid4()),
        "program_id": program_id,
        "feed_id": "90001",
        "generation": generation,
        "product_key": key,
        "normalized_url": normalize_product_url(url),
        "merchant_url": url,
        "title": title,
        "ean": ean,
        "specs": {},
        "imported_at": datetime.now(timezone.utc),
    }


async def test_solo_la_generacion_activa_es_visible(session):
    advertiser = str(900000 + uuid.uuid4().int % 99999)
    program = AffiliateProgram(
        network="awin", advertiser_id=advertiser, name="FIXTURE", domains=["fixture-shop.example.com"], feeds=[]
    )
    session.add(program)
    await session.flush()
    repo = AffiliateRepository(session)
    url = "https://www.fixture-shop.example.com/monitor?color=negro"
    await repo.insert_feed_rows(
        [
            _row(program.id, 1, "K1", url, "FIXTURE Monitor 27 QHD", ean="8400000000017"),
            _row(program.id, 2, "K1", url, "FIXTURE Monitor 27 QHD (nueva generación parcial)"),
        ]
    )

    # Sin generación publicada no hay catálogo.
    assert await repo.find_feed_products(program, normalized_url=normalize_product_url(url)) == []

    program.feeds = [{"feed_id": "90001", "selected": True, "generation": 1}]
    found = await repo.find_feed_products(program, normalized_url=normalize_product_url(url))
    assert [r.title for r in found] == ["FIXTURE Monitor 27 QHD"]
    assert len(await repo.find_feed_products(program, ean="8400000000017")) == 1
    assert len(await repo.feed_candidates(program, ["monitor", "inexistente"])) == 1

    await repo.delete_generation(program.id, "90001", keep=2)
    program.feeds = [{"feed_id": "90001", "selected": True, "generation": 2}]
    found = await repo.find_feed_products(program, product_key="K1")
    assert [r.title for r in found] == ["FIXTURE Monitor 27 QHD (nueva generación parcial)"]

    assert [p.id for p in await repo.programs_for_url("https://shop.fixture-shop.example.com/x")] == [program.id]
