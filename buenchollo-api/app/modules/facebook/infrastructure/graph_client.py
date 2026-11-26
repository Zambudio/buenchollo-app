"""Cliente mínimo de la Graph API para publicar fotos en una página de Facebook.

El token configurado es el del usuario del sistema del porfolio (`EAA…`, sin
caducidad); con él se pide el token de la página (`/{page_id}?fields=access_token`),
que es el que publica. La foto se sube en la propia petición (multipart): no
hace falta una URL pública como en Instagram.

Los tokens van en la cabecera `Authorization`, nunca en la URL, para que no
acaben en logs ni en mensajes de excepción.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

GRAPH_HOST = "https://graph.facebook.com"
_TIMEOUT = (10, 60)
# 190: token caducado/revocado. 10/200/210: sin permiso sobre la página.
_TOKEN_ERROR_CODES = {190, 10, 200, 210}


class FacebookApiError(Exception):
    def __init__(self, message: str, *, code: int | None = None, transient: bool = False, unknown: bool = False):
        super().__init__(message)
        self.code = code
        # Reintentable más tarde (caída, límite, error temporal de Meta).
        self.transient = transient
        # No se sabe si Facebook lo publicó (tiempo agotado tras enviar): no repetir.
        self.unknown = unknown

    @property
    def token_invalid(self) -> bool:
        return self.code in _TOKEN_ERROR_CODES


@dataclass(frozen=True)
class PageAccess:
    name: str | None
    access_token: str


class FacebookGraphClient:
    def __init__(self, access_token: str, version: str = "v23.0", http=None):
        self._token = access_token
        self._base = f"{GRAPH_HOST}/{version.strip('/')}" if version else GRAPH_HOST
        self._http = http or requests

    def page_access(self, page_id: str) -> PageAccess:
        """Nombre de la página y su token (el que publica)."""
        data = self._request("GET", f"{self._base}/{page_id}", self._token, params={"fields": "name,access_token"})
        token = data.get("access_token")
        if not token:
            raise FacebookApiError("El token no da acceso a la página (falta pages_manage_posts o el activo)", code=200)
        return PageAccess(name=data.get("name"), access_token=str(token))

    def publish_photo(self, page_id: str, page_token: str, image: bytes, message: str) -> str:
        """Publica la foto con su texto en el muro de la página. Devuelve el id del post."""
        data = self._request(
            "POST",
            f"{self._base}/{page_id}/photos",
            page_token,
            data={"message": message, "published": "true"},
            files={"source": ("chollo.jpg", image, "image/jpeg")},
            unknown_on_timeout=True,
        )
        return str(data.get("post_id") or data.get("id") or "")

    # ── Internos ───────────────────────────────────────────────────────────

    def _request(self, method, url, token, *, params=None, data=None, files=None, unknown_on_timeout=False) -> dict:
        try:
            resp = self._http.request(
                method, url, params=params, data=data, files=files, timeout=_TIMEOUT,
                headers={"Authorization": f"Bearer {token}"},
            )
        except (requests.ReadTimeout, requests.exceptions.ChunkedEncodingError) as exc:
            raise FacebookApiError(
                f"Facebook no respondió ({type(exc).__name__})", transient=not unknown_on_timeout, unknown=unknown_on_timeout
            ) from None
        except requests.RequestException as exc:
            raise FacebookApiError(f"Sin conexión con Facebook ({type(exc).__name__})", transient=True) from None
        return self._json(resp)

    @staticmethod
    def _json(resp) -> dict:
        try:
            data = resp.json()
        except ValueError:
            data = {}
        if resp.status_code < 400 and isinstance(data, dict) and "error" not in data:
            return data
        error = data.get("error") if isinstance(data, dict) else None
        error = error if isinstance(error, dict) else {}
        message = str(error.get("message") or f"HTTP {resp.status_code}")[:300]
        code = error.get("code")
        transient = bool(error.get("is_transient")) or resp.status_code >= 500 or code in {1, 2, 4, 17, 32, 368, 613}
        raise FacebookApiError(message, code=code if isinstance(code, int) else None, transient=transient)
