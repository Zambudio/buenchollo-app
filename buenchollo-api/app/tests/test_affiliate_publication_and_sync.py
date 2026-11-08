"""Guarda de publicación, sincronización de feeds y endpoints admin (FIXTURES)."""

import asyncio
import gzip
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import require_admin
from app.main import app
from app.modules.affiliates.application.feed_sync import AwinFeedSync, merge_feed_metadata
from app.modules.affiliates.application.programs import PublicationBlocked, PublicationGuard
from app.modules.affiliates.domain.models import AffiliateProgram
from app.modules.affiliates.infrastructure.awin_client import iter_feed_rows, parse_feed_list
from app.modules.affiliates.infrastructure.http import NetworkError
from app.modules.deals.application.deal_service import DealService

FIX = Path(__file__).parent / "fixtures" / "affiliates"
NOW = datetime.now(timezone.utc)


def _program(**kw):
    base = dict(
        id="prog-awin",
        network="awin",
        advertiser_id="20982",
        name="PcComponentes",
        domains=["pccomponentes.com"],
        membership_status="joined",
        enabled=True,
        feeds=[],
        restrictions={"image_channels": ["web", "telegram"]},
        max_data_age_hours=24,
    )
    base.update(kw)
    return AffiliateProgram(**base)


class ProgRepo:
    def __init__(self, program):
        self.program = program

    async def get_program(self, program_id):
        return self.program if self.program and self.program.id == program_id else None


def _deal_data(**kw):
    base = dict(
        status="active",
        title="FIXTURE Monitor",
        affiliate_url="https://www.awin1.com/cread.php?awinmid=20982&awinaffid=3148595&ued=x",
        current_price=199.90,
        previous_price=249.00,
        price_reference_type="store_strikethrough_verified",
        price_reference_evidence="Tachado en tienda 08/11 10:00",
        shipping_info="Envío: 4,99 €",
        short_description="Monitor QHD.",
        category_id="cat",
        image_url="https://img.example.com/x.jpg",
        affiliate_program_id="prog-awin",
        data_source="awin_feed",
        data_provider_updated_at=NOW - timedelta(hours=1),
        price_verified_at=None,
    )
    base.update(kw)
    return base


# ── Guarda ───────────────────────────────────────────────────────────────────

def test_borrador_siempre_se_guarda():
    guard = PublicationGuard(ProgRepo(_program()))
    asyncio.run(guard.ensure_publishable(_deal_data(status="draft", previous_price=None)))


def test_activo_sin_evidencia_de_precio_anterior_se_bloquea():
    guard = PublicationGuard(ProgRepo(_program()))
    with pytest.raises(PublicationBlocked) as exc:
        asyncio.run(guard.ensure_publishable(_deal_data(price_reference_type="rrp")))
    assert "reference_not_proof" in exc.value.blockers
    assert exc.value.http_status == 400


def test_chollo_amazon_no_se_ve_afectado():
    guard = PublicationGuard(ProgRepo(None))
    amazon = {"status": "active", "affiliate_url": "https://www.amazon.es/dp/B08TEST123?tag=x", "data_source": None}
    asyncio.run(guard.ensure_publishable(amazon))


def test_programa_pendiente_bloquea_publicar():
    guard = PublicationGuard(ProgRepo(_program(membership_status="pending")))
    with pytest.raises(PublicationBlocked):
        asyncio.run(guard.ensure_publishable(_deal_data()))


def test_completo_se_publica():
    asyncio.run(PublicationGuard(ProgRepo(_program())).ensure_publishable(_deal_data()))


def test_deal_service_bloquea_alta_activa_y_permite_borrador():
    repo = MagicMock()
    repo.user_has_profile = AsyncMock(return_value=True)
    repo.find_by_external_id = AsyncMock(return_value=None)
    created = SimpleNamespace(id="d1", status="draft")
    repo.create = AsyncMock(return_value=created)
    repo.get_by_id = AsyncMock(return_value=created)
    service = DealService(repo, publication_guard=PublicationGuard(ProgRepo(_program())))

    with pytest.raises(PublicationBlocked):
        asyncio.run(service.create_deal(_deal_data(previous_price=None), "user"))
    repo.create.assert_not_awaited()

    asyncio.run(service.create_deal(_deal_data(status="draft", previous_price=None), "user"))
    repo.create.assert_awaited_once()


