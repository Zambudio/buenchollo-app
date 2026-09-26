from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Protocol


_BOT_PATTERN = re.compile(
    r"bot|crawler|spider|slurp|bingpreview|facebookexternalhit|telegrambot|whatsapp",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TrackPageViewCommand:
    visitor_id: str
    session_id: str
    path: str
    source: str
    source_detail: str
    medium: str
    campaign: str | None
    referrer_host: str | None
    user_agent: str


@dataclass(frozen=True)
class PageViewEvent:
    visitor_hash: str
    session_hash: str
    path: str
    source: str
    source_detail: str
    medium: str
    campaign: str | None
    referrer_host: str | None


@dataclass(frozen=True)
class TrackPageViewResult:
    accepted: bool
    blog_view_count: int | None = None


class AnalyticsRepositoryPort(Protocol):
    async def record_page_view(self, event: PageViewEvent) -> int | None: ...

    async def delete_expired(self, retention_months: int) -> None: ...

    async def get_overview(self, days: int) -> dict: ...


def _pseudonymize(value: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


class AnalyticsService:
    def __init__(
        self,
        repository: AnalyticsRepositoryPort,
        *,
        hash_secret: str,
        retention_months: int,
    ) -> None:
        if not hash_secret:
            raise ValueError("ANALYTICS_HASH_SECRET debe estar configurado")
        self.repository = repository
        self.hash_secret = hash_secret
        self.retention_months = retention_months

    async def track_page_view(self, command: TrackPageViewCommand) -> TrackPageViewResult:
        if not command.user_agent or _BOT_PATTERN.search(command.user_agent):
            return TrackPageViewResult(accepted=False)

        event = PageViewEvent(
            visitor_hash=_pseudonymize(command.visitor_id, self.hash_secret),
            session_hash=_pseudonymize(command.session_id, self.hash_secret),
            path=command.path,
            source=command.source,
            source_detail=command.source_detail,
            medium=command.medium,
            campaign=command.campaign,
            referrer_host=command.referrer_host,
        )
        blog_view_count = await self.repository.record_page_view(event)
        return TrackPageViewResult(accepted=True, blog_view_count=blog_view_count)

    async def get_overview(self, days: int) -> dict:
        await self.repository.delete_expired(self.retention_months)
        return await self.repository.get_overview(days)
