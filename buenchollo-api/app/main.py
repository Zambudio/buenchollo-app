"""FastAPI entrypoint for the BuenChollo backend."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.core.request_id import REQUEST_ID_HEADER, RequestIdMiddleware, get_request_id
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.sentry import init_sentry
from app.modules.products.api.router import router as products_router
from app.modules.categories.api.router import router as categories_router
from app.modules.deals.api.router import router as deals_router
from app.modules.stores.api.router import router as stores_router
from app.modules.users.api.router import router as auth_router
from app.modules.telegram.api.router import router as telegram_router
from app.modules.alerts.api.router import router as alerts_router
from app.modules.notifications.api.router import router as notifications_router
from app.modules.comments.api.router import router as comments_router

settings = get_settings()
configure_logging(settings.log_level, fmt=settings.log_format)
# Sentry debe inicializarse cuanto antes para capturar errores de arranque.
# Si SENTRY_DSN está vacío, no se inicializa y la app funciona normal.
init_sentry(settings)
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
        # Ejecutar limpieza una vez al arrancar para no esperar a las 3am
        cleaner.clean_expired_deals()
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

# Registro del limiter en el state de la app — slowapi lo resuelve por aquí.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ── Middlewares ──────────────────────────────────────────────────────────────
# Orden de registro = orden inverso de ejecución en Starlette. Queremos:
#   1) RequestId  (etiqueta toda la cadena)
#   2) RateLimit  (filtra antes de tocar la lógica)
#   3) CORS       (envuelve la respuesta final)
# Así que registramos en orden inverso: CORS, RateLimit, RequestId.
_allow_all = "*" in settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else settings.cors_origins,
    allow_credentials=not _allow_all,  # credentials=True es incompatible con allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],  # para que el browser pueda leerlo
)
app.add_middleware(SlowAPIMiddleware)
# Security headers: se registra DESPUÉS de CORS para que CORS pueda
# sobrescribir el Access-Control-* sin colisionar con la CSP. HSTS sólo
# en producción para no quemar el hostname en dev local con http://.
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=settings.app_env == "production",
)
app.add_middleware(RequestIdMiddleware)


def _with_request_id_header(headers: dict[str, str] | None = None) -> dict[str, str]:
    """Devuelve los `headers` con `X-Request-Id` añadido si hay request en curso.

    Las respuestas que se construyen aquí (handlers de error) no pasan por
    `RequestIdMiddleware.dispatch` después, así que añadimos el header a mano
    para que el cliente lo siga viendo en respuestas 4xx/5xx.
    """
    result = dict(headers or {})
    rid = get_request_id()
    if rid:
        result[REQUEST_ID_HEADER] = rid
    return result


@app.exception_handler(DomainError)
async def domain_exception_handler(request: Request, exc: DomainError):
    """Traduce excepciones de dominio a HTTP usando `exc.http_status`.

    Mantiene el mensaje del dominio como `detail`. Los logs se quedan en
    INFO (no es un error inesperado, es lógica de negocio). Si crece a
    volumen, considerar nivel WARNING para 4xx y ERROR para 5xx.
    """
    logger.info("DomainError %s: %s", type(exc).__name__, exc)
    content: dict = {"detail": str(exc)}
    # Las excepciones de dominio pueden adjuntar un `payload` con datos
    # estructurados para el cliente (p. ej. el deal existente en un
    # conflicto de duplicado). Se fusiona en el body de la respuesta.
    if extra := getattr(exc, "payload", None):
        content |= extra
    return JSONResponse(
        status_code=exc.http_status,
        content=content,
        headers=_with_request_id_header(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Captura cualquier excepción no manejada y devuelve 500 genérico.

    Las HTTPException de FastAPI se manejan por su propia ruta; las
    DomainError tienen handler dedicado arriba.
    """
    if isinstance(exc, HTTPException):
        raise exc  # dejar que FastAPI lo maneje normalmente
    logger.exception("Error no manejado: %s", exc)
    # CORS para respuestas de error: SOLO reflejamos el `Origin` si está
    # explícitamente en la allowlist. NUNCA reflejar arbitrario + Allow-
    # Credentials:true (origin reflection, OWASP A05). Si la app está en
    # modo abierto (CORS_ORIGINS=*), repetimos "*" sin credenciales.
    # Ver SECURITY_AUDIT.md SEC-02.
    origin = request.headers.get("origin", "")
    cors_headers: dict[str, str] = {}
    if _allow_all:
        cors_headers["Access-Control-Allow-Origin"] = "*"
    elif origin in settings.cors_origins:
        cors_headers["Access-Control-Allow-Origin"] = origin
        cors_headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
        headers=_with_request_id_header(cors_headers),
    )


# ── Routers ───────────────────────────────────────────────────────────────────
# Todos los routers de negocio cuelgan de /v1/. Esto permite introducir /v2/
# en el futuro sin romper clientes existentes (cohabitación durante la
# migración). Sólo el health check queda sin versionar — es infraestructura,
# no contrato.
v1 = APIRouter(prefix="/v1")
v1.include_router(auth_router)
v1.include_router(products_router)
v1.include_router(categories_router)
v1.include_router(deals_router)
v1.include_router(stores_router)
v1.include_router(telegram_router)
v1.include_router(alerts_router)
v1.include_router(notifications_router)
v1.include_router(comments_router)

app.include_router(v1)
app.include_router(health_router)  # /health y /health/ready — sin /v1
