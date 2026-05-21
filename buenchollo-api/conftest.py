"""
conftest.py — configuración global de pytest para buenchollo-api.

1. Carga el .env ANTES de que cualquier módulo de la app sea importado,
   resolviendo el problema de lru_cache en get_settings() / database.py.
2. Expone un fixture `integration_client` — un único TestClient compartido
   por todos los tests de integración para evitar cierres prematuros del
   event loop de asyncio entre clases de test.
"""
from pathlib import Path
from unittest.mock import MagicMock
import sys

# ── Mocks de dependencias externas ───────────────────────────────────────────
# Necesario antes de importar cualquier módulo de la app para evitar errores
# de compilación de wheels (supabase, amazon_paapi) en entornos de CI/dev.
_mock_supabase = MagicMock()
_mock_supabase.Client = MagicMock
_mock_supabase.create_client = MagicMock(return_value=MagicMock())
sys.modules.setdefault("supabase", _mock_supabase)
sys.modules.setdefault("amazon_paapi", MagicMock())
sys.modules.setdefault("amazon_paapi.errors", MagicMock())

# ── Variables de entorno ──────────────────────────────────────────────────────
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# ── Fixture de cliente compartido ────────────────────────────────────────────
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def integration_client():
    """
    TestClient con lifespan activo, compartido por toda la sesión de pytest.
    Usar este fixture en tests de integración evita que cada clase de test
    abra y cierre el event loop de asyncio por separado.
    """
    from app.main import app
    with TestClient(app) as client:
        yield client
