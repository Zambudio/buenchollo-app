"""Tests del rate limiter.

Cubre:
- Un endpoint decorado con `@limiter.limit("2/minute")` devuelve 429
  tras la tercera petición desde la misma IP.
- La respuesta 429 lleva nuestro `detail`, `Retry-After` y headers
  estándar `X-RateLimit-*`.
- `_estimate_retry_after` calcula bien los segundos.
"""
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.rate_limit import (
    _estimate_retry_after,
    limiter,
    rate_limit_exceeded_handler,
)


def _build_app_with_limit(rule: str) -> TestClient:
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/limited")
    @limiter.limit(rule)
    def limited(request: Request) -> dict:
        return {"ok": True}

    return TestClient(app)


def test_endpoint_devuelve_429_tras_superar_el_limite():
    client = _build_app_with_limit("2/minute")

    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200
    r = client.get("/limited")

    assert r.status_code == 429
    body = r.json()
    assert "límite" in body["detail"].lower()
    # Nuestro Retry-After custom (no usamos headers_enabled de slowapi)
    assert "retry-after" in {k.lower() for k in r.headers}


def test_estimate_retry_after_para_distintas_ventanas():
    assert _estimate_retry_after("5 per 1 second") == 1
    assert _estimate_retry_after("10 per 1 minute") == 60
    assert _estimate_retry_after("100 per 2 hour") == 7200
    assert _estimate_retry_after("invalid") is None
    # slowapi a veces omite el número delante de la unidad
    assert _estimate_retry_after("10 per minute") == 60


def test_endpoints_no_decorados_no_se_limitan():
    """Las rutas sin @limiter.limit nunca devuelven 429."""
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/free")
    def free() -> dict:
        return {"ok": True}

    client = TestClient(app)
    for _ in range(20):
        assert client.get("/free").status_code == 200


# ── Identificación del cliente (C1) ──────────────────────────────────────────

from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402
from fastapi import Header  # noqa: E402
from starlette.requests import Request as StarletteRequest  # noqa: E402

from app.core.rate_limit import client_ip  # noqa: E402


def _request(headers: dict[str, str], peer: str = "10.0.0.5") -> StarletteRequest:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (peer, 12345),
    }
    return StarletteRequest(scope)


def test_client_ip_ignora_x_forwarded_for():
    assert client_ip(_request({"X-Forwarded-For": "1.2.3.4, 10.0.0.1"})) == "10.0.0.5"


def test_client_ip_usa_cf_connecting_ip():
    req = _request({"CF-Connecting-IP": " 203.0.113.9 ", "X-Forwarded-For": "1.2.3.4"})
    assert client_ip(req) == "203.0.113.9"


def test_client_ip_sin_cabeceras_usa_el_peer():
    assert client_ip(_request({})) == "10.0.0.5"


def _build_isolated_app(rule: str, name: str) -> TestClient:
    """Como `_build_app_with_limit`, pero con un endpoint de nombre propio:
    slowapi registra los límites por nombre de función y acumularía los de
    otros tests."""
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    def endpoint(request: Request) -> dict:
        return {"ok": True}

    endpoint.__name__ = name
    app.get("/limited")(limiter.limit(rule)(endpoint))
    return TestClient(app)


def test_xff_falsificado_no_cambia_el_bucket():
    limiter.reset()
    client = _build_isolated_app("2/minute", "limited_xff")
    assert client.get("/limited", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/limited", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200
    assert client.get("/limited", headers={"X-Forwarded-For": "3.3.3.3"}).status_code == 429


def test_cf_connecting_ip_separa_buckets():
    limiter.reset()
    client = _build_isolated_app("1/minute", "limited_cf")
    assert client.get("/limited", headers={"CF-Connecting-IP": "1.1.1.1"}).status_code == 200
    assert client.get("/limited", headers={"CF-Connecting-IP": "2.2.2.2"}).status_code == 200
    assert client.get("/limited", headers={"CF-Connecting-IP": "1.1.1.1"}).status_code == 429


# ── Límite por usuario en endpoints de propuestas ────────────────────────────


class _CountingProfileRepo:
    def __init__(self):
        self.calls = 0

    async def get_by_user_id(self, user_id):
        self.calls += 1
        return SimpleNamespace(display_name="Pedro")


class _FakeSession:
    async def rollback(self):
        return None

    async def commit(self):
        return None


class _FakeCheckLink:
    async def execute(self, url):
        return SimpleNamespace(
            status="ok", canonical_url=url, affiliate_url=url, is_amazon=False, warnings=[]
        )


@pytest.fixture
def submissions_client():
    from app.core.database import get_db
    from app.core.security import AuthenticatedUser, get_current_user
    from app.main import app
    from app.modules.submissions.api.dependencies import get_profile_repository
    from app.modules.submissions.api.router import get_check_link_use_case

    limiter.reset()
    profiles = _CountingProfileRepo()

    def fake_user(x_test_user: str = Header(...)) -> AuthenticatedUser:
        return AuthenticatedUser(id=x_test_user)

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_profile_repository] = lambda: profiles
    app.dependency_overrides[get_check_link_use_case] = lambda: _FakeCheckLink()
    app.dependency_overrides[get_db] = lambda: _FakeSession()
    yield TestClient(app), profiles
    app.dependency_overrides.clear()
    limiter.reset()


def _check(client, user, ip="9.9.9.9"):
    return client.post(
        "/v1/submissions/check-link",
        json={"url": "https://tienda.com/p/1"},
        headers={"X-Test-User": user, "CF-Connecting-IP": ip},
    )


def test_check_link_limita_por_usuario_y_no_por_ip(submissions_client):
    client, _ = submissions_client
    for _ in range(20):
        assert _check(client, "user-a").status_code == 200
    blocked = _check(client, "user-a")
    assert blocked.status_code == 429
    assert "límite" in blocked.json()["detail"].lower()
    assert blocked.headers["retry-after"] == "60"
    # Otro usuario desde la MISMA IP tiene su propio contador.
    assert _check(client, "user-b").status_code == 200


def test_check_link_cambiar_de_ip_no_evita_el_limite(submissions_client):
    client, _ = submissions_client
    for i in range(20):
        assert _check(client, "user-a", ip=f"1.1.1.{i}").status_code == 200
    assert _check(client, "user-a", ip="8.8.8.8").status_code == 429


def test_peticion_limitada_no_consulta_el_perfil(submissions_client):
    client, profiles = submissions_client
    for _ in range(20):
        _check(client, "user-a")
    assert profiles.calls == 20
    assert _check(client, "user-a").status_code == 429
    assert profiles.calls == 20
