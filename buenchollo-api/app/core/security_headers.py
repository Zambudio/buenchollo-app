"""Middleware que añade Security Headers a TODAS las respuestas.

Defensa en profundidad ante XSS, clickjacking, MIME sniffing y fuga
de URLs por Referer. Documentado en SECURITY_AUDIT.md SEC-03.

Cabeceras emitidas:

- Content-Security-Policy: política conservadora que permite los orígenes
  reales del proyecto (Supabase, fonts.google, imágenes de Amazon). Si
  el frontend se sirve detrás del mismo proxy, esta CSP se aplica también
  a los HTML estáticos; en su defecto, el reverse proxy debe replicarla.
- X-Frame-Options: DENY → impide embedding en iframes (clickjacking).
- X-Content-Type-Options: nosniff → impide MIME sniffing.
- Referrer-Policy: strict-origin-when-cross-origin → no fuga la URL
  completa a destinos externos.
- Permissions-Policy: deshabilita APIs sensibles del navegador
  (geolocalización, cámara, micrófono, payment).
- Strict-Transport-Security: sólo en producción, fuerza HTTPS para los
  próximos 6 meses. En dev local (http://localhost) se omite para no
  romper el flujo.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Política CSP. Se queda en una sola línea para enviarla tal cual; el orden
# de las directivas no importa. Cambios deben revisarse contra los orígenes
# reales que la app necesita cargar.
_CSP = "; ".join([
    "default-src 'self'",
    # data: para imágenes inline (favicons, placeholders). https para Amazon
    # (m.media-amazon.com, *.amazon.*) y Supabase Storage.
    "img-src 'self' data: https:",
    # 'unsafe-inline' es desafortunado pero React + shadcn inyectan styles
    # inline. Una mitigación futura sería usar nonces; over-engineering ahora.
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    # connect-src cubre las llamadas fetch/XHR/WebSocket: la propia API,
    # Supabase Auth/Storage, Sentry SaaS.
    "connect-src 'self' https://*.supabase.co https://*.ingest.sentry.io",
    # No permitimos scripts inline (defensa anti-XSS). React empaqueta su
    # JS en archivos servidos por el bundler, no usa inline.
    "script-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
])

# CSP relajada SÓLO para las páginas de documentación interactiva (Swagger UI
# y ReDoc), que cargan su JS/CSS desde cdn.jsdelivr.net e incluyen un script
# inline de arranque. Sin esto la página sale en blanco. El alcance se limita
# a las rutas de docs (ver `_DOCS_PATHS`); el resto de la API mantiene la CSP
# estricta de arriba.
_CSP_DOCS = "; ".join([
    "default-src 'self'",
    "img-src 'self' data: https:",
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "font-src 'self' data: https://cdn.jsdelivr.net",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
])

# Rutas (HTML) donde aplica `_CSP_DOCS`. Son las que sirve FastAPI por defecto
# para Swagger UI / ReDoc. `/openapi.json` no se incluye: es JSON y no necesita
# excepción de CSP.
_DOCS_PATHS = frozenset({"/docs", "/redoc", "/docs/oauth2-redirect"})

# Permissions-Policy: deshabilitamos por completo lo que no usamos. Si
# alguna feature legítima rompe en el futuro, quitarla de la lista.
_PERMISSIONS_POLICY = ", ".join([
    "accelerometer=()",
    "camera=()",
    "geolocation=()",
    "gyroscope=()",
    "magnetometer=()",
    "microphone=()",
    "payment=()",
    "usb=()",
])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inyecta cabeceras de seguridad en cada respuesta."""

    def __init__(self, app, *, enable_hsts: bool = False):
        super().__init__(app)
        # HSTS sólo en producción: en dev local (http://localhost) bloquearía
        # cualquier acceso futuro al hostname si el browser lo cachea.
        self._enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # setdefault: si una respuesta ya trae su propia cabecera (raro),
        # no la pisamos. Las páginas de docs usan una CSP relajada acotada.
        csp = _CSP_DOCS if request.url.path in _DOCS_PATHS else _CSP
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", _PERMISSIONS_POLICY)
        if self._enable_hsts:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=15552000; includeSubDomains",
            )
        return response
