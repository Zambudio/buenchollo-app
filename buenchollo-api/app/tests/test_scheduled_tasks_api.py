"""Tests de integración del panel de tareas programadas. Requieren
PostgreSQL real (excluidos del CI con -m "not integration")."""
from unittest.mock import patch

import pytest

from app.core.security import require_admin
from app.main import app

pytestmark = pytest.mark.integration


class MockUser:
    id = "dbe6e006-4f3e-4be8-8351-7e264ed3acb6"


async def mock_require_admin():
    return MockUser()


@pytest.fixture(autouse=True)
def override_admin():
    app.dependency_overrides[require_admin] = mock_require_admin
    yield
    app.dependency_overrides.clear()


def _get_price_check_task_id(client) -> str:
    response = client.get("/v1/admin/scheduled-tasks")
    assert response.status_code == 200, response.text
    tasks = response.json()
    price_check = next(t for t in tasks if t["task_type"] == "price_check")
    return price_check["id"]


def test_list_scheduled_tasks_incluye_price_check_seed(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    assert task_id


def test_update_scheduled_task_cambia_config(integration_client):
    task_id = _get_price_check_task_id(integration_client)

    response = integration_client.put(
        f"/v1/admin/scheduled-tasks/{task_id}",
        json={"enabled": True, "frequency_preset": "daily", "run_hour": 6, "config": {"price_tolerance_percent": 15}},
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["enabled"] is True
    assert updated["frequency_preset"] == "daily"
    assert updated["run_hour"] == 6
    assert updated["config"]["price_tolerance_percent"] == 15


def test_preview_sin_candidatos_devuelve_lista_vacia(integration_client):
    task_id = _get_price_check_task_id(integration_client)

    with patch(
        "app.modules.scheduled_tasks.api.router.AmazonProductClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.get_product_preview.return_value = None
        response = integration_client.post(f"/v1/admin/scheduled-tasks/{task_id}/preview")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidates"] == []


def test_confirm_borra_el_deal_y_crea_el_registro(integration_client):
    task_id = _get_price_check_task_id(integration_client)

    create_resp = integration_client.post(
        "/v1/deals/admin",
        json={
            "title": "Auriculares Test Price Check",
            "current_price": 50.0,
            "affiliate_url": "https://amazon.es/dp/B0TESTPRICE",
            "external_id": "B0TESTPRICE",
            "status": "active",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    deal = create_resp.json()

    confirm_payload = {
        "total_checked": 1,
        "candidates": [
            {
                "deal_id": deal["id"],
                "title": deal["title"],
                "slug": deal["slug"],
                "image_url": None,
                "description": None,
                "store_id": None,
                "store_name": None,
                "category_id": None,
                "subcategory_id": None,
                "external_id": "B0TESTPRICE",
                "affiliate_url": deal["affiliate_url"],
                "source_url": None,
                "old_price": 50.0,
                "new_price": 65.0,
                "reason": "price_increase",
            }
        ],
    }
    response = integration_client.post(
        f"/v1/admin/scheduled-tasks/{task_id}/confirm", json=confirm_payload
    )

    assert response.status_code == 200, response.text
    run = response.json()
    assert run["trigger_type"] == "manual"
    assert run["total_affected"] == 1

    get_deal_resp = integration_client.get(f"/v1/deals/{deal['slug']}")
    assert get_deal_resp.status_code == 404
