"""Caso de uso URL → oferta del editor, con FIXTURES (repositorio y redes falsos).

Cubre: tienda no soportada, Amazon intacto, varios programas, programa
pendiente, sin credenciales, importación Awin/Tradedoubler, variantes ambiguas,
sin coincidencia (candidatos sin autoselección), solo enlace, fallo de enlace
sin fabricar URL, cuota agotada, datos caducados, deduplicación y URLs no válidas.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.modules.affiliates.application.import_offer import ImportOfferUseCase, ImportRequest
from app.modules.affiliates.domain.links import InvalidLinkError
from app.modules.affiliates.domain.models import AffiliateFeedProduct, AffiliateProgram
from app.modules.affiliates.domain.offers import url_matches
from app.modules.affiliates.infrastructure.awin_client import AwinLinkUnavailable, iter_feed_rows
from app.modules.affiliates.infrastructure.http import NetworkRateLimited

FIX = Path(__file__).parent / "fixtures" / "affiliates"
NOW = datetime(2026, 11, 8, 6, tzinfo=timezone.utc)


def _program(**kw) -> AffiliateProgram:
    base = dict(
        id=kw.pop("id", "prog-awin"),
        network="awin",
        advertiser_id="20982",
        name="PcComponentes",
        store_id="store-pcc",
        domains=["pccomponentes.com"],
        currency="EUR",
        membership_status="joined",
        enabled=True,
        supports_links=True,
        supports_import=True,
        feeds=[{"feed_id": "90001", "selected": True, "generation": 1}],
        restrictions={"image_channels": ["web", "telegram"]},
        max_data_age_hours=24,
        deeplink_verified_at=None,
        disclosure_text=None,
    )
    base.update(kw)
    return AffiliateProgram(**base)


def _feed_rows(tmp: Path) -> list[AffiliateFeedProduct]:
    import gzip

    path = tmp / "f.gz"
    path.write_bytes(gzip.compress((FIX / "awin_feed.csv").read_bytes()))
    out = []
    for row in iter_feed_rows(path, 10**7, 1000):
        out.append(AffiliateFeedProduct(program_id="prog-awin", feed_id="90001", generation=1, imported_at=NOW, **row))
    return out


class FakeRepo:
    def __init__(self, programs, rows=(), existing=None):
        self.programs, self.rows, self.existing = programs, list(rows), existing

    async def programs_for_url(self, url):
        return [p for p in self.programs if url_matches(url, p.domains)]

    async def find_feed_products(self, program, *, normalized_url=None, ean=None, merchant_product_id=None, product_key=None, limit=20):
        out = []
        for r in self.rows:
            if (
                (normalized_url and r.normalized_url == normalized_url)
                or (ean and r.ean == ean)
                or (merchant_product_id and r.merchant_product_id == merchant_product_id)
                or (product_key and r.product_key == product_key)
            ):
                out.append(r)
        return out

    async def feed_candidates(self, program, words, limit=8):
        return [r for r in self.rows if any(w.lower() in r.title.lower() for w in words)][:limit]

    async def deal_by_external_id(self, external_id):
        return self.existing if self.existing and self.existing.external_id == external_id else None


class FakeAwin:
    api_configured = True
    feeds_configured = True
    secrets = ("SECRET-TOKEN-XYZ",)

    def __init__(self, fail=None):
        self.fail, self.calls = fail, []

    def generate_link(self, advertiser_id, destination, clickref=None):
        self.calls.append((advertiser_id, destination))
        if self.fail:
            raise self.fail
        return f"https://www.awin1.com/cread.php?awinmid={advertiser_id}&awinaffid=3148595&ued=fixture"


class FakeTD:
    configured = True
    secrets = ()

    def __init__(self, products=None, site_id="123"):
        self.products = products or []
        self.calls = []
        self.site_id = site_id

    def search_products(self, feed_id, *, ean=None, sp_id=None, query=None, page_size=10):
        self.calls.append((feed_id, ean, sp_id, query))
        return self.products

    def deeplink(self, program_id, destination):
        return f"https://clk.tradedoubler.com/click?p={program_id}&a={self.site_id}&url=fixture"


def run(use_case, **req):
    return asyncio.run(use_case.execute(ImportRequest(**req), now=NOW))


def test_url_no_valida_o_interna_se_rechaza():
    uc = ImportOfferUseCase(FakeRepo([_program()]), FakeAwin(), FakeTD())
    for bad in ("file:///etc/passwd", "http://127.0.0.1/admin", "https://pccomponentes.com@evil.example/x", "hola"):
        with pytest.raises(InvalidLinkError):
            run(uc, url=bad)


def test_amazon_sigue_su_flujo():
    uc = ImportOfferUseCase(FakeRepo([_program()]), FakeAwin(), FakeTD())
    assert run(uc, url="https://www.amazon.es/dp/B08TEST123").status == "use_amazon_flow"


def test_tienda_no_configurada():
    uc = ImportOfferUseCase(FakeRepo([_program()]), FakeAwin(), FakeTD())
    assert run(uc, url="https://www.otra-tienda.es/x").status == "unsupported_store"


def test_miravia_pide_elegir_programa():
    progs = [
        _program(id="m1", advertiser_id="37166", name="Miravia RRSS", domains=["miravia.es"]),
        _program(id="m2", advertiser_id="37168", name="Miravia otros", domains=["miravia.es"]),
    ]
    awin = FakeAwin()
    result = run(ImportOfferUseCase(FakeRepo(progs), awin, FakeTD()), url="https://www.miravia.es/p/x")
    assert result.status == "program_choice_required"
    assert {o["advertiser_id"] for o in result.program_options} == {"37166", "37168"}
    assert awin.calls == []


def test_programa_pendiente_no_aparece_aprobado_ni_genera_enlace():
    awin = FakeAwin()
    result = run(
        ImportOfferUseCase(FakeRepo([_program(membership_status="pending")]), awin, FakeTD()),
        url="https://www.pccomponentes.com/fixture-monitor-27-qhd",
    )
    assert result.status == "pending_approval"
    assert result.program["membership_status"] == "pending"
    assert result.link.get("affiliate_url") is None and awin.calls == []


def test_sin_credenciales():
    awin = FakeAwin()
    awin.api_configured = False
    result = run(ImportOfferUseCase(FakeRepo([_program()]), awin, FakeTD()), url="https://www.pccomponentes.com/x")
    assert result.status == "not_configured"


def test_awin_importa_producto_exacto(tmp_path):
    uc = ImportOfferUseCase(FakeRepo([_program()], _feed_rows(tmp_path)), FakeAwin(), FakeTD())
    result = run(uc, url="https://www.pccomponentes.com/fixture-monitor-27-qhd?utm_source=tg")
    assert result.status == "imported" and result.stage == "product_imported"
    offer = result.offer
    assert offer["title"] == "FIXTURE Monitor 27 QHD"
    assert offer["current_price"] == "199.90"
    assert offer["affiliate_url"].startswith("https://www.awin1.com/")
    assert offer["link_source"] == "awin_linkbuilder"
    # El PVP se muestra aparte y NO se usa como precio anterior.
    assert offer["rrp_price"] == "279.00" and offer["reference_price"] is None and offer["reference_type"] == "none"
    assert "previous_price_evidence" in result.missing
    assert offer["shipping_info"] == "Envío: 4,99 € (según la red)"
    assert offer["external_id"] == "aw:20982:F-1001"
    assert result.provenance["freshness"] == "fresh"
    assert result.provenance["provider_updated_at"].startswith("2026-11-08T02:00")


def test_variantes_ambiguas_no_se_autoseleccionan(tmp_path):
    uc = ImportOfferUseCase(FakeRepo([_program()], _feed_rows(tmp_path)), FakeAwin(), FakeTD())
    result = run(uc, url="https://www.pccomponentes.com/fixture-ssd-nvme?color=negro")
    assert result.status == "ambiguous"
    assert result.offer is not None and result.offer.get("title") is None  # solo enlace, sin ficha elegida
    assert {c["condition"] for c in result.candidates} == {"new", "refurbished"}
    chosen = run(uc, url="https://www.pccomponentes.com/fixture-ssd-nvme?color=negro", product_key="F-2002")
    assert chosen.status == "imported" and chosen.offer["condition"] == "refurbished"


def test_campos_ausentes_no_se_inventan(tmp_path):
    uc = ImportOfferUseCase(FakeRepo([_program()], _feed_rows(tmp_path)), FakeAwin(), FakeTD())
    result = run(uc, url="https://www.pccomponentes.com/fixture-ssd-nvme", product_key="F-2001")
    o = result.offer
    assert o["shipping_info"] is None  # no "gratis"
    assert o["rrp_price"] is None and o["reference_price"] is None
    assert "shipping_info" in result.missing


def test_sin_coincidencia_propone_candidatos_sin_elegir(tmp_path):
    uc = ImportOfferUseCase(FakeRepo([_program()], _feed_rows(tmp_path)), FakeAwin(), FakeTD())
    result = run(uc, url="https://www.pccomponentes.com/fixture-monitor-otro")
    assert result.status == "no_match"
    assert result.stage == "link_generated"  # el enlace sí se genera
    assert [c["product_key"] for c in result.candidates] == ["F-1001"]
    assert result.offer.get("title") is None


def test_catalogo_no_disponible_pero_enlace_si(tmp_path):
    uc = ImportOfferUseCase(FakeRepo([_program(feeds=[])]), FakeAwin(), FakeTD())
    result = run(uc, url="https://www.pccomponentes.com/x")
    assert result.status == "catalog_unavailable"
    assert result.link["status"] == "generated"


def test_solo_enlace():
    awin = FakeAwin()
    result = run(ImportOfferUseCase(FakeRepo([_program()]), awin, FakeTD()), url="https://www.pccomponentes.com/x?color=rojo", link_only=True)
    assert result.status == "link_only" and result.stage == "link_generated"
    assert awin.calls == [("20982", "https://www.pccomponentes.com/x?color=rojo")]
    assert result.offer["data_source"] == "link_only"


def test_fallo_de_enlace_no_fabrica_url():
    awin = FakeAwin(fail=AwinLinkUnavailable("Awin no ha generado el enlace"))
    result = run(ImportOfferUseCase(FakeRepo([_program()]), awin, FakeTD()), url="https://www.pccomponentes.com/x", link_only=True)
    assert result.link["status"] == "error"
    assert result.offer is None and result.stage == "none"


def test_cuota_agotada_estado_util():
    awin = FakeAwin(fail=NetworkRateLimited("Límite de llamadas por minuto"))
    result = run(ImportOfferUseCase(FakeRepo([_program()]), awin, FakeTD()), url="https://www.pccomponentes.com/x", link_only=True)
    assert result.status == "rate_limited"


def test_datos_caducados(tmp_path):
    rows = _feed_rows(tmp_path)
    for r in rows:
        r.provider_updated_at = NOW - timedelta(days=4)
    uc = ImportOfferUseCase(FakeRepo([_program()], rows), FakeAwin(), FakeTD())
    result = run(uc, url="https://www.pccomponentes.com/fixture-monitor-27-qhd")
    assert result.status == "stale_data" and result.provenance["freshness"] == "stale"


def test_reimportar_detecta_chollo_existente(tmp_path):
    existing = SimpleNamespace(id="d1", slug="monitor", title="Monitor", status="draft", external_id="aw:20982:F-1001")
    uc = ImportOfferUseCase(FakeRepo([_program()], _feed_rows(tmp_path), existing), FakeAwin(), FakeTD())
    result = run(uc, url="https://www.pccomponentes.com/fixture-monitor-27-qhd")
    assert result.existing_deal == {"id": "d1", "slug": "monitor", "title": "Monitor", "status": "draft"}


# ── Tradedoubler ─────────────────────────────────────────────────────────────

def _td_program(**kw):
    return _program(
        id="prog-td",
        network="tradedoubler",
        advertiser_id="270504",
        name="MediaMarkt ES",
        domains=["mediamarkt.es"],
        feeds=[{"feed_id": "55501", "selected": True}],
        restrictions={"image_channels": []},
        **kw,
    )


def _td_products():
    return json.loads((FIX / "td_products.json").read_text(encoding="utf-8"))["products"]


def test_tradedoubler_importa_por_source_url_y_usa_productUrl():
    td = FakeTD(_td_products())
    uc = ImportOfferUseCase(FakeRepo([_td_program()]), FakeAwin(), td)
    result = run(uc, url="https://www.mediamarkt.es/es/product/_fixture-portatil-15-77.html")
    assert result.status == "imported"
    o = result.offer
    assert o["affiliate_url"].startswith("https://pdt.tradedoubler.com/") and o["link_source"] == "tradedoubler_product"
    assert o["current_price"] == "699.00"
    # Referencia del historial de precios (mínimo 30 días) con evidencia.
    assert o["reference_price"] == "849.00" and o["reference_type"] == "provider_price_history_30d"
    assert "Tradedoubler" in o["reference_evidence"]
    assert o["shipping_info"] == "Envío: 0,00 € (según la red)"
    assert td.calls[0][3] == "fixture portatil"  # búsqueda por palabras, nunca por URL


def test_tradedoubler_sin_coincidencia_exacta_no_elige():
    td = FakeTD(_td_products())
    uc = ImportOfferUseCase(FakeRepo([_td_program()]), FakeAwin(), td)
    result = run(uc, url="https://www.mediamarkt.es/es/product/_fixture-portatil-15-99.html")
    assert result.status == "no_match"
    assert len(result.candidates) == 2
    # Sin ficha y sin deeplink verificado: no se fabrica enlace.
    assert result.link["status"] == "unavailable" and result.offer is None


def test_tradedoubler_deeplink_solo_si_verificado():
    td = FakeTD([])
    prog = _td_program(deeplink_verified_at=NOW)
    result = run(ImportOfferUseCase(FakeRepo([prog]), FakeAwin(), td), url="https://www.mediamarkt.es/es/x.html", link_only=True)
    assert result.link["source"] == "tradedoubler_deeplink"
    assert result.status == "link_only"


def test_tradedoubler_por_ean():
    td = FakeTD(_td_products()[:1])
    uc = ImportOfferUseCase(FakeRepo([_td_program()]), FakeAwin(), td)
    result = run(uc, url="https://www.mediamarkt.es/es/product/otra-url.html", ean="8400000000031")
    assert result.status == "imported"
    assert td.calls[0][1] == "8400000000031" and td.calls[0][3] is None
