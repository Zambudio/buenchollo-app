from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.products.domain.entities import ProductPreview
from app.modules.scheduled_tasks.application.price_check_handler import PriceCheckHandler


def _deal(**overrides):
    base = dict(
        id="deal-1",
        title="Producto X",
        slug="producto-x",
        image_url="https://img/x.jpg",
        description="desc",
        store_id="store-1",
        store=SimpleNamespace(name="Amazon"),
        category_id="cat-1",
        subcategory_id=None,
        external_id="B0D9WH9WLD",
        affiliate_url="https://amazon.es/dp/B0D9WH9WLD",
        source_url=None,
        current_price=100.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class FakeVerifier:
    def __init__(self, products: dict[str, ProductPreview | None]):
        self.products = products

    def get_product_preview(self, asin: str):
        return self.products.get(asin)


class FakeDealRepo:
    def __init__(self, deals_by_id: dict[str, object]):
        self.deals_by_id = deals_by_id
        self.deleted: list[str] = []
        self.get_by_id = AsyncMock(side_effect=lambda deal_id: self.deals_by_id.get(deal_id))

    async def delete(self, deal):
        self.deleted.append(deal.id)


def test_evaluate_marca_price_increase_fuera_de_tolerancia():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=115.0, original_price=150.0, discount_percentage=23, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert result.total_checked == 1
    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "price_increase"
    assert result.candidates[0].new_price == 115.0


def test_evaluate_no_marca_price_increase_dentro_de_tolerancia():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=108.0, original_price=150.0, discount_percentage=28, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert result.total_checked == 1
    assert result.candidates == []


def test_evaluate_marca_out_of_stock():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=90.0, original_price=150.0, discount_percentage=40, in_stock=False,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "out_of_stock"
    assert result.candidates[0].new_price is None


def test_evaluate_marca_no_longer_deal_si_amazon_ya_no_reporta_descuento():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=100.0, original_price=None, discount_percentage=None, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "no_longer_deal"


def test_evaluate_ignora_asin_no_encontrado_en_amazon():
    deal = _deal()
    verifier = FakeVerifier({})  # Amazon no devuelve nada para este ASIN
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert result.total_checked == 1
    assert result.candidates == []


def test_evaluate_usa_tolerancia_por_defecto_diez_por_ciento_si_falta_config():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=111.0, original_price=150.0, discount_percentage=26, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {})

    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "price_increase"


@pytest.mark.asyncio
async def test_execute_borra_los_deals_encontrados_y_omite_los_ya_borrados():
    from app.modules.scheduled_tasks.application.task_handler import Candidate
    from decimal import Decimal

    deal1 = _deal(id="deal-1")
    repo = FakeDealRepo({"deal-1": deal1})  # deal-2 ya no existe (borrado por otra vía)
    handler = PriceCheckHandler(FakeVerifier({}), repo)
    candidates = [
        Candidate(
            deal_id="deal-1", title="X", slug="x", image_url=None, description=None,
            store_id=None, store_name=None, category_id=None, subcategory_id=None,
            external_id="B0D9WH9WLD", affiliate_url="https://a", source_url=None,
            old_price=Decimal("100.00"), new_price=Decimal("115.00"), reason="price_increase",
        ),
        Candidate(
            deal_id="deal-2", title="Y", slug="y", image_url=None, description=None,
            store_id=None, store_name=None, category_id=None, subcategory_id=None,
            external_id="B0OTHER0001", affiliate_url="https://b", source_url=None,
            old_price=Decimal("50.00"), new_price=None, reason="out_of_stock",
        ),
    ]

    deleted = await handler.execute(candidates)

    assert [c.deal_id for c in deleted] == ["deal-1"]
    assert repo.deleted == ["deal-1"]
