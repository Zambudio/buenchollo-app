from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
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


def test_mis_votos_exige_sesion_deduplica_y_limita_la_consulta():
    from app.modules.catalog.api.router import MAX_VOTE_LOOKUP, get_top_service

    service = SimpleNamespace(my_votes=AsyncMock(return_value=[]))
    app.dependency_overrides[get_top_service] = lambda: service
    product_id = "2a4eb5e7-91c7-4b4d-8ce4-b6c366364eef"
    many = [f"00000000-0000-4000-8000-{index:012d}" for index in range(MAX_VOTE_LOOKUP + 5)]
    try:
        with TestClient(app) as client:
            assert client.get(f"/v1/catalog/my-votes?product_ids={product_id}").status_code in (401, 403)
            app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="u-1")
            response = client.get(f"/v1/catalog/my-votes?product_ids={product_id}&product_ids={product_id}")
            assert response.status_code == 200
            service.my_votes.assert_awaited_with([product_id], "u-1")
            client.get("/v1/catalog/my-votes?" + "&".join(f"product_ids={item}" for item in many))
            assert len(service.my_votes.await_args.args[0]) == MAX_VOTE_LOOKUP
    finally:
        app.dependency_overrides.pop(get_top_service, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_votar_un_producto_no_publico_devuelve_404():
    from app.modules.catalog.application.top_service import TopService
    from app.modules.catalog.domain.exceptions import ProductNotFound

    repo = SimpleNamespace(product_exists=AsyncMock(return_value=False), toggle_vote=AsyncMock())
    with pytest.raises(ProductNotFound):
        await TopService(repo).toggle_vote("p-1", "u-1")
    repo.toggle_vote.assert_not_awaited()
