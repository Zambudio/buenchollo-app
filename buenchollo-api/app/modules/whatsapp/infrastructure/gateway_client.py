"""Cliente de la pasarela `whatsapp-gateway` (contenedor propio en el NAS, red
interna de Docker). La pasarela va vinculada a la cuenta que administra el
Canal; aquí solo se pregunta su estado y se le pide publicar.

El token va en la cabecera `Authorization`, nunca en la URL ni en los errores.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import requests

_TIMEOUT_STATUS = (5, 15)
# Subir la imagen y publicar; si se agota después de enviar, el resultado es desconocido.
_TIMEOUT_SEND = (5, 120)


class GatewayError(Exception):
    def __init__(self, message: str, *, status: int | None = None, unknown: bool = False, offline: bool = False):
        super().__init__(message)
        self.status = status
        # No se sabe si WhatsApp lo publicó (tiempo agotado tras enviar): no repetir.
        self.unknown = unknown
        # La pasarela no responde o WhatsApp no está vinculado: no cuenta como intento.
        self.offline = offline


@dataclass(frozen=True)
class GatewayStatus:
    connection: str
    me: str | None = None
    pairing_code: str | None = None
    last_error: str | None = None

    @property
    def connected(self) -> bool:
        return self.connection == "open"


class WhatsAppGatewayClient:
    def __init__(self, base_url: str, token: str, *, http=requests):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.http = http

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    @staticmethod
    def _error(response) -> GatewayError:
        try:
            detail = (response.json() or {}).get("error") or ""
        except ValueError:
            detail = ""
        status = response.status_code
        return GatewayError(
            f"Pasarela de WhatsApp: HTTP {status} {detail}".strip()[:300],
            status=status,
            # 503: WhatsApp no está vinculado. Un 500 es un fallo al publicar (cuenta como intento).
            offline=status == 503,
        )

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            response = self.http.get(
                f"{self.base_url}{path}", params=params, headers=self._headers(), timeout=_TIMEOUT_STATUS
            )
        except requests.RequestException as exc:
            raise GatewayError(f"La pasarela de WhatsApp no responde ({type(exc).__name__})", offline=True) from None
        if response.status_code != 200:
            raise self._error(response)
        return response.json() or {}

    def status(self) -> GatewayStatus:
        data = self._get("/status")
        return GatewayStatus(
            connection=str(data.get("connection") or "unknown"),
            me=data.get("me"),
            pairing_code=data.get("pairing_code"),
            last_error=data.get("last_error"),
        )

    def channel(self, *, jid: str | None = None, invite: str | None = None) -> dict:
        return self._get("/channel", {"jid": jid} if jid else {"invite": invite or ""})

    def send(self, jid: str, text: str, image: bytes | None = None, size: tuple[int, int] | None = None) -> str | None:
        body: dict = {"jid": jid, "text": text}
        if image:
            body["image_base64"] = base64.b64encode(image).decode("ascii")
            if size:
                body["width"], body["height"] = size
        try:
            response = self.http.post(
                f"{self.base_url}/send", json=body, headers=self._headers(), timeout=_TIMEOUT_SEND
            )
        except requests.ConnectTimeout:
            raise GatewayError("La pasarela de WhatsApp no responde (ConnectTimeout)", offline=True) from None
        except requests.Timeout:
            raise GatewayError("La pasarela no confirmó la publicación (tiempo agotado)", unknown=True) from None
        except requests.ConnectionError as exc:
            raise GatewayError(f"La pasarela de WhatsApp no responde ({type(exc).__name__})", offline=True) from None
        except requests.RequestException as exc:
            raise GatewayError(f"Fallo hablando con la pasarela ({type(exc).__name__})") from None
        if response.status_code != 200:
            raise self._error(response)
        return (response.json() or {}).get("id")
