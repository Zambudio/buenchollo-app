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


async def _history(session, listing_id):
    from app.modules.catalog.domain.models import PriceHistory

    rows = await session.execute(
        select(PriceHistory).where(PriceHistory.listing_id == listing_id).order_by(PriceHistory.observed_on)
    )
    return list(rows.scalars())


async def test_link_new_deal_apunta_el_precio_inicial_en_el_historico(session):
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal("B0REPOH001", price=42.0))
    history = await _history(session, deal.listing_id)
    assert [(float(h.price), h.source) for h in history] == [(42.0, "deal")]
    assert history[0].product_id == deal.product_id


def _obs(deal, price, *, days=3, source="price_check"):
    from app.modules.catalog.domain.price_history import PriceObservation

    return PriceObservation(
        listing_id=deal.listing_id, product_id=deal.product_id, store_id=deal.store_id,
        price=price, reference_price=None, in_stock=True, source=source,
        observed_at=datetime.now(timezone.utc) + timedelta(days=days),
    )


async def test_record_prices_un_punto_por_dia_con_el_minimo_del_dia(session):
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal("B0REPOH002", price=50.0))
    await repo.record_prices([_obs(deal, 45)])
    await repo.record_prices([_obs(deal, 48)])
    await session.flush()

    history = await _history(session, deal.listing_id)
    assert len(history) == 2
    await session.refresh(history[-1])
    assert (float(history[-1].price), float(history[-1].low_price)) == (48.0, 45.0)

    summary = await repo.all_time_summary(deal.product_id)
    assert summary.days_tracked == 2 and float(summary.low) == 45.0
    points = await repo.price_points(deal.product_id, since=history[-1].observed_on)
    assert [float(p.price) for p in points] == [48.0]


async def test_edicion_manual_sustituye_el_minimo_del_dia(session):
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal("B0REPOH004", price=199.0))
    await repo.record_prices([_obs(deal, 1.99, days=0, source="deal")])  # precio mal tecleado
    await repo.record_prices([_obs(deal, 199, days=0, source="deal")])  # corregido
    history = await _history(session, deal.listing_id)
    await session.refresh(history[0])
    assert float(history[0].low_price) == 199.0


async def test_record_deal_price_no_apunta_si_el_chollo_cambio_de_tienda(session):
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal("B0REPOH005", price=30.0))
    deal.external_id = "OTRA-TIENDA-1"
    deal.current_price = 25.0
    await repo.record_deal_price(deal, now=datetime.now(timezone.utc) + timedelta(days=2))
    assert len(await _history(session, deal.listing_id)) == 1


async def test_record_prices_ignora_precios_nulos_o_cero(session):
    repo = CatalogRepository(session)
    deal = await _add_linked(session, repo, _deal("B0REPOH003", price=10.0))
    await repo.record_prices([_obs(deal, None, days=1), _obs(deal, 0, days=1)])
    assert len(await _history(session, deal.listing_id)) == 1
