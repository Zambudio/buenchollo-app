"""PriceCheckHandler: revisión diaria del catálogo. Ya no borra chollos: actualiza
precio/disponibilidad, termina o reactiva ofertas y purga tiendas que llevan
`purge_after_days` sin disponibilidad confirmada."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.catalog.domain.offer_rules import Observation
from app.modules.products.domain.entities import ProductPreview
from app.modules.products.infrastructure.amazon_client import MAX_ITEMS_PER_REQUEST
from app.modules.scheduled_tasks.application.price_check_handler import ListingCheck, PriceCheckHandler

NOW = datetime(2026, 11, 5, 4, 0, tzinfo=timezone.utc)
CONFIG = {"price_tolerance_percent": 10, "min_discount_percent": 5, "purge_after_days": 30}


def _listing(**overrides):
    base = dict(
        id="listing-1", product_id="product-1", external_id="B0D9WH9WLD",
        current_price=Decimal("100"), reference_price=None, discount_percentage=None,
        in_stock=None, availability="unknown", unavailable_since=None, last_checked_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _deal(**overrides):
    base = dict(
        id="deal-1", title="Producto X", slug="producto-x", image_url="https://img/x.jpg",
        description="desc", short_description=None, store_id="store-1",
        store=SimpleNamespace(name="Amazon"), category_id="cat-1", subcategory_id=None,
        external_id="B0D9WH9WLD", affiliate_url="https://amazon.es/dp/B0D9WH9WLD", source_url=None,
        current_price=Decimal("100"), previous_price=None, discount_percentage=None,
        savings_amount=None, offer_price=Decimal("100"), status="active", offer_end_reason=None,
        published_at=NOW - timedelta(days=10), last_price_check_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _obs(price="100", *, found=True, in_stock=True, reference=None, discount=None):
    return Observation(
        found=found, in_stock=in_stock,
        price=Decimal(price) if price is not None else None,
        reference_price=Decimal(reference) if reference is not None else None,
        discount_percentage=discount,
    )


class FakeVerifier:
    def __init__(self, products=None, fail=False, fail_times=0):
        self.products = products or {}
        self.fail = fail
        self.fail_times = fail_times
        self.batch_calls: list[list[str]] = []

    def get_product_previews(self, asins):
        self.batch_calls.append(list(asins))
        if self.fail or self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("Amazon caído")
        return {asin: self.products.get(asin) for asin in asins}


class FakeCatalogRepo:
    def __init__(self, pairs=None, deleted_ids=None):
        self.pairs = pairs or []
        self.purged: list[str] = []
        self.deleted_ids = deleted_ids or []

    async def get_checkable(self):
        return self.pairs

    async def purge_listing(self, listing):
        self.purged.append(listing.id)
        return list(self.deleted_ids)


def _handler(verifier=None, repo=None, sleeps=None):
    pauses = sleeps if sleeps is not None else []
    return PriceCheckHandler(verifier or FakeVerifier(), repo or FakeCatalogRepo(), sleep=pauses.append)


# --- fetch / collect ---


def test_fetch_consulta_en_lotes_de_10():
    pairs = [(_listing(id=f"l{i}", external_id=f"B0000000{i:02d}"), None) for i in range(23)]
    verifier = FakeVerifier()
    checks = _handler(verifier).fetch(pairs)
    assert [len(b) for b in verifier.batch_calls] == [MAX_ITEMS_PER_REQUEST, MAX_ITEMS_PER_REQUEST, 3]
    assert len(checks) == 23


def test_fetch_espacia_las_peticiones_a_amazon():
    pairs = [(_listing(id=f"l{i}", external_id=f"B0000000{i:02d}"), None) for i in range(21)]
    sleeps: list[float] = []
    _handler(FakeVerifier(), sleeps=sleeps).fetch(pairs)
    # 3 peticiones → 2 pausas de al menos ~1 s (la Creators API admite 1 TPS)
    assert len(sleeps) == 2 and all(pause >= 1.0 for pause in sleeps)


def test_fetch_reintenta_una_vez_un_lote_fallido():
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(current_price=10, in_stock=True)}, fail_times=1)
    checks = _handler(verifier).fetch([(_listing(), _deal())])
    assert len(verifier.batch_calls) == 2
    assert checks[0].observation.found is True


def test_fetch_excluye_ids_que_no_son_asin_validos():
    """Un id inválido hace que Amazon rechace el lote entero con un 400."""
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(current_price=10, in_stock=True)})
    pairs = [(_listing(id="bad", external_id="B0RUNDETAIL1"), None), (_listing(), _deal())]
    checks = {c.listing.id: c for c in _handler(verifier).fetch(pairs)}
    assert verifier.batch_calls == [["B0D9WH9WLD"]]
    assert checks["bad"].observation is None
    assert checks["listing-1"].observation.found is True


def test_fetch_lote_fallido_deja_observacion_none():
    checks = _handler(FakeVerifier(fail=True)).fetch([(_listing(), _deal())])
    assert checks[0].observation is None


def test_fetch_ausente_en_respuesta_es_not_found():
    checks = _handler(FakeVerifier({})).fetch([(_listing(), _deal())])
    assert checks[0].observation == Observation(False, False, None, None, None)


def test_fetch_mapea_el_producto():
    verifier = FakeVerifier({"B0D9WH9WLD": ProductPreview(
        current_price=89.991, original_price=120.0, discount_percentage=25, in_stock=True,
    )})
    obs = _handler(verifier).fetch([(_listing(), _deal())])[0].observation
    assert obs == Observation(True, True, Decimal("89.99"), Decimal("120.00"), 25)


@pytest.mark.asyncio
async def test_collect_carga_del_catalogo_y_consulta():
    repo = FakeCatalogRepo([(_listing(), _deal())])
    checks = await _handler(FakeVerifier({}), repo).collect()
    assert len(checks) == 1 and checks[0].observation.found is False


# --- evaluate (vista previa, sin escribir) ---


def test_evaluate_no_escribe_y_lista_transiciones():
    deal = _deal()
    result = _handler().evaluate([ListingCheck(_listing(), deal, _obs("120"))], CONFIG, NOW)
    assert result.total_checked == 1
    [candidate] = result.candidates
    assert (candidate.transition, candidate.reason) == ("offer_ended", "price_increase")
    assert candidate.new_price == Decimal("120")
    assert deal.status == "active"


def test_evaluate_reactivacion():
    deal = _deal(status="expired", offer_end_reason="price_increase", offer_price=Decimal("80"))
    result = _handler().evaluate([ListingCheck(_listing(), deal, _obs("79"))], CONFIG, NOW)
    assert [(c.transition, c.reason) for c in result.candidates] == [("reactivated", "deal_again")]


# --- apply ---


@pytest.mark.asyncio
async def test_lote_fallido_no_toca_nada():
    listing, deal = _listing(availability="available"), _deal()
    applied = await _handler().apply([ListingCheck(listing, deal, None)], CONFIG, NOW)
    assert applied == []
    assert deal.status == "active" and deal.current_price == Decimal("100")
    assert listing.availability == "available" and listing.last_checked_at is None
    assert deal.last_price_check_at is None


@pytest.mark.asyncio
async def test_actualiza_precio_sin_transicion():
    listing, deal = _listing(), _deal()
    applied = await _handler().apply(
        [ListingCheck(listing, deal, _obs("95", reference="130", discount=27))], CONFIG, NOW
    )
    assert applied == []
    assert listing.current_price == Decimal("95") and listing.reference_price == Decimal("130")
    assert listing.availability == "available" and listing.last_checked_at == NOW
    assert deal.current_price == Decimal("95")
    assert deal.previous_price == Decimal("130")
    assert deal.discount_percentage == 27
    assert deal.savings_amount == Decimal("35")
    assert deal.last_price_check_at == NOW
    assert deal.offer_price == Decimal("100")


@pytest.mark.asyncio
async def test_ausente_marca_not_found_y_fija_unavailable_since():
    listing, deal = _listing(availability="available"), _deal()
    applied = await _handler().apply(
        [ListingCheck(listing, deal, _obs(None, found=False, in_stock=False))], CONFIG, NOW
    )
    assert listing.availability == "not_found"
    assert listing.unavailable_since == NOW
    assert deal.status == "expired" and deal.offer_end_reason == "not_found"
    assert deal.current_price == Decimal("100")
    assert [c.transition for c in applied] == ["offer_ended"]


@pytest.mark.asyncio
async def test_sigue_no_disponible_conserva_unavailable_since():
    since = NOW - timedelta(days=3)
    listing = _listing(availability="unavailable", unavailable_since=since)
    deal = _deal(status="expired", offer_end_reason="out_of_stock")
    await _handler().apply([ListingCheck(listing, deal, _obs(in_stock=False))], CONFIG, NOW)
    assert listing.unavailable_since == since


@pytest.mark.asyncio
async def test_vuelve_disponible_limpia_unavailable_since():
    listing = _listing(availability="unavailable", unavailable_since=NOW - timedelta(days=3))
    deal = _deal(status="expired", offer_end_reason="out_of_stock")
    await _handler().apply([ListingCheck(listing, deal, _obs("100"))], CONFIG, NOW)
    assert listing.availability == "available" and listing.unavailable_since is None


@pytest.mark.asyncio
async def test_end_no_borra_deal():
    deal = _deal()
    applied = await _handler().apply([ListingCheck(_listing(), deal, _obs(discount=0))], CONFIG, NOW)
    assert deal.status == "expired" and deal.offer_end_reason == "no_longer_deal"
    assert applied[0].deal_id == "deal-1" and applied[0].old_price == Decimal("100")


@pytest.mark.asyncio
async def test_reactivate_fija_offer_price_y_published_at():
    deal = _deal(status="expired", offer_end_reason="out_of_stock", offer_price=Decimal("80"))
    applied = await _handler().apply([ListingCheck(_listing(), deal, _obs("78"))], CONFIG, NOW)
    assert deal.status == "active" and deal.offer_end_reason is None
    assert deal.published_at == NOW and deal.offer_price == Decimal("78")
    assert [(c.transition, c.new_price) for c in applied] == [("reactivated", Decimal("78"))]


@pytest.mark.asyncio
async def test_listing_sin_deal_principal_solo_actualiza_listing():
    listing = _listing()
    applied = await _handler().apply([ListingCheck(listing, None, _obs("70"))], CONFIG, NOW)
    assert applied == [] and listing.current_price == Decimal("70")


@pytest.mark.asyncio
@pytest.mark.parametrize("days, purged", [(29, False), (30, True)])
async def test_purga_tras_purge_after_days(days, purged):
    listing = _listing(availability="not_found", unavailable_since=NOW - timedelta(days=days))
    deal = _deal(status="expired", offer_end_reason="not_found")
    repo = FakeCatalogRepo(deleted_ids=["deal-1"])
    applied = await _handler(repo=repo).apply(
        [ListingCheck(listing, deal, _obs(None, found=False, in_stock=False))], CONFIG, NOW
    )
    assert (repo.purged == ["listing-1"]) is purged
    if purged:
        assert [(c.transition, c.reason) for c in applied] == [("purged", "product_purged")]


@pytest.mark.asyncio
async def test_purga_de_tienda_con_otras_tiendas_no_borra_deal():
    listing = _listing(availability="unavailable", unavailable_since=NOW - timedelta(days=40))
    deal = _deal(status="expired", offer_end_reason="out_of_stock")
    repo = FakeCatalogRepo(deleted_ids=[])
    applied = await _handler(repo=repo).apply(
        [ListingCheck(listing, deal, _obs(in_stock=False))], CONFIG, NOW
    )
    assert [(c.transition, c.reason) for c in applied] == [("purged", "listing_purged")]


@pytest.mark.asyncio
async def test_no_purga_si_la_consulta_de_hoy_fallo():
    listing = _listing(availability="not_found", unavailable_since=NOW - timedelta(days=90))
    repo = FakeCatalogRepo(deleted_ids=["deal-1"])
    await _handler(repo=repo).apply([ListingCheck(listing, _deal(), None)], CONFIG, NOW)
    assert repo.purged == []


@pytest.mark.parametrize("value", [0, "x", 1000])
def test_purge_after_days_invalido_usa_30(value):
    listing = _listing(availability="not_found", unavailable_since=NOW - timedelta(days=30))
    deal = _deal(status="expired", offer_end_reason="not_found")
    check = ListingCheck(listing, deal, _obs(None, found=False, in_stock=False))
    result = _handler().evaluate([check], {"purge_after_days": value}, NOW)
    assert [c.transition for c in result.candidates] == ["purged"]


@pytest.mark.asyncio
async def test_listing_sin_deal_se_purga_sin_item_de_registro():
    listing = _listing(availability="not_found", unavailable_since=NOW - timedelta(days=31))
    repo = FakeCatalogRepo(deleted_ids=["draft-1"])
    applied = await _handler(repo=repo).apply(
        [ListingCheck(listing, None, _obs(None, found=False, in_stock=False))], CONFIG, NOW
    )
    assert repo.purged == ["listing-1"] and applied == []
