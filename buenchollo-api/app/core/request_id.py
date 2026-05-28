"""Identificador único por petición HTTP.

Cada request entrante recibe un `request_id` (UUID4) que viaja con la
respuesta como cabecera `X-Request-Id` y se inyecta en cada log que se emita
mientras se procesa esa petición.

Si la petición ya viene con `X-Request-Id` desde un proxy o load balancer,
se respeta — útil para trazabilidad end-to-end cuando hay un Nginx delante.

Uso:

    # En main.py
    from app.core.request_id import RequestIdMiddleware
    app.add_middleware(RequestIdMiddleware)

    # Desde cualquier sitio del código
    from app.core.request_id import get_request_id
    logger.info("Algo pasó", extra={"foo": "bar"})    # request_id va automático
    rid = get_request_id()                            # si lo necesitas explícito
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


REQUEST_ID_HEADER = "X-Request-Id"
"""Nombre de la cabecera HTTP en peticiones y respuestas."""

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Devuelve el request_id de la petición en curso, si lo hay."""
    return _request_id_ctx.get()


def _new_request_id() -> str:
    return uuid.uuid4().hex  # 32 chars sin guiones, más compacto en logs


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware HTTP que asigna o respeta un `X-Request-Id` por petición.

    Reglas:
    - Si la petición trae `X-Request-Id`, se reutiliza tal cual.
    - Si no, se genera un UUID4 hex.
    - Se inyecta en el `ContextVar` antes de invocar al endpoint y se
      reinicia tras responder.
    - La respuesta siempre incluye `X-Request-Id` para que el cliente lo
      vea (y lo cite si reporta un error).
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming or _new_request_id()
        token = _request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
