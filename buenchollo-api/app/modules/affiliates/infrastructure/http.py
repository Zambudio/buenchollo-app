"""HTTP saliente hacia las APIs de las redes de afiliación.

- Solo hosts de una allowlist fija y siempre https; cada redirección se valida
  y se limita su número (nunca IPs, hosts internos ni `file:`).
- Tiempo máximo por petición y tamaño máximo de respuesta / descarga.
- Reintentos acotados solo ante fallos transitorios (red, 5xx); un 429 no se
  reintenta: se informa como cuota agotada.
- Límite propio de llamadas por minuto (Awin publica 20/min por usuario).
- Ningún secreto sale en logs ni en mensajes de error (`redact`).
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import deque
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.exceptions import ServiceUnavailableError, TooManyRequestsError, ValidationError

logger = logging.getLogger(__name__)

MAX_REDIRECTS = 3
DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
MAX_JSON_BYTES = 5 * 1024 * 1024


class NetworkError(ServiceUnavailableError):
    """La red de afiliación no respondió correctamente."""


class NetworkRateLimited(TooManyRequestsError):
    """Cuota de la API de la red agotada (propia o informada por la red)."""


class NetworkAuthError(ServiceUnavailableError):
    """Credenciales rechazadas por la red (401/403)."""


class NetworkHostNotAllowed(ValidationError):
    """Destino fuera de la allowlist de la integración."""


_SECRET_PATTERNS = (
    re.compile(r"(apikey/)[^/?#\s]+", re.I),
    re.compile(r"(accessToken=|token=|api_key=|apikey=)[^&#\s]+", re.I),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.I),
    re.compile(r"(/publisher/\d+/)[^/\s]+(/)", re.I),
)


def redact(text: str, secrets: Iterable[str] = ()) -> str:
    """Quita claves y tokens de URLs/mensajes antes de loguear o devolver."""
    out = str(text or "")
    for secret in secrets:
        if secret and len(secret) >= 6:
            out = out.replace(secret, "***")
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(lambda m: m.group(1) + "***" + (m.group(2) if m.lastindex and m.lastindex >= 2 else ""), out)
    return out[:300]


class MinuteRateLimiter:
    """Ventana deslizante de 60 s compartida por el proceso. No espera: si no
    hay hueco lanza `NetworkRateLimited` para que el editor muestre el estado."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = max(1, per_minute)
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        now = time.monotonic()
        with self._lock:
            while self._calls and now - self._calls[0] >= 60:
                self._calls.popleft()
            if len(self._calls) >= self.per_minute:
                raise NetworkRateLimited("Límite de llamadas por minuto de la red alcanzado. Reinténtalo en un minuto.")
            self._calls.append(now)


class SafeHttp:
    def __init__(
        self,
        allowed_hosts: frozenset[str],
        *,
        secrets: Iterable[str] = (),
        limiter: MinuteRateLimiter | None = None,
        transport: httpx.BaseTransport | None = None,
        retries: int = 2,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.allowed_hosts = allowed_hosts
        self.secrets = tuple(s for s in secrets if s)
        self.limiter = limiter
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self._client = httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=False,
            transport=transport,
            headers={"User-Agent": "BuenCholloTech-affiliates/1.0"},
            trust_env=False,
        )

    def _check(self, url: str) -> None:
        parts = urlsplit(url)
        if parts.scheme != "https" or (parts.hostname or "").lower() not in self.allowed_hosts or parts.port not in (None, 443):
            raise NetworkHostNotAllowed("Destino no permitido para la integración de afiliación.")
        if parts.username or parts.password:
            raise NetworkHostNotAllowed("Destino no permitido para la integración de afiliación.")

    def _send(self, method: str, url: str, *, stream: bool = False, **kwargs) -> httpx.Response:
        attempt = 0
        while True:
            attempt += 1
            current = url
            try:
                for _ in range(MAX_REDIRECTS + 1):
                    self._check(current)
                    if self.limiter:
                        self.limiter.acquire()
                    request = self._client.build_request(method, current, **kwargs)
                    response = self._client.send(request, stream=stream)
                    if response.is_redirect:
                        location = response.headers.get("location", "")
                        response.close()
                        current = urljoin(current, location)
                        method = "GET" if method == "POST" and response.status_code in (301, 302, 303) else method
                        continue
                    break
                else:
                    raise NetworkError("Demasiadas redirecciones en la respuesta de la red.")
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                logger.warning("Fallo de red con %s: %s", urlsplit(url).hostname, redact(str(exc), self.secrets))
                if attempt <= self.retries:
                    time.sleep(self.backoff_seconds * attempt)
                    continue
                raise NetworkError("La red de afiliación no responde. Reinténtalo más tarde.") from None

            status = response.status_code
            if status == 429:
                response.close()
                raise NetworkRateLimited("La red de afiliación indica cuota agotada (429). Reinténtalo más tarde.")
            if status in (401, 403):
                response.close()
                raise NetworkAuthError("La red ha rechazado las credenciales configuradas (revisa el token).")
            if status >= 500 and attempt <= self.retries:
                response.close()
                time.sleep(self.backoff_seconds * attempt)
                continue
            return response

    def json(self, method: str, url: str, **kwargs):
        response = self._send(method, url, **kwargs)
        try:
            body = response.content
            if len(body) > MAX_JSON_BYTES:
                raise NetworkError("Respuesta de la red demasiado grande.")
            if response.status_code >= 400:
                logger.warning(
                    "Red %s respondió %s: %s",
                    urlsplit(url).hostname,
                    response.status_code,
                    redact(body[:300].decode("utf-8", "replace"), self.secrets),
                )
                return response.status_code, _safe_json(body)
            return response.status_code, _safe_json(body)
        finally:
            response.close()

    def text(self, url: str, max_bytes: int = MAX_JSON_BYTES) -> tuple[int, str]:
        response = self._send("GET", url, stream=True)
        try:
            chunks, total = [], 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise NetworkError("Respuesta de la red demasiado grande.")
                chunks.append(chunk)
            return response.status_code, b"".join(chunks).decode("utf-8-sig", "replace")
        finally:
            response.close()

    def download(self, url: str, dest: Path, max_bytes: int) -> int:
        """Descarga en streaming a disco cortando al superar `max_bytes`."""
        response = self._send("GET", url, stream=True)
        try:
            if response.status_code >= 400:
                raise NetworkError(f"La red respondió {response.status_code} al descargar el feed.")
            total = 0
            with dest.open("wb") as fh:
                for chunk in response.iter_bytes(chunk_size=256 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise NetworkError("El feed supera el tamaño máximo de descarga configurado.")
                    fh.write(chunk)
            return total
        finally:
            response.close()

    def close(self) -> None:
        self._client.close()


def _safe_json(body: bytes):
    import json

    try:
        return json.loads(body.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return None
