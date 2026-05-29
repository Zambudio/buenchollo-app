"""Tests de integración para el CRUD de chollos (deals)."""
import uuid
import pytest
from app.main import app
from app.core.security import require_admin


class MockUser:
    id = "dbe6e006-4f3e-4be8-8351-7e264ed3acb6"


async def mock_require_admin():
    return MockUser()


@pytest.fixture(autouse=True)
def override_admin():
    app.dependency_overrides[require_admin] = mock_require_admin
    yield
    app.dependency_overrides.clear()


def test_create_update_delete_deal_flow(integration_client):
    unique_id = str(uuid.uuid4())[:8]

    # 1. Crear
    payload = {
        "title": "API Test Deal - Antigravity",
        "slug": f"api-test-deal-antigravity-{unique_id}",
        "description": "Descripcion de prueba por la API",
        "short_description": "API Test",
        "current_price": 49.99,
        "previous_price": 99.99,
        "discount_percentage": 50,
        "affiliate_url": "https://amazon.es/dp/B000000001",
        "status": "active",
        "source": "manual",
        "brand": "API Brand",
        "shipping_info": "Envio gratis",
    }
    response = integration_client.post("/v1/deals/admin", json=payload)
    assert response.status_code == 200, response.text
    deal = response.json()
    assert deal["title"] == "API Test Deal - Antigravity"
    deal_id = deal["id"]

    # 2. Actualizar
    update_response = integration_client.put(
        f"/v1/deals/admin/{deal_id}",
        json={"title": "API Test Deal - Updated", "current_price": 39.99},
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["title"] == "API Test Deal - Updated"
    assert updated["current_price"] == 39.99

    # 3. Borrar
    delete_response = integration_client.delete(f"/v1/deals/admin/{deal_id}")
    assert delete_response.status_code == 204, delete_response.text
