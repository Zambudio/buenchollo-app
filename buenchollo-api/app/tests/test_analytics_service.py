from dataclasses import dataclass

import pytest

from app.modules.analytics.application.service import AnalyticsService, TrackPageViewCommand


@dataclass
class _RecordedEvent:
    visitor_hash: str
    session_hash: str
    path: str
    source: str


class _FakeAnalyticsRepository:
    def __init__(self) -> None:
        self.events: list[_RecordedEvent] = []

    async def record_page_view(self, event):
        self.events.append(
            _RecordedEvent(
                visitor_hash=event.visitor_hash,
                session_hash=event.session_hash,
                path=event.path,
                source=event.source,
            )
        )
        return 42

    async def delete_expired(self, retention_months: int) -> None:
        return None


def _command(**overrides) -> TrackPageViewCommand:
    values = {
        "visitor_id": "visitor-123",
        "session_id": "session-456",
        "path": "/blog/guia-portatiles",
        "source": "telegram",
        "source_detail": "telegram",
        "medium": "social",
        "campaign": "canal",
        "referrer_host": None,
        "user_agent": "Mozilla/5.0 Firefox/142.0",
    }
    values.update(overrides)
    return TrackPageViewCommand(**values)


@pytest.mark.asyncio
async def test_track_page_view_pseudonymizes_client_identifiers_before_persistence():
    repo = _FakeAnalyticsRepository()
    service = AnalyticsService(repo, hash_secret="test-secret", retention_months=25)

    result = await service.track_page_view(_command())

    assert result.accepted is True
    assert result.blog_view_count == 42
    assert len(repo.events) == 1
    event = repo.events[0]
    assert event.visitor_hash == "6ada455511a262d1782d3868059bd45e1d3f6837f3fd5c9e0e217548cdbac9cc"
    assert event.session_hash == "7f0a309fae850e064c126168af4a14576730c1e7ac00dcd77c82bbff0f4aae18"
    assert event.path == "/blog/guia-portatiles"
    assert event.source == "telegram"


@pytest.mark.asyncio
async def test_track_page_view_discards_known_bots_without_persisting():
    repo = _FakeAnalyticsRepository()
    service = AnalyticsService(repo, hash_secret="test-secret", retention_months=25)

    result = await service.track_page_view(_command(user_agent="Googlebot/2.1"))

    assert result.accepted is False
    assert result.blog_view_count is None
    assert repo.events == []


@pytest.mark.asyncio
async def test_track_page_view_requires_a_private_hash_secret():
    repo = _FakeAnalyticsRepository()

    with pytest.raises(ValueError, match="ANALYTICS_HASH_SECRET"):
        AnalyticsService(repo, hash_secret="", retention_months=25)
