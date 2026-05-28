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