def test_deal_service_bloquea_activar_un_borrador_incompleto():
    deal = SimpleNamespace(**_deal_data(status="draft", shipping_info=None), id="d1", external_id=None)
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=deal)
    repo.update = AsyncMock()
    service = DealService(repo, publication_guard=PublicationGuard(ProgRepo(_program())))
    with pytest.raises(PublicationBlocked) as exc:
        asyncio.run(service.update_deal("d1", {"status": "active"}))
    assert exc.value.blockers == ["shipping_info"]
    repo.update.assert_not_awaited()


# ── Sincronización de feeds ─────────────────────────────────────────────────

def test_merge_feed_metadata_conserva_seleccion_y_no_guarda_urls():
    program = _program(feeds=[{"feed_id": "90001", "selected": True, "generation": 5}])
    listed = parse_feed_list((FIX / "awin_feed_list.csv").read_text(encoding="utf-8"))
    feeds = merge_feed_metadata(program, listed)
    assert feeds == [
        {
            "feed_id": "90001",
            "selected": True,
            "generation": 5,
            "name": "FIXTURE Feed A",
            "language": "es",
            "format": "Awin",
            "products": "4",
            "last_imported": "2026-11-08 03:00:00",
            "membership_status": "active",
            "available": True,
        }
    ]
    assert "url" not in str(feeds).lower().replace("available", "")


class SyncRepo:
    def __init__(self, program):
        self.program = program
        self.rows: list[dict] = [{"feed_id": "90001", "generation": 5, "product_key": "OLD"}]
        self.session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

    async def list_programs(self):
        return [self.program]

    async def get_program(self, pid):
        return self.program

    async def save(self, program):
        self.program = program
        return program

    async def insert_feed_rows(self, rows):
        self.rows.extend(rows)

    async def delete_generation(self, program_id, feed_id, *, keep=None, only=None):
        self.rows = [
            r
            for r in self.rows
            if not (
                r["feed_id"] == feed_id
                and ((keep is not None and r["generation"] != keep) or (only is not None and r["generation"] == only))
            )
        ]


class SyncClient:
    feeds_configured = True
    secrets = ("FIXTUREKEY123456",)

    def __init__(self, fail_after_rows=False):
        self.fail_after_rows = fail_after_rows

    def feed_list(self):
        return parse_feed_list((FIX / "awin_feed_list.csv").read_text(encoding="utf-8"))

    def download_feed(self, url, dest: Path):
        dest.write_bytes(gzip.compress((FIX / "awin_feed.csv").read_bytes()))
        return 1

    def iter_feed_file(self, path):
        for i, row in enumerate(iter_feed_rows(path, 10**7, 1000)):
            if self.fail_after_rows and i == 2:
                raise NetworkError("fallo a mitad https://productdata.awin.com/datafeed/download/apikey/FIXTUREKEY123456/x")
            yield row


def test_sync_ok_sustituye_generacion():
    repo = SyncRepo(_program(feeds=[{"feed_id": "90001", "selected": True, "generation": 5, "last_synced_remote": "old"}]))
    report = asyncio.run(AwinFeedSync(repo, SyncClient()).run())
    assert report[0]["status"] == "ok" and report[0]["rows"] == 4
    assert {r["product_key"] for r in repo.rows} == {"F-1001", "F-2001", "F-2002", "F-3001"}
    feed = repo.program.feeds[0]
    assert feed["generation"] != 5 and feed["last_status"] == "ok"
    assert feed["last_synced_remote"] == "2026-11-08 03:00:00"


