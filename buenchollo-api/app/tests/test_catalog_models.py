"""Modelos del catálogo permanente (products / product_listings) y columnas
nuevas de `deals` y `scheduled_task_run_items`."""
import subprocess
import sys


def test_catalogo_resuelve_mappers_en_proceso_aislado():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.modules.deals.domain.models import Deal; "
                "from app.modules.catalog.domain.models import Product, ProductListing; "
                "from sqlalchemy import inspect; "
                "inspect(Deal); inspect(Product); inspect(ProductListing)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_tablas_del_catalogo():
    from app.modules.catalog.domain.models import Product, ProductListing

    assert Product.__tablename__ == "products"
    assert ProductListing.__tablename__ == "product_listings"
    uniques = [
        tuple(c.name for c in constraint.columns)
        for constraint in ProductListing.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    ]
    assert ("store_id", "external_id") in uniques


def test_columnas_nuevas_de_deal():
    from app.modules.deals.domain.models import Deal

    columns = set(Deal.__table__.c.keys())
    assert {
        "product_id",
        "listing_id",
        "offer_end_reason",
        "offer_price",
        "last_price_check_at",
        "admin_notified_at",
        "admin_notified_price",
    } <= columns


def test_run_item_tiene_transicion():
    from app.modules.scheduled_tasks.domain.models import ScheduledTaskRunItem

    assert "transition" in ScheduledTaskRunItem.__table__.c


def test_base_registra_el_catalogo():
    from app.core.base import Base

    assert {"products", "product_listings"} <= set(Base.metadata.tables)
