"""Seguridad por defecto en producción: docs desactivadas, CORS sin '*' y
aviso si ANALYTICS_HASH_SECRET cae al respaldo de SUPABASE_KEY."""
import importlib
import logging

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings


def _reload_main(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    import app.main as main

    return importlib.reload(main)


@pytest.fixture(autouse=True)
def _restore_main(monkeypatch):
    yield
    monkeypatch.undo()
    get_settings.cache_clear()
    import app.main as main

    importlib.reload(main)


def test_docs_desactivadas_en_produccion(monkeypatch):
    main = _reload_main(
        monkeypatch, APP_ENV="production", CORS_ORIGINS="https://buenchollotech.com",
        ANALYTICS_HASH_SECRET="s",
    )
    assert main.app.docs_url is None
    assert main.app.redoc_url is None
    assert main.app.openapi_url is None
    client = TestClient(main.app)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_docs_activas_fuera_de_produccion(monkeypatch):
    main = _reload_main(monkeypatch, APP_ENV="local")
    assert main.app.docs_url == "/docs"
    assert main.app.redoc_url == "/redoc"
    assert main.app.openapi_url == "/openapi.json"
    assert TestClient(main.app).get("/openapi.json").status_code == 200


def test_cors_asterisco_falla_en_produccion():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(app_env="production", cors_origins="*")
    with pytest.raises(ValidationError):
        Settings(app_env="production", cors_origins='["https://a.com","*"]')


def test_cors_explicito_valido_en_produccion_y_asterisco_en_local():
    Settings(app_env="production", cors_origins="https://a.com")
    Settings(app_env="local", cors_origins="*")


def _warnings_al_arrancar(monkeypatch, secret: str) -> list[str]:
    # `configure_logging` reconfigura el root logger al importar main, así que
    # se captura con un handler propio en el logger `app.main`.
    messages: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.WARNING:
                messages.append(record.getMessage())

    handler = _Capture()
    logging.getLogger("app.main").addHandler(handler)
    try:
        _reload_main(
            monkeypatch, APP_ENV="production", CORS_ORIGINS="https://buenchollotech.com",
            ANALYTICS_HASH_SECRET=secret,
        )
    finally:
        logging.getLogger("app.main").removeHandler(handler)
    return messages


def test_aviso_si_falta_analytics_hash_secret_en_produccion(monkeypatch):
    assert any("ANALYTICS_HASH_SECRET" in m for m in _warnings_al_arrancar(monkeypatch, ""))


def test_sin_aviso_si_analytics_hash_secret_definido(monkeypatch):
    assert not any("ANALYTICS_HASH_SECRET" in m for m in _warnings_al_arrancar(monkeypatch, "un-secreto"))
