from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.security import AuthenticatedUser, get_current_user
from app.main import app


def test_top_products_publico_y_voto_autenticado():
    from app.modules.catalog.api.router import get_top_service

    product = {
        "id": "2a4eb5e7-91c7-4b4d-8ce4-b6c366364eef",
        "title": "Monitor 4K",
        "image_url": None,
        "deal_slug": "monitor-4k",
        "vote_count": 3,
        "position": 1,
    }
    service = SimpleNamespace(
        list_top=AsyncMock(return_value=[product]),
        toggle_vote=AsyncMock(return_value=True),
    )
    app.dependency_overrides[get_top_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.get("/v1/catalog/tops/monitores")
            assert response.status_code == 200
            assert response.json()[0]["vote_count"] == 3
            assert response.json()[0]["position"] == 1
            response = client.post(f"/v1/catalog/products/{product['id']}/vote")
            assert response.status_code in (401, 403)
            app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
                id="9e6e4807-cd1a-4fc7-bdf2-10b8d34cb5ef"
            )
            response = client.post(f"/v1/catalog/products/{product['id']}/vote")
            assert response.status_code == 200
            assert response.json() == {"voted": True}
    finally:
        app.dependency_overrides.pop(get_top_service, None)
        app.dependency_overrides.pop(get_current_user, None)
