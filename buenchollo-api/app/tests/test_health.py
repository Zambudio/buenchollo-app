"""Tests del módulo de health checks.

Cubre:
- `/health` responde 200 con el payload esperado y NO toca BD ni servicios.
- `/health/ready` responde 200 cuando la BD responde a SELECT 1 y la
  config Supabase está completa.
- `/health/ready` responde 503 cuando la BD falla.
- `/health/ready` responde 503 cuando faltan credenciales Supabase.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import get_db
from app.core.health import router as health_router


def _build_app(*, db_ok: bool, settings: Settings | None = None) -> TestClient:
    """App mínima con el router de health y dependencies override.

    No registramos middlewares (request_id, rate_limit) para que los tests
    sean independientes y rápidos.
    """
    app = FastAPI()
    app.include_router(health_router)

    async def _fake_db():
        session = MagicMock()
        if db_ok:
            session.execute = AsyncMock(return_value=MagicMock())
        else:
            session.execute = AsyncMock(side_effect=RuntimeError("connection refused"))
        yield session

    app.dependency_overrides[get_db] = _fake_db

    if settings is not None:
        from app.core.config import get_settings
        app.dependency_overrides[get_settings] = lambda: settings

    return TestClient(app)


# ── /health (liveness) ─────────────────────────────────────────────────────

def test_health_liveness_responde_200_y_no_toca_bd():
    """El liveness debe ser barato — sin importar el estado de la BD."""
    client = _build_app(db_ok=False)  # BD rota a propósito

    r = client.get("/health")

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "app" in body
    assert "environment" in body


# ── /health/ready (readiness) ──────────────────────────────────────────────

def test_health_ready_devuelve_200_si_bd_y_supabase_ok():
    client = _build_app(
        db_ok=True,
        settings=Settings(
            supabase_url="https://x.supabase.co",
            supabase_key="key-xyz",
        ),
    )

    r = client.get("/health/ready")

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["checks"]["db"]["status"] == "ok"
    assert "latency_ms" in body["checks"]["db"]
    assert body["checks"]["supabase_auth"]["status"] == "ok"


def test_health_ready_devuelve_503_si_bd_falla():
    client = _build_app(
        db_ok=False,
        settings=Settings(
            supabase_url="https://x.supabase.co",
            supabase_key="key-xyz",
        ),
    )

    r = client.get("/health/ready")

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["db"]["status"] == "error"
    assert body["checks"]["db"]["error"] == "RuntimeError"


def test_health_ready_devuelve_503_si_faltan_credenciales_supabase():
    client = _build_app(
        db_ok=True,
        settings=Settings(supabase_url="", supabase_key=""),
    )

    r = client.get("/health/ready")

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["supabase_auth"]["status"] == "error"
    assert body["checks"]["supabase_auth"]["error"] == "credentials_missing"
