import asyncio
import re
from urllib.parse import urljoin, urlparse

import httpx

from app.core.ssrf import resolves_to_private_ip
from app.modules.submissions.application.image_processing import MAX_IMAGE_BYTES
from app.modules.submissions.domain.exceptions import InvalidImageError

MAX_REDIRECTS = 3
TIMEOUT_SECONDS = 10
TOTAL_DEADLINE_SECONDS = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_UNSAFE_CHARS = re.compile(r"[\\\s\x00-\x1f\x7f]")


def _is_fetchable(url: str) -> bool:
    if _UNSAFE_CHARS.search(url) or len(url) > 2048:
        return False
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    return port in (None, 80, 443)


class ImageFetcher:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        deadline: float = TOTAL_DEADLINE_SECONDS,
    ) -> None:
        self._transport = transport
        self._deadline = deadline

    async def _validate(self, url: str) -> None:
        if not _is_fetchable(url) or await asyncio.to_thread(resolves_to_private_ip, url):
            raise InvalidImageError("No se puede descargar la imagen de esa dirección")

    async def fetch(self, url: str) -> bytes:
        try:
            async with asyncio.timeout(self._deadline):
                return await self._fetch(url)
        except TimeoutError as exc:
            raise InvalidImageError("La descarga de la imagen ha tardado demasiado") from exc

    async def _fetch(self, url: str) -> bytes:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT, "Accept": "image/*", "Accept-Encoding": "identity"},
            transport=self._transport,
        ) as client:
            current = url
            for _ in range(MAX_REDIRECTS + 1):
                await self._validate(current)
                try:
                    async with client.stream("GET", current) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                raise InvalidImageError("No se pudo descargar la imagen")
                            current = urljoin(current, location)
                            continue
                        if response.headers.get("content-encoding", "identity").lower() != "identity":
                            raise InvalidImageError("No se pudo descargar la imagen")
                        if response.status_code != 200:
                            raise InvalidImageError("No se pudo descargar la imagen")
                        return await self._read_limited(response)
                except httpx.HTTPError as exc:
                    raise InvalidImageError("No se pudo descargar la imagen") from exc
            raise InvalidImageError("No se pudo descargar la imagen")

    @staticmethod
    async def _read_limited(response: httpx.Response) -> bytes:
        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > MAX_IMAGE_BYTES:
            raise InvalidImageError("La imagen supera el máximo de 5 MB")
        buffer = bytearray()
        async for chunk in response.aiter_bytes():
            buffer.extend(chunk)
            if len(buffer) > MAX_IMAGE_BYTES:
                raise InvalidImageError("La imagen supera el máximo de 5 MB")
        return bytes(buffer)
