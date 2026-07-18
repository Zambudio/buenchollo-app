"""Middleware que añade `Cache-Control` explícito a las respuestas de /v1.

Sin cabecera explícita del origen, cualquier capa intermedia (la Cache Rule
de Cloudflare sobre api.buenchollotech.com, o el propio navegador) decide por
su cuenta qué cachear — causa real de los contadores de votos/comentarios
obsoletos tras un F5 (ver docs/guides/Cloudflare.md § T9).

Política:

- Por defecto, TODO /v1 responde `no-store`: datos por-usuario (my-votes,
  favorites), admin, detalle de chollo y comentarios van siempre a origen.
- Solo los listados públicos (allowlist EXACTA de rutas GET, nunca prefijos:
  bajo /v1/categories y /v1/stores cuelgan GETs de admin) se marcan
  `public, max-age=0, s-maxage=30`: el navegador revalida siempre
  (max-age=0) y únicamente el borde de Cloudflare cachea 30 segundos
  (s-maxage), con la regla del panel en modo "respect origin".
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_NO_STORE = "no-store"
_PUBLIC_LISTING = "public, max-age=0, s-maxage=30"

# Rutas exactas de listados públicos sin auth y con idéntica respuesta para
# cualquier usuario. Ampliar sólo con endpoints que cumplan ambas condiciones.
_PUBLIC_LISTING_PATHS = frozenset({
    "/v1/deals",
    "/v1/deals/latest",
    "/v1/deals/popular",
    "/v1/categories",
    "/v1/stores",
})


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """Inyecta la política de caché en cada respuesta de la API versionada."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        path = request.url.path
        if not path.startswith("/v1"):
            return response
        cacheable = (
            request.method == "GET"
            and response.status_code == 200
            and path in _PUBLIC_LISTING_PATHS
        )
        # setdefault: un endpoint concreto puede fijar su propia política.
        response.headers.setdefault(
            "Cache-Control", _PUBLIC_LISTING if cacheable else _NO_STORE
        )
        return response