def test_sync_sin_cambios_no_descarga():
    program = _program(
        feeds=[{"feed_id": "90001", "selected": True, "generation": 5, "last_synced_remote": "2026-11-08 03:00:00"}]
    )
    client = SyncClient()
    client.download_feed = MagicMock(side_effect=AssertionError("no debe descargar"))
    report = asyncio.run(AwinFeedSync(SyncRepo(program), client).run())
    assert report[0]["status"] == "unchanged"


def test_sync_fallida_conserva_el_catalogo_anterior_y_redacta():
    repo = SyncRepo(_program(feeds=[{"feed_id": "90001", "selected": True, "generation": 5}]))
    report = asyncio.run(AwinFeedSync(repo, SyncClient(fail_after_rows=True)).run())
    assert report[0]["status"] == "error"
    assert "FIXTUREKEY123456" not in report[0]["message"]
    assert [r["product_key"] for r in repo.rows] == ["OLD"]
    feed = repo.program.feeds[0]
    assert feed["generation"] == 5 and feed["last_status"] == "error"


# ── Endpoints ────────────────────────────────────────────────────────────────

SECRET = "SUPERSECRET-awin-token-123"


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _as_admin():
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id="dbe6e006-4f3e-4be8-8351-7e264ed3acb6")

    async def _db():
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock())
        session.get = AsyncMock(return_value=None)
        yield session

    app.dependency_overrides[get_db] = _db
    settings = Settings(awin_publisher_id="3148595", awin_access_token=SECRET, awin_feed_api_key=SECRET + "f",
                        tradedoubler_products_token="", tradedoubler_site_id="")
    app.dependency_overrides[get_settings] = lambda: settings


def test_endpoints_exigen_admin(client):
    assert client.get("/v1/affiliates/status").status_code in (401, 403)
    assert client.post("/v1/affiliates/import", json={"url": "https://www.pccomponentes.com/x"}).status_code in (401, 403)


def test_status_no_expone_secretos(client):
    _as_admin()
    r = client.get("/v1/affiliates/status")
    assert r.status_code == 200
    assert r.json() == {
        "awin_publisher_api": True,
        "awin_feeds": True,
        "tradedoubler_products": False,
        "tradedoubler_site_id": False,
    }
    assert SECRET not in r.text


def test_import_rechaza_url_interna(client):
    _as_admin()
    r = client.post("/v1/affiliates/import", json={"url": "http://192.168.1.10/admin"})
    assert r.status_code == 400


def test_readiness_amazon_no_aplica(client):
    _as_admin()
    r = client.post("/v1/affiliates/readiness", json={"affiliate_url": "https://www.amazon.es/dp/B08TEST123"})
    assert r.json()["applies"] is False


def test_readiness_red_sin_programa_bloquea(client):
    _as_admin()
    r = client.post(
        "/v1/affiliates/readiness",
        json={"affiliate_url": "https://www.awin1.com/cread.php?x=1", "current_price": 10, "previous_price": 20},
    )
    body = r.json()
    assert body["applies"] is True and body["ready"] is False
    codes = {b["code"] for b in body["blockers"]}
    assert {"program_disabled", "reference_not_proof", "shipping_info"} <= codes
    assert body["savings_amount"] == "10.00" and body["discount_percentage"] == 50


def test_telegram_bloquea_enlace_de_red_sin_chollo_listo(client, monkeypatch):
    _as_admin()
    settings = Settings(telegram_enabled=True, telegram_bot_token="tok", telegram_main_channel_id="chan")
    app.dependency_overrides[get_settings] = lambda: settings
    bot = MagicMock()
    monkeypatch.setattr("app.modules.telegram.api.router.TelegramBot", lambda token: bot)
    r = client.post(
        "/v1/telegram/notify",
        json={"text": "🍄 FIXTURE\n🛒 https://www.awin1.com/cread.php?awinmid=1", "image_url": "https://img.example.com/x.jpg"},
    )
    assert r.status_code == 400
    bot.send_preformatted.assert_not_called()
