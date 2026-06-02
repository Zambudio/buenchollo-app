"""Tests del SecurityHeadersMiddleware.

Verifican que cada respuesta lleva las cabeceras defensivas y que HSTS
sólo se emite cuando el flag enable_hsts está activo.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security_headers import SecurityHeadersMiddleware


def _app(*, enable_hsts: bool = False) -> TestClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=enable_hsts)

    @app.get("/x")
    def x() -> dict:
        return {"ok": True}

    return TestClient(app)


def test_emite_csp_x_frame_y_nosniff():
    client = _app()
    response = client.get("/x")
    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_emite_referrer_y_permissions_policy():
    client = _app()
    response = client.get("/x")
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    perms = response.headers["Permissions-Policy"]
    assert "camera=()" in perms
    assert "geolocation=()" in perms
    assert "microphone=()" in perms


def test_no_emite_hsts_en_dev():
    client = _app(enable_hsts=False)
    response = client.get("/x")
    assert "Strict-Transport-Security" not in response.headers


def test_emite_hsts_en_produccion():
    client = _app(enable_hsts=True)
    response = client.get("/x")
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "includeSubDomains" in response.headers["Strict-Transport-Security"]


def test_csp_permite_supabase_y_sentry():
    client = _app()
    response = client.get("/x")
    csp = response.headers["Content-Security-Policy"]
    assert "https://*.supabase.co" in csp
    assert "https://*.ingest.sentry.io" in csp
