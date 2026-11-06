"""CatalogRepository contra PostgreSQL real (transacción revertida).

Requiere DATABASE_URL con la migración del catálogo aplicada (BD de local-env).
Se excluye del CI con -m "not integration".
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.modules.catalog.domain.models import Product, ProductListing
from app.modules.catalog.infrastructure.repository import CatalogRepository
from app.modules.deals.domain.models import Deal

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


async def _any_user_id(conn) -> str:
    """Un user_id válido para deal_votes: en la BD local (esquema de producción)
    la FK apunta a auth.users; en la de CI (create_all) no hay FK."""
    if (await conn.execute(text("SELECT to_regclass('auth.users')"))).scalar() is None:
        return str(uuid.uuid4())
    return str((await conn.execute(text("SELECT id FROM auth.users LIMIT 1"))).scalar_one())


def _deal(external_id: str | None, *, status="active", published_at=None, price=50.0, url=None) -> Deal:
    suffix = uuid.uuid4().hex[:10]
    return Deal(
        title=f"Producto {suffix}",
        slug=f"producto-repo-{suffix}",
        current_price=price,
        affiliate_url=url or f"https://www.amazon.es/dp/{external_id or 'B000000000'}?tag=x",
        status=status,
        external_id=external_id,
        published_at=published_at or datetime.now(timezone.utc),
        images=[],
    )


async def _add_linked(session, repo, deal: Deal) -> Deal:
    session.add(deal)
    await session.flush()
    await repo.link_new_deal(deal)
    await session.flush()
    return deal


async def test_link_new_deal_crea_producto_y_listing_amazon(session):
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal("B0REPOA001", price=42.0))

    listing = await session.get(ProductListing, deal.listing_id)
    product = await session.get(Product, deal.product_id)
    assert listing.source == "amazon"
    assert listing.external_id == "B0REPOA001"
    assert product.slug == deal.slug
    assert float(deal.offer_price) == 42.0


async def test_link_new_deal_reutiliza_listing_con_asin_en_minusculas(session):
    repo = CatalogRepository(session)
    first = await _add_linked(session, repo, _deal("B0REPOA002", status="expired"))
    second = await _add_linked(session, repo, _deal("b0repoa002"))
    assert second.listing_id == first.listing_id
    assert second.product_id == first.product_id


async def test_link_new_deal_sin_asin_es_manual(session):
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal(None, url="https://www.pccomponentes.com/x"))
    listing = await session.get(ProductListing, deal.listing_id)
    assert listing.source == "manual"
    assert listing.external_id is None


async def test_get_checkable_elige_el_deal_mas_reciente_y_excluye_manual(session):
    repo = CatalogRepository(session)
    now = datetime.now(timezone.utc)
    old = await _add_linked(session, repo, _deal("b0repoa003", status="expired", published_at=now - timedelta(days=5)))
    recent = await _add_linked(session, repo, _deal("B0REPOA003", status="active", published_at=now))
    await _add_linked(session, repo, _deal("B0rEPOA003", status="draft", published_at=now + timedelta(days=1)))
    manual = await _add_linked(session, repo, _deal(None, url="https://www.pccomponentes.com/y"))

    pairs = await repo.get_checkable()
    by_listing = {listing.id: deal for listing, deal in pairs}
    assert by_listing[recent.listing_id].id == recent.id
    assert old.listing_id == recent.listing_id
    assert manual.listing_id not in by_listing


async def test_get_checkable_listing_solo_con_draft_devuelve_none(session):
    repo = CatalogRepository(session)
    draft = await _add_linked(session, repo, _deal("B0REPOA004", status="draft"))
    pairs = dict((listing.id, deal) for listing, deal in await repo.get_checkable())
    assert pairs[draft.listing_id] is None


async def test_purge_listing_con_otra_tienda_repunta_y_no_borra(session):
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal("B0REPOA005"))
    other = ProductListing(
        product_id=deal.product_id, source="manual", external_id="OTRA-1",
        availability="available", current_price=30,
    )
    session.add(other)
    await session.flush()
    listing = await session.get(ProductListing, deal.listing_id)

    deleted = await repo.purge_listing(listing)

    assert deleted == []
    await session.refresh(deal)
    assert deal.listing_id == other.id
    assert await session.get(Product, deal.product_id) is not None


async def test_purge_listing_unico_borra_producto_deal_y_votos(session):
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal("B0REPOA006"))
    user_id = await _any_user_id(session)
    await session.execute(
        text("INSERT INTO deal_votes (deal_id, user_id, vote) VALUES (:d, :u, 1)"),
        {"d": deal.id, "u": user_id},
    )
    listing = await session.get(ProductListing, deal.listing_id)
    product_id, deal_id = deal.product_id, deal.id

    deleted = await repo.purge_listing(listing)

    assert deleted == [deal_id]
    session.expunge_all()
    assert await session.get(Product, product_id) is None
    assert (await session.execute(select(Deal).where(Deal.id == deal_id))).scalar() is None
    votes = (await session.execute(text("SELECT count(*) FROM deal_votes WHERE deal_id = :d"), {"d": deal_id})).scalar_one()
    assert votes == 0


async def test_get_purgeable(session):
    repo = CatalogRepository(session)
    now = datetime.now(timezone.utc)
    deal = await _add_linked(session, repo, _deal("B0REPOA007"))
    listing = await session.get(ProductListing, deal.listing_id)
    listing.availability = "not_found"
    listing.unavailable_since = now - timedelta(days=31)
    await session.flush()

    ids = {item.id for item in await repo.get_purgeable(now - timedelta(days=30))}
    assert listing.id in ids
    ids = {item.id for item in await repo.get_purgeable(now - timedelta(days=40))}
    assert listing.id not in ids


async def test_delete_product_if_orphan(session):
    repo = CatalogRepository(session)
    first = await _add_linked(session, repo, _deal("B0REPOA008", status="expired"))
    second = await _add_linked(session, repo, _deal("b0repoa008"))
    product_id = first.product_id

    assert await repo.delete_product_if_orphan(product_id) is False
    await session.delete(first)
    await session.delete(second)
    await session.flush()
    assert await repo.delete_product_if_orphan(product_id) is True
    session.expunge_all()
    assert await session.get(Product, product_id) is None


async def test_get_checkable_y_limpieza_ignoran_productos_sin_chollos(session):
    """Un chollo borrado fuera de DealService (SQL, cascadas) deja su producto
    huérfano: no se consulta a Amazon y la revisión diaria lo elimina."""
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal("B0REPOA009"))
    listing_id, product_id = deal.listing_id, deal.product_id
    await session.execute(text("DELETE FROM deals WHERE id = :d"), {"d": deal.id})
    session.expunge_all()

    assert listing_id not in {listing.id for listing, _ in await repo.get_checkable()}
    assert await repo.delete_orphan_products() >= 1
    assert await session.get(Product, product_id) is None
