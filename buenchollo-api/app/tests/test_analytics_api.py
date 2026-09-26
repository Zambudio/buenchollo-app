from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app


async def _no_database():
    yield None


def _analytics_settings():
    return SimpleNamespace(
        effective_analytics_hash_secret="test-secret",
        analytics_retention_months=25,
    )


def test_page_view_endpoint_discards_bot_event_without_touching_database():
    app.dependency_overrides[get_db] = _no_database
    app.dependency_overrides[get_settings] = _analytics_settings
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/analytics/events",
                headers={"User-Agent": "Googlebot/2.1"},
                json={
                    "visitor_id": "b1f52fb5-6ac2-472c-a443-ac2bfa1a4fe6",
                    "session_id": "3b52f346-e770-479d-8538-9f2f0fbe10b3",
                    "path": "/blog/guia-portatiles",
                    "source": "telegram",
                    "source_detail": "telegram",
                    "medium": "social",
                    "campaign": "canal",
                    "referrer_host": None,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {"accepted": False, "blog_view_count": None}
