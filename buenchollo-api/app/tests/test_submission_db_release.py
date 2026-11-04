"""La conexión de BD se libera antes de la E/S externa lenta (C2, TD-11)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import AuthenticatedUser, get_current_user
from app.main import app
from app.modules.products.domain.entities import ProductPreview
from app.modules.submissions.api.dependencies import get_profile_repository
from app.modules.submissions.api.router import get_ingest_image_use_case
from app.modules.submissions.application.check_link import CheckLinkUseCase
from app.modules.submissions.application.create_submission import CreateSubmissionUseCase
from app.core.exceptions import TooManyRequestsError

ASIN = "B0ABCDEFGH"


class SpySession:
    def __init__(self, events):
        self.events = events

    async def rollback(self):
        self.events.append("release")

    async def commit(self):
        self.events.append("commit")


class ExpiringStore:
    """Simula un objeto ORM: tras el rollback leerlo lanzaría (lazy load)."""

    def __init__(self, events):
        self._events = events

    def __getattr__(self, name):
        if "release" in self._events:
            raise AssertionError(f"store.{name} leído tras liberar la sesión")
        return {"id": "store-1", "name": "Amazon"}[name]


class EventRepo:
    def __init__(self, events, store=None):
        self.events, self.store = events, store

    async def find_store_by_host(self, host):
        self.events.append("db")
        return self.store

    async def find_live_deal(self, asin, canonical_url):
        self.events.append("db")
        return None

    async def find_pending(self, asin, canonical_url):
        self.events.append("db")
        return None

    async def find_expired_deal(self, asin, canonical_url):
        self.events.append("db")
        return None

    async def count_pending_by_user(self, user_id):
        self.events.append("db")
        return 5

    async def count_since(self, user_id, since):
        self.events.append("db")
        return 0


class EventProvider:
    def __init__(self, events):
        self.events = events

    def get_product_preview(self, url_or_asin):
        self.events.append("amazon")
        return ProductPreview(title="T", asin=ASIN, current_price=10.0)


@pytest.mark.asyncio
async def test_check_link_libera_la_bd_antes_de_llamar_a_amazon():
    events: list[str] = []

    async def release():
        events.append("release")

    use_case = CheckLinkUseCase(
        EventRepo(events, store=ExpiringStore(events)),
        EventProvider(events),
        amazon_tag="tag-21",
        release_db=release,
    )
    result = await use_case.execute(f"https://www.amazon.es/dp/{ASIN}")

    assert events == ["db", "db", "db", "db", "release", "amazon"]
    assert result.store_id == "store-1"
    assert result.prefill is not None


@pytest.mark.asyncio
async def test_check_link_no_amazon_no_libera_ni_llama():
    events: list[str] = []

    async def release():
        events.append("release")

    use_case = CheckLinkUseCase(
        EventRepo(events), EventProvider(events), release_db=release
    )
    await use_case.execute("https://tienda.com/p/1")
    assert "amazon" not in events and "release" not in events


@pytest.mark.asyncio
async def test_crear_resuelve_el_enlace_corto_antes_de_tocar_la_bd():
    events: list[str] = []

    def resolver(url):
        events.append("short-link")
        return ASIN

    use_case = CreateSubmissionUseCase(EventRepo(events), None, asin_resolver=resolver)
    data = SimpleNamespace(url="https://amzn.to/abc")
    with pytest.raises(TooManyRequestsError):
        await use_case.execute("u1", data, "tag-21")
    assert events[0] == "short-link"
    assert events[1:] == ["db", "db"]


class _Profiles:
    def __init__(self, events, display_name="Pedro"):
        self.events, self.display_name = events, display_name

    async def get_by_user_id(self, user_id):
        self.events.append("profile")
        return SimpleNamespace(display_name=self.display_name)


class _Ingest:
    def __init__(self, events):
        self.events = events

    async def from_url(self, user_id, url):
        self.events.append("storage")
        return "https://cdn/x.webp", 1, 1


@pytest.fixture
def events():
    limiter.reset()
    ev: list[str] = []
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="u1")
    app.dependency_overrides[get_db] = lambda: SpySession(ev)
    app.dependency_overrides[get_ingest_image_use_case] = lambda: _Ingest(ev)
    yield ev
    app.dependency_overrides.clear()


def test_endpoint_de_imagen_libera_la_bd_tras_comprobar_el_perfil(events):
    app.dependency_overrides[get_profile_repository] = lambda: _Profiles(events)
    resp = TestClient(app).post(
        "/v1/submissions/images/from-url", json={"url": "https://ejemplo.com/a.jpg"}
    )
    assert resp.status_code == 200, resp.text
    assert events[:3] == ["profile", "release", "storage"]


def test_perfil_incompleto_tambien_libera_la_bd(events):
    app.dependency_overrides[get_profile_repository] = lambda: _Profiles(events, "  ")
    resp = TestClient(app).post(
        "/v1/submissions/images/from-url", json={"url": "https://ejemplo.com/a.jpg"}
    )
    assert resp.status_code == 403
    assert events[:2] == ["profile", "release"]
    assert "storage" not in events
