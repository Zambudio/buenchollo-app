"""Endpoints de salud (liveness y readiness).

Convención estándar de orquestadores tipo K8s, Docker Swarm y Synology
Container Manager:

- **`/health`** (liveness):
  Responde 200 si el proceso está vivo. NO toca dependencias externas.
  Ideal para que el orquestador sepa cuándo reiniciar un contenedor:
  si esto falla, el proceso está colgado y hay que reciclarlo.

- **`/health/ready`** (readiness):
  Responde 200 si la API puede atender tráfico (BD accesible, config
  cargada). Responde 503 si alguna dependencia crítica está caída.
  El orquestador NO debería enrutar tráfico a esta instancia mientras
  responda 503, pero NO la reinicia (puede recuperarse sola).

Por qué dos endpoints en vez de uno: si las mezclas, un fallo temporal
de la BD provocaría reinicios cíclicos del contenedor (cosa que no
arregla nada y agrava el problema con cold starts repetidos).
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

#: Timeout máximo (segundos) para el probe a BD. Suficiente para que
#: PgBouncer + Supabase respondan; si tarda más, asumimos problema.
_DB_PROBE_TIMEOUT_S = 3.0


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    """Liveness probe — confirma que el proceso atiende peticiones.

    No toca BD ni servicios externos. Si esto falla, el contenedor está
    realmente roto y hay que reiniciarlo.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/health/ready")
async def health_ready(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Readiness probe — confirma que la API puede servir tráfico real.

    Comprueba:
    - Conectividad a la BD (SELECT 1 contra Postgres via PgBouncer).
    - Configuración de Supabase presente (sin esto Auth no funcionaría;
      no hacemos HTTP a Supabase para no añadir latencia).

    Si algo falla, responde 503 con el detalle por chequeo. Útil tanto
    para orquestadores como para diagnóstico humano:
    `curl /health/ready | jq .checks` enseña exactamente qué falla.
    """
    checks: dict[str, dict] = {}

    # ── BD ──────────────────────────────────────────────────────────────
    db_start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - db_start) * 1000, 1),
        }
    except Exception as exc:
        checks["db"] = {
            "status": "error",
            "error": type(exc).__name__,
            "latency_ms": round((time.perf_counter() - db_start) * 1000, 1),
        }
        logger.warning("health/ready: probe BD falló: %s", exc)

    # ── Supabase Auth (config check; sin HTTP) ──────────────────────────
    if settings.supabase_url and settings.supabase_key:
        checks["supabase_auth"] = {"status": "ok"}
    else:
        checks["supabase_auth"] = {
            "status": "error",
            "error": "credentials_missing",
        }

    all_ok = all(c["status"] == "ok" for c in checks.values())
    payload = {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
    }
    return JSONResponse(content=payload, status_code=200 if all_ok else 503)
