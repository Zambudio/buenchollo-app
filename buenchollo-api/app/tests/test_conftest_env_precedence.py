"""Regresión: una variable exportada en la shell debe ganar al `.env` local.

Con `load_dotenv(override=True)`, exportar DATABASE_URL hacia una base de test
(como indica docs/guides/LOCAL-ENV.md) no servía de nada si existía un `.env`
real: los tests de integración acababan contra la base de PRODUCCIÓN.
En CI no hay `.env` y el test pasa siempre; en un PC con `.env` es la guarda.
"""
import os
import subprocess
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]


def test_la_variable_exportada_gana_al_env_local():
    env = {**os.environ, "DATABASE_URL": "postgresql+asyncpg://sentinel@127.0.0.1:1/sentinel"}
    result = subprocess.run(
        [sys.executable, "-c", "import conftest, os; print(os.environ['DATABASE_URL'])"],
        cwd=API_ROOT, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("/sentinel")
