"""Tests del CacheHeadersMiddleware.

Verifican la política de caché de /v1: `no-store` por defecto (endpoints
por-usuario y admin nunca cacheables) y `public, max-age=0, s-maxage=30`
sólo en la allowlist exacta de listados públicos.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.core.cache_headers import CacheHeadersMiddleware


def _app() -> TestClient:
    app = FastAPI()
    app.add_middleware(CacheHeadersMiddleware)

    for path in (
        "/v1/deals",
        "/v1/deals/latest",
        "/v1/deals/my-votes",
        "/v1/deals/favorites",
        "/v1/deals/un-slug",
        "/v1/categories",
        "/v1/categories/admin/all",
        "/v1/stores/admin/all",
        "/health",
    ):
        app.get(path)(lambda: {"ok": True})

    @app.post("/v1/deals")
    def create_deal() -> dict:
        return {"ok": True}

    # Listado de la allowlist respondiendo non-200 (p. ej. mantenimiento).
    @app.get("/v1/stores")
    def stores_caidas() -> JSONResponse:
        return JSONResponse({"detail": "mantenimiento"}, status_code=503)

    return TestClient(app)


def test_listados_publicos_cacheables_en_el_borde():
    client = _app()
    for path in ("/v1/deals", "/v1/deals/latest", "/v1/categories"):
        cc = client.get(path).headers["Cache-Control"]
        assert cc == "public, max-age=0, s-maxage=30", path


def test_endpoints_por_usuario_no_store():
    """my-votes/favorites cuelgan de /v1/deals pero son por-usuario: jamás
    deben ser cacheables (fuga entre usuarios en el borde)."""
    client = _app()
    for path in ("/v1/deals/my-votes", "/v1/deals/favorites", "/v1/deals/un-slug"):
        assert client.get(path).headers["Cache-Control"] == "no-store", path


def test_admin_no_store_aunque_cuelgue_de_prefijo_publico():
    client = _app()
    for path in ("/v1/categories/admin/all", "/v1/stores/admin/all"):
        assert client.get(path).headers["Cache-Control"] == "no-store", path


def test_metodos_de_escritura_no_store():
    client = _app()
    assert client.post("/v1/deals").headers["Cache-Control"] == "no-store"


def test_non_200_en_allowlist_no_cacheable():
    """Un error en ruta de la allowlist no debe quedarse 30s en el borde."""
    client = _app()
    response = client.get("/v1/stores")
    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"


def test_fuera_de_v1_sin_cabecera():
    """Fuera de /v1 (p. ej. /health) el middleware no impone política."""
    client = _app()
    assert "Cache-Control" not in client.get("/health").headers
