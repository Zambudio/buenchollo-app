from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.products.domain.entities import ProductPreview
from app.modules.products.infrastructure.amazon_client import MAX_ITEMS_PER_REQUEST
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
        self.batch_calls: list[list[str]] = []

    def get_product_preview(self, asin: str):
        return self.products.get(asin)

    def get_product_previews(self, asins: list[str]) -> dict[str, ProductPreview | None]:
        self.batch_calls.append(list(asins))
        return {asin: self.products.get(asin) for asin in asins}


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


def test_evaluate_conserva_deal_si_precio_se_mantiene_aunque_amazon_omita_saving_basis():
    """Protección contra falsos positivos (TD-18): Si Amazon omite original_price/discount_percentage
    pero el producto sigue al precio de oferta publicado, el deal se mantiene activo."""
    deal = _deal(current_price=100.0, previous_price=150.0)
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=100.0, original_price=None, discount_percentage=None, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert result.total_checked == 1
    assert result.candidates == []


def test_evaluate_marca_no_longer_deal_si_descuento_explicito_es_cero():
    deal = _deal(current_price=100.0)
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=100.0, original_price=100.0, discount_percentage=0, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 10})

    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "no_longer_deal"


def test_evaluate_marca_no_longer_deal_si_precio_actual_iguala_o_supera_el_pvp_anterior():
    deal = _deal(current_price=100.0, previous_price=150.0)
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=150.0, original_price=None, discount_percentage=None, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 100})

    assert len(result.candidates) == 1
    assert result.candidates[0].reason == "no_longer_deal"


def test_evaluate_agrupa_varios_deals_en_una_sola_llamada_a_amazon():
    """El fix de rendimiento: evaluar N deals debe hacer 1 llamada en lote
    a Amazon (hasta MAX_ITEMS_PER_REQUEST), no N llamadas individuales —
    con cientos de candidatos, ir uno a uno agotaba el timeout del
    navegador (197 deals reales en producción tardaban minutos)."""
    deals = [_deal(id=f"deal-{i}", external_id=f"B0ASIN{i:04d}") for i in range(5)]
    verifier = FakeVerifier({
        d.external_id: ProductPreview(
            current_price=100.0, original_price=120.0, discount_percentage=17, in_stock=True,
        )
        for d in deals
    })
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate(deals, {"price_tolerance_percent": 10})

    assert verifier.batch_calls == [[d.external_id for d in deals]]
    assert result.total_checked == 5


def test_evaluate_trocea_mas_de_diez_deals_en_varios_lotes():
    deals = [_deal(id=f"deal-{i}", external_id=f"B0ASIN{i:04d}") for i in range(MAX_ITEMS_PER_REQUEST + 5)]
    verifier = FakeVerifier({})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    handler.evaluate(deals, {"price_tolerance_percent": 10})

    assert len(verifier.batch_calls) == 2
    assert len(verifier.batch_calls[0]) == MAX_ITEMS_PER_REQUEST
    assert len(verifier.batch_calls[1]) == 5


def test_evaluate_omite_un_lote_si_amazon_falla_pero_sigue_con_los_demas_lotes():
    """Un fallo transitorio de Amazon (red, rate-limit, 5xx) en un lote
    completo no debe abortar los demás lotes (finding 1, ahora a nivel de
    lote tras introducir el batching de llamadas a Amazon)."""
    primer_lote = [
        _deal(id=f"deal-fail-{i}", external_id=f"B0FAIL{i:04d}")
        for i in range(MAX_ITEMS_PER_REQUEST)
    ]
    deal_ok = _deal(id="deal-ok", external_id="B0D9WH9WLD")

    class RaisingOnFirstBatchVerifier:
        def __init__(self):
            self.calls = 0

        def get_product_previews(self, asins):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("Amazon no disponible")
            return {
                "B0D9WH9WLD": ProductPreview(
                    current_price=115.0, original_price=150.0, discount_percentage=23, in_stock=True,
                )
            }

    handler = PriceCheckHandler(RaisingOnFirstBatchVerifier(), FakeDealRepo({}))

    result = handler.evaluate(primer_lote + [deal_ok], {"price_tolerance_percent": 10})

    assert result.total_checked == MAX_ITEMS_PER_REQUEST + 1
    assert len(result.candidates) == 1
    assert result.candidates[0].deal_id == "deal-ok"
    assert result.candidates[0].reason == "price_increase"


def test_evaluate_tolerancia_negativa_cae_al_valor_por_defecto():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=105.0, original_price=150.0, discount_percentage=30, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": -50})

    # Con la tolerancia negativa tratada literalmente, el umbral sería
    # menor que el precio antiguo (falso positivo masivo). Con el fallback
    # al 10% por defecto, 105 esta dentro de tolerancia y no hay candidato.
    assert result.candidates == []


def test_evaluate_tolerancia_no_numerica_cae_al_valor_por_defecto():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=105.0, original_price=150.0, discount_percentage=30, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": "no-es-un-numero"})

    assert result.candidates == []


def test_evaluate_tolerancia_fuera_de_rango_cae_al_valor_por_defecto():
    deal = _deal()
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=115.0, original_price=150.0, discount_percentage=23, in_stock=True,
    )})
    handler = PriceCheckHandler(verifier, FakeDealRepo({}))

    result = handler.evaluate([deal], {"price_tolerance_percent": 500})

    # Con 500% tomado literalmente, 115 quedaria dentro de tolerancia (sin
    # candidato). Con el fallback al 10% por defecto, 115 > 110 sí dispara.
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
