"""FastAPI entrypoint for the BuenChollo backend."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.modules.products.api.router import router as products_router
from app.modules.categories.api.router import router as categories_router
from app.modules.deals.api.router import router as deals_router
from app.modules.stores.api.router import router as stores_router
from app.modules.users.api.router import router as auth_router
from app.modules.telegram.api.router import router as telegram_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación: inicia y detiene el scheduler."""
    scheduler = None
    try:
        from app.modules.deals.application.cleaner_service import DealCleanerService
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()
        cleaner = DealCleanerService(settings)
        scheduler.add_job(cleaner.mark_expired_deals, "interval", minutes=5)
        scheduler.add_job(cleaner.activate_scheduled_deals, "interval", minutes=5)
        scheduler.add_job(cleaner.clean_expired_deals, "cron", hour=3, minute=0)
        scheduler.start()
        logger.info(
            "Background scheduler iniciado: "
            "mark_expired + activate_scheduled (cada 5 min) | clean (03:00 diario)"
        )
    except Exception as exc:
        logger.warning("Scheduler no disponible, la API arranca sin él: %s", exc)

    yield  # La aplicación está en funcionamiento

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler detenido.")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# ── CORS ─────────────────────────────────────────────────────────────────────
_allow_all = "*" in settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else settings.cors_origins,
    allow_credentials=not _allow_all,  # credentials=True es incompatible con allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Devuelve 500 con CORS headers para que el browser pueda leer el error."""
    if isinstance(exc, HTTPException):
        raise exc  # dejar que FastAPI lo maneje normalmente
    logger.exception("Error no manejado: %s", exc)
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(categories_router)
app.include_router(deals_router)
app.include_router(stores_router)
app.include_router(telegram_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Return a small status payload for uptime checks."""
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}
