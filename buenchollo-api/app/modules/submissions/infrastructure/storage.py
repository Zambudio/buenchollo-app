import asyncio
import logging
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from app.modules.submissions.domain.exceptions import ImageStorageUnavailableError

logger = logging.getLogger(__name__)

BUCKET = "deal-images"


class SubmissionImageStorage:
    def __init__(self, client_factory: Callable[[], Any], supabase_url: str) -> None:
        self._client_factory = client_factory
        self._base_url = supabase_url.split("/rest/v1")[0].rstrip("/")

    def public_url(self, path: str) -> str:
        return f"{self._base_url}/storage/v1/object/public/{BUCKET}/{path}"

    def _upload_sync(self, path: str, data: bytes) -> None:
        self._client_factory().storage.from_(BUCKET).upload(
            path,
            data,
            {"content-type": "image/webp", "cache-control": "31536000", "upsert": "false"},
        )

    async def upload(self, user_id: str, data: bytes) -> str:
        path = f"submissions/{user_id}/{uuid4()}.webp"
        try:
            await asyncio.to_thread(self._upload_sync, path, data)
        except Exception as exc:
            logger.exception("Fallo al subir imagen de propuesta a Storage")
            raise ImageStorageUnavailableError() from exc
        return self.public_url(path)
