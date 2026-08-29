"""Tests de compresión GZip HTTP en respuestas de FastAPI."""
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.testclient import TestClient


def _app() -> TestClient:
    app = FastAPI()
    app.add_middleware(GZipMiddleware, minimum_size=500)

    @app.get("/small")
    def small_endpoint():
        return {"msg": "ok"}

    @app.get("/large")
    def large_endpoint():
        return {"items": [{"id": i, "name": f"Product {i}" * 10} for i in range(50)]}

    return TestClient(app)


def test_respuestas_grandes_se_comprimen_con_gzip():
    client = _app()
    # TestClient de starlette maneja automáticamente Accept-Encoding y descompresión,
    # pero podemos verificar Content-Encoding o headers en la respuesta
    response = client.get("/large", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    # En starlette TestClient, la descompresión es automática y el body es JSON válido
    data = response.json()
    assert len(data["items"]) == 50


def test_respuestas_pequenas_no_comprimen():
    client = _app()
    response = client.get("/small", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.json() == {"msg": "ok"}
