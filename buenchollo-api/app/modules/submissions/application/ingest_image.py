import asyncio
from collections.abc import Callable
from typing import Protocol

from app.modules.submissions.application.image_processing import process_image
from app.modules.submissions.domain.exceptions import InvalidImageError


class ImageSource(Protocol):
    async def fetch(self, url: str) -> bytes: ...


class ImageSink(Protocol):
    async def upload(self, user_id: str, data: bytes) -> str: ...


class IngestImageUseCase:
    def __init__(
        self, fetcher: ImageSource, storage: ImageSink, is_trusted_url: Callable[[str], bool]
    ) -> None:
        self._fetcher = fetcher
        self._storage = storage
        self._is_trusted_url = is_trusted_url

    async def from_bytes(self, user_id: str, data: bytes) -> tuple[str, int, int]:
        if not data:
            raise InvalidImageError()
        processed = await asyncio.to_thread(process_image, data)
        url = await self._storage.upload(user_id, processed.data)
        return url, processed.width, processed.height

    async def from_url(self, user_id: str, url: str) -> tuple[str, int, int]:
        if self._is_trusted_url(url):
            return url, 0, 0
        return await self.from_bytes(user_id, await self._fetcher.fetch(url))
