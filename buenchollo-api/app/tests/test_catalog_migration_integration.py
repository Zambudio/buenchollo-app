"""Backfill del catálogo permanente contra PostgreSQL real, dentro de una
transacción que se revierte. Requiere la BD con la migración
`20261105120000` aplicada (p. ej. la local de `local-env`).

Se excluye del CI con -m "not integration".
"""

import importlib.util
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261105120000_permanent_catalogue.py"
)


def _load_backfill():
    spec = importlib.util.spec_from_file_location("permanent_catalogue_migration", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.backfill_catalog


@pytest_asyncio.fixture
async def conn():
    url = get_settings().database_url
    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
    connection = await engine.connect()
    trans = await connection.begin()
    try:
        yield connection
    finally:
        await trans.rollback()
        await connection.close()
        await engine.dispose()


async def _any_user_id(conn) -> str:
    """Un user_id válido para deal_votes: en la BD local (esquema de producción)
    la FK apunta a auth.users; en la de CI (create_all) no hay FK."""
    if (await conn.execute(text("SELECT to_regclass('auth.users')"))).scalar() is None:
        return str(uuid.uuid4())
    return str((await conn.execute(text("SELECT id FROM auth.users LIMIT 1"))).scalar_one())


async def _insert_deal(conn, *, external_id, status, published_at, price):
    deal_id = str(uuid.uuid4())
    await conn.execute(
        text(
            "INSERT INTO deals (id, title, slug, current_price, previous_price, affiliate_url, "
            "canonical_url, status, source, external_id, published_at, images, temperature, "
            "votes_up, votes_down, click_count, comment_count, favorite_count, show_keepa_chart) VALUES "
            "(:id, :title, :slug, :price, :prev, :url, :canon, :status, 'manual', :ext, :pub, '[]', "
            "0, 0, 0, 0, 0, 0, false)"
        ),
        {
            "id": deal_id,
            "title": f"Producto {deal_id[:6]}",
            "slug": f"producto-test-{deal_id}",
            "price": price,
            "prev": price + 10,
            "url": "https://www.amazon.es/dp/B0TESTA001?tag=x",
            "canon": "https://www.amazon.es/dp/B0TESTA001" if external_id else None,
            "status": status,
            "ext": external_id,
            "pub": published_at,
        },
    )
    return deal_id


async def test_backfill_agrupa_por_asin_sin_perder_deals_ni_votos(conn):
    now = datetime.now(timezone.utc)
    old_active = await _insert_deal(
        conn, external_id="b0testa001", status="active", published_at=now - timedelta(days=3), price=50
    )
    new_active = await _insert_deal(
        conn, external_id="B0TESTA001", status="active", published_at=now, price=45
    )
    manual = await _insert_deal(
        conn, external_id=None, status="active", published_at=now, price=20
    )
    user_id = await _any_user_id(conn)
    await conn.execute(
        text("INSERT INTO deal_votes (deal_id, user_id, vote) VALUES (:d, :u, 1)"),
        {"d": old_active, "u": user_id},
    )

    await conn.run_sync(_load_backfill())

    rows = (
        await conn.execute(
            text(
                "SELECT id::text, product_id::text, listing_id::text, status, offer_price, "
                "offer_end_reason FROM deals WHERE id IN (:a, :b, :c)"
            ),
            {"a": old_active, "b": new_active, "c": manual},
        )
    ).all()
    by_id = {r[0]: r for r in rows}
    assert len(by_id) == 3
    assert all(r[1] and r[2] for r in rows)
    # Mismo ASIN (sin distinguir mayúsculas) → mismo producto y listing
    assert by_id[old_active][1] == by_id[new_active][1]
    assert by_id[old_active][2] == by_id[new_active][2]
    assert by_id[manual][1] != by_id[new_active][1]
    # Solo el más reciente sigue activo
    assert by_id[new_active][3] == "active"
    assert by_id[old_active][3] == "expired"
    assert by_id[old_active][5] == "manual"
    assert float(by_id[new_active][4]) == 45.0

    votes = (
        await conn.execute(text("SELECT count(*) FROM deal_votes WHERE deal_id = :d"), {"d": old_active})
    ).scalar_one()
    assert votes == 1

    listing = (
        await conn.execute(
            text(
                "SELECT source, external_id, availability, current_price, reference_price "
                "FROM product_listings WHERE id = :l"
            ),
            {"l": by_id[new_active][2]},
        )
    ).one()
    assert listing[0] == "amazon"
    assert listing[1] == "B0TESTA001"
    assert listing[2] == "unknown"
    assert float(listing[3]) == 45.0
    assert float(listing[4]) == 55.0

    manual_listing = (
        await conn.execute(
            text("SELECT source, external_id FROM product_listings WHERE id = :l"),
            {"l": by_id[manual][2]},
        )
    ).one()
    assert manual_listing[1] is None


async def test_backfill_es_idempotente(conn):
    await _insert_deal(
        conn, external_id="B0TESTA002", status="expired", published_at=datetime.now(timezone.utc), price=10
    )
    backfill = _load_backfill()
    await conn.run_sync(backfill)
    products_before = (await conn.execute(text("SELECT count(*) FROM products"))).scalar_one()
    await conn.run_sync(backfill)
    products_after = (await conn.execute(text("SELECT count(*) FROM products"))).scalar_one()
    assert products_after == products_before


async def test_backfill_admite_external_id_largo(conn):
    """deals.external_id no tiene límite de longitud: el backfill (que corre al
    arrancar el contenedor de producción) no puede fallar por uno largo."""
    long_id = "SKU-" + "X" * 90
    deal_id = await _insert_deal(
        conn, external_id=long_id, status="active", published_at=datetime.now(timezone.utc), price=10
    )
    await conn.run_sync(_load_backfill())
    stored = (
        await conn.execute(
            text("SELECT l.external_id FROM deals d JOIN product_listings l ON l.id = d.listing_id WHERE d.id = :d"),
            {"d": deal_id},
        )
    ).scalar_one()
    assert stored == long_id.upper()
