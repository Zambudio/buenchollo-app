"""Cliente mínimo de la API de Instagram con inicio de sesión de Instagram
(`graph.instagram.com`): publicar una imagen en el feed y renovar el token.

Publicar son dos pasos: crear el contenedor con la URL pública de la imagen
(Instagram la descarga) y publicarlo cuando su estado es FINISHED.

El token va en la cabecera `Authorization`, nunca en la URL, para que no acabe
en logs ni en mensajes de excepción. Solo la renovación lo exige en la URL: sus
errores se registran sin el detalle de `requests`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

GRAPH_HOST = "https://graph.instagram.com"
# Tokens de Facebook (usuario del sistema de un porfolio empresarial, «EAA…»):
# misma API de publicación, pero en graph.facebook.com y sin renovación.
FACEBOOK_GRAPH_HOST = "https://graph.facebook.com"
_TIMEOUT = (10, 30)
_TOKEN_ERROR_CODES = {190}  # token caducado, revocado o inválido


class InstagramApiError(Exception):
    def __init__(self, message: str, *, code: int | None = None, transient: bool = False, unknown: bool = False):
        super().__init__(message)
        self.code = code
        # Reintentable más tarde (caída, límite, error temporal de Meta).
        self.transient = transient
        # No se sabe si Instagram lo hizo (tiempo agotado tras enviar): no repetir.
        self.unknown = unknown

    @property
    def token_invalid(self) -> bool:
        return self.code in _TOKEN_ERROR_CODES


@dataclass(frozen=True)
class RefreshedToken:
    access_token: str
    expires_in: int | None


class InstagramGraphClient:
    def __init__(self, access_token: str, version: str = "v23.0", http=None):
        self._token = access_token
        # Los tokens del inicio de sesión de Instagram empiezan por «IG»; el resto
        # (usuario del sistema de Meta Business) van contra graph.facebook.com.
        self.instagram_login = access_token.startswith("IG")
        host = GRAPH_HOST if self.instagram_login else FACEBOOK_GRAPH_HOST
        self._base = f"{host}/{version.strip('/')}" if version else host
        self._http = http or requests

    @property
    def refreshable(self) -> bool:
        """Solo los de Instagram caducan a los 60 días y se renuevan; los de
        usuario del sistema se generan sin caducidad."""
        return self.instagram_login

    # ── Llamadas ────────────────────────────────────────────────────────────

    def me(self) -> dict:
        """`user_id` (el que publica) y `username` de la cuenta del token."""
        return self._request("GET", f"{self._base}/me", params={"fields": "user_id,username"})

    def account_info(self, user_id: str) -> dict:
        """Usuario de una cuenta profesional conocida (`INSTAGRAM_USER_ID`)."""
        return self._request("GET", f"{self._base}/{user_id}", params={"fields": "id,username"})

    def create_image_container(self, user_id: str, image_url: str, caption: str) -> str:
        data = self._request(
            "POST", f"{self._base}/{user_id}/media", json={"image_url": image_url, "caption": caption}
        )
        return str(data["id"])

    def container_status(self, container_id: str) -> str:
        """FINISHED, IN_PROGRESS, ERROR, EXPIRED o PUBLISHED."""
        data = self._request("GET", f"{self._base}/{container_id}", params={"fields": "status_code"})
        return str(data.get("status_code") or "")

    def publish(self, user_id: str, container_id: str) -> str:
        data = self._request(
            "POST", f"{self._base}/{user_id}/media_publish", json={"creation_id": container_id}, unknown_on_timeout=True
        )
        return str(data["id"])

    def refresh_token(self) -> RefreshedToken:
        """Renueva el token de larga duración (60 días más). Exige que tenga al
        menos 24 h y que no haya caducado."""
        try:
            resp = self._http.get(
                f"{GRAPH_HOST}/refresh_access_token",
                params={"grant_type": "ig_refresh_token", "access_token": self._token},
                timeout=_TIMEOUT,
            )
        except requests.RequestException as exc:
            # Sin str(exc): incluiría la URL con el token.
            raise InstagramApiError(f"Sin respuesta al renovar el token ({type(exc).__name__})", transient=True) from None
        data = self._json(resp)
        return RefreshedToken(access_token=str(data["access_token"]), expires_in=data.get("expires_in"))

    # ── Internos ───────────────────────────────────────────────────────────

    def _request(self, method: str, url: str, *, params=None, json=None, unknown_on_timeout: bool = False) -> dict:
        try:
            resp = self._http.request(
                method, url, params=params, json=json, timeout=_TIMEOUT,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except (requests.ReadTimeout, requests.exceptions.ChunkedEncodingError) as exc:
            raise InstagramApiError(
                f"Instagram no respondió ({type(exc).__name__})", transient=not unknown_on_timeout, unknown=unknown_on_timeout
            ) from None
        except requests.RequestException as exc:
            raise InstagramApiError(f"Sin conexión con Instagram ({type(exc).__name__})", transient=True) from None
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
        transient = bool(error.get("is_transient")) or resp.status_code >= 500 or code in {1, 2, 4, 17, 32, 613}
        raise InstagramApiError(message, code=code if isinstance(code, int) else None, transient=transient)
