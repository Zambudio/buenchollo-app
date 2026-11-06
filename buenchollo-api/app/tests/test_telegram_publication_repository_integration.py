"""TelegramPublicationRepository contra PostgreSQL real (transacción revertida)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.modules.deals.domain.models import Deal
from app.modules.telegram.domain.models import TelegramPublication
from app.modules.telegram.infrastructure.publication_repository import TelegramPublicationRepository

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


async def test_ultima_publicacion_publica_ignora_el_canal_admin(session):
    suffix = uuid.uuid4().hex[:8]
    deal = Deal(title="P", slug=f"pub-{suffix}", current_price=10, affiliate_url="https://a", images=[],
                temperature=0, votes_up=0, votes_down=0, click_count=0, comment_count=0, favorite_count=0)
    session.add(deal)
    await session.flush()
    repo = TelegramPublicationRepository(session)
    now = datetime.now(timezone.utc)
    for kind, text, minutes in [("main", "vieja", 30), ("main", "buena", 20), ("admin", "aviso", 10)]:
        await repo.add(TelegramPublication(
            deal_id=deal.id, channel_id=f"-100{kind}", channel_kind=kind, source="panel",
            text=text, sent_at=now - timedelta(minutes=minutes),
        ))

    latest = await repo.latest_public_for_deal(deal.id)
    assert latest.text == "buena"
    assert [p.text for p in await repo.list_for_deal(deal.id)] == ["aviso", "buena", "vieja"]
