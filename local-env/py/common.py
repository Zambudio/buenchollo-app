"""Rutas y configuración compartidas por los scripts del entorno local.

Todo lo que es estado de máquina (binarios de Postgres, datos, venv, logs)
vive fuera del repo, en %LOCALAPPDATA%\\BuenCholloLocal (o BCT_LOCAL_HOME):
el repo puede estar en un share de red y no queremos ni ensuciarlo ni que
el NAS cargue nada de esto. Ver docs/guides/LOCAL-ENV.md.
"""

from __future__ import annotations

import fnmatch
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values

LOCAL_ENV_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = LOCAL_ENV_DIR.parent
API_DIR = REPO_DIR / "buenchollo-api"
WEB_DIR = REPO_DIR / "buenchollo-web"

RUNTIME_DIR = Path(
    os.environ.get("BCT_LOCAL_HOME")
    or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "BuenCholloLocal"
)
STATE_FILE = RUNTIME_DIR / "state.json"

PG_HOST = "127.0.0.1"
PG_PORT = int(os.environ.get("BCT_PG_PORT", "54329"))
PG_USER = "postgres"
PG_DB = "buenchollo_local"


def local_dsn(database: str = PG_DB) -> str:
    """DSN para asyncpg (sin el prefijo de driver de SQLAlchemy)."""
    return f"postgresql://{PG_USER}@{PG_HOST}:{PG_PORT}/{database}"


def local_sqlalchemy_url() -> str:
    return f"postgresql+asyncpg://{PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}"


def load_config() -> dict:
    """config.json (versionado) + config.local.json (opcional, ignorado por git)."""
    config = json.loads((LOCAL_ENV_DIR / "config.json").read_text(encoding="utf-8"))
    override = LOCAL_ENV_DIR / "config.local.json"
    if override.exists():
        config.update(json.loads(override.read_text(encoding="utf-8")))
    return config


def api_dotenv() -> dict[str, str]:
    """Valores del .env real de la API (credenciales de Supabase, Amazon...).

    Solo se leen; nunca se imprimen. El .env apunta a la base de datos de
    producción: los scripts locales lo usan exclusivamente para la copia de
    solo lectura del catálogo y para la API de administración de Auth.
    """
    path = API_DIR / ".env"
    if not path.exists():
        raise SystemExit(
            f"Falta {path}. Cópialo desde el NAS (ver docs/guides/LOCAL-ENV.md, sección 'Otro PC')."
        )
    return {k: v for k, v in dotenv_values(path, encoding="utf-8-sig").items() if v is not None}


def prod_dsn() -> str:
    url = api_dotenv().get("DATABASE_URL", "")
    if not url:
        raise SystemExit("DATABASE_URL no está en buenchollo-api/.env")
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def supabase_url() -> str:
    return api_dotenv().get("SUPABASE_URL", "").split("/rest/v1")[0].rstrip("/")


def supabase_service_key() -> str:
    return api_dotenv().get("SUPABASE_KEY", "")


def read_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def write_state(**changes) -> None:
    state = read_state()
    state.update(changes)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def email_matches(email: str | None, patterns: list[str]) -> bool:
    if not email:
        return False
    email = email.lower()
    return any(fnmatch.fnmatchcase(email, p.lower()) for p in patterns)
