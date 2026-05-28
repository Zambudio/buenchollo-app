"""Rate limiting con slowapi.

Modelo: límites por IP del cliente con storage en memoria. Suficiente
para el monolito desplegado en NAS Synology. Si en el futuro se escala
a múltiples instancias, cambiar `storage_uri` a Redis (`redis://...`)
para que el contador sea compartido.

Uso:

    # En main.py
    from app.core.rate_limit import limiter, rate_limit_exceeded_handler
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # En cualquier router
    from app.core.rate_limit import limiter
    @router.post("/expensive")
    @limiter.limit("10/minute")
    async def endpoint(request: Request, ...):
        ...

Detalle importante: el decorador `@limiter.limit("...")` exige que el
endpoint tenga un parámetro `request: Request` en su firma (slowapi lo
usa para resolver la IP). Si falta, FastAPI no inyectará nada y slowapi
disparará un AttributeError en runtime.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.request_id import REQUEST_ID_HEADER, get_request_id


def _key_func(request: Request) -> str:
    """Identifica al cliente para contar peticiones.

    Respeta `X-Forwarded-For` cuando viene del proxy/Nginx delante del
    contenedor (típico en NAS Synology con reverse proxy). Cae a la IP
    de la conexión directa si no.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Primera IP de la cadena = cliente original
        return forwarded.split(",", 1)[0].strip()
    return get_remote_address(request)


_settings = get_settings()

# `enabled=False` desactiva todos los decoradores @limiter.limit(...) sin
# tocar el código: útil en tests masivos y en desarrollo si molesta.
#
# `headers_enabled` no se activa: con True slowapi exige un `response: Response`
# en cada endpoint decorado, lo que añade boilerplate sin valor real para el
# cliente. La información que importa (cuándo reintentar) la damos en la
# respuesta 429 vía `Retry-After`.
limiter = Limiter(
    key_func=_key_func,
    enabled=_settings.rate_limit_enabled,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Devuelve 429 con nuestro formato `{"detail": "..."}` + X-Request-Id."""
    headers: dict[str, str] = {}
    rid = get_request_id()
    if rid:
        headers[REQUEST_ID_HEADER] = rid
    # slowapi adjunta retry-after en exc.detail; lo usamos para Retry-After estándar.
    if hasattr(exc, "detail") and exc.detail:
        # `exc.detail` típico: "10 per 1 minute"
        retry_after_seconds = _estimate_retry_after(str(exc.detail))
        if retry_after_seconds:
            headers["Retry-After"] = str(retry_after_seconds)

    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Has excedido el límite de peticiones. Espera un momento e inténtalo de nuevo."
            ),
        },
        headers=headers,
    )


def _estimate_retry_after(detail: str) -> int | None:
    """Extrae segundos de espera de un string tipo 'N per X second(s)/minute/hour'."""
    parts = detail.lower().split(" per ")
    if len(parts) != 2:
        return None
    window = parts[1].strip()
    tokens = window.split()
    if not tokens:
        return None
    try:
        amount = int(tokens[0]) if tokens[0].isdigit() else 1
    except ValueError:
        amount = 1
    unit = tokens[-1].rstrip("s")
    seconds_per_unit = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}.get(unit)
    if not seconds_per_unit:
        return None
    return amount * seconds_per_unit
