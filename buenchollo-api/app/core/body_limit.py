"""Límite de tamaño de cuerpo por ruta (ASGI puro).

Starlette parsea todo el multipart (volcando a disco) antes de ejecutar
dependencias o handler, así que el límite debe aplicarse antes: por
`Content-Length` declarado y contando bytes en cuerpos chunked.
"""

import json
from collections.abc import Mapping

from starlette.types import ASGIApp, Message, Receive, Scope, Send

DEFAULT_DETAIL = "La imagen supera el máximo de 5 MB"


class _BodyTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, limits: Mapping[str, int], detail: str = DEFAULT_DETAIL) -> None:
        self.app = app
        self.limits = dict(limits)
        self.detail = detail

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit = self.limits.get(scope.get("path", "")) if scope["type"] == "http" else None
        if limit is None or scope.get("method") not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > limit:
            await self._reject(send)
            return

        received = 0
        started = False
        exceeded = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    raise _BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if exceeded:
                # FastAPI convierte el error de lectura en un 400: lo sustituimos por 413.
                if not started:
                    started = True
                    await self._reject(send)
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not started:
                started = True
                await self._reject(send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps({"detail": self.detail}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
