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
    # `price_check` es una fila real única compartida (no hay BD de test
    # separada, ver task-8-report.md) y ya está enganchada al scheduler real
    # (Task 7) — este test no puede dejarla habilitada tras ejecutarse, así
    # que capturamos su estado original y lo restauramos siempre, incluso si
    # una aserción falla a mitad de camino.
    original = integration_client.get("/v1/admin/scheduled-tasks").json()
    original_task = next(t for t in original if t["id"] == task_id)

    try:
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
    finally:
        integration_client.put(
            f"/v1/admin/scheduled-tasks/{task_id}",
            json={
                "enabled": original_task["enabled"],
                "frequency_preset": original_task["frequency_preset"],
                "run_hour": original_task["run_hour"],
                "config": original_task["config"],
            },
        )


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


def _create_deal(client, *, asin: str, price: float = 50.0) -> dict:
    resp = client.post(
        "/v1/deals/admin",
        json={
            "title": f"Producto {asin}",
            "current_price": price,
            "affiliate_url": f"https://amazon.es/dp/{asin}",
            "external_id": asin,
            "status": "active",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _confirm_deletion(client, task_id: str, deal: dict, *, reason: str = "price_increase") -> dict:
    payload = {
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
                "external_id": deal["external_id"],
                "affiliate_url": deal["affiliate_url"],
                "source_url": None,
                "old_price": deal["current_price"],
                "new_price": deal["current_price"] + 20,
                "reason": reason,
            }
        ],
    }
    resp = client.post(f"/v1/admin/scheduled-tasks/{task_id}/confirm", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_list_runs_devuelve_el_run_recien_creado(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RUNLIST01")
    run = _confirm_deletion(integration_client, task_id, deal)

    resp = integration_client.get(f"/v1/admin/scheduled-tasks/{task_id}/runs")

    assert resp.status_code == 200, resp.text
    run_ids = [r["id"] for r in resp.json()]
    assert run["id"] in run_ids


def test_get_run_detail_incluye_los_items(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RUNDETAIL1")
    run = _confirm_deletion(integration_client, task_id, deal)

    resp = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}")

    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert len(detail["items"]) == 1
    assert detail["items"][0]["deal_id_snapshot"] == deal["id"]
    assert detail["items"][0]["restored_at"] is None


def test_restore_item_recrea_el_deal_activo(integration_client):
    # `confirm` borra el deal original; `restore` crea uno NUEVO, activo y
    # permanente (visible en buenchollotech.com). No hay BD de test separada
    # (ver task-8-report.md / task-9-brief.md), así que hay que borrarlo
    # explícitamente al terminar, incluso si una aserción posterior falla.
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RESTORE001")
    run = _confirm_deletion(integration_client, task_id, deal)
    detail = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}").json()
    item_id = detail["items"][0]["id"]

    resp = integration_client.post(f"/v1/admin/scheduled-tasks/runs/items/{item_id}/restore")

    assert resp.status_code == 200, resp.text
    restored = resp.json()
    try:
        assert restored["status"] == "active"
        assert restored["external_id"] == "B0RESTORE001"

        detail_after = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}").json()
        assert detail_after["items"][0]["restored_at"] is not None
    finally:
        integration_client.delete(f"/v1/deals/admin/{restored['id']}")


def test_restore_item_ya_restaurado_devuelve_409(integration_client):
    # La primera llamada a /restore SÍ crea un deal activo permanente (igual
    # que en test_restore_item_recrea_el_deal_activo) aunque el objetivo del
    # test sea la segunda llamada (409) — hay que limpiar el deal restaurado
    # en la primera, no solo comprobar el 409 de la segunda.
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RESTORE002")
    run = _confirm_deletion(integration_client, task_id, deal)
    detail = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}").json()
    item_id = detail["items"][0]["id"]
    first_restore = integration_client.post(f"/v1/admin/scheduled-tasks/runs/items/{item_id}/restore")
    assert first_restore.status_code == 200, first_restore.text
    restored = first_restore.json()

    try:
        resp = integration_client.post(f"/v1/admin/scheduled-tasks/runs/items/{item_id}/restore")

        assert resp.status_code == 409
    finally:
        integration_client.delete(f"/v1/deals/admin/{restored['id']}")


def test_delete_run_lo_elimina(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0DELETERUN1")
    run = _confirm_deletion(integration_client, task_id, deal)

    resp = integration_client.delete(f"/v1/admin/scheduled-tasks/runs/{run['id']}")
    assert resp.status_code == 204

    detail_resp = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}")
    assert detail_resp.status_code == 404


def test_bulk_delete_runs_borra_varios(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal_a = _create_deal(integration_client, asin="B0BULK000001")
    deal_b = _create_deal(integration_client, asin="B0BULK000002")
    run_a = _confirm_deletion(integration_client, task_id, deal_a)
    run_b = _confirm_deletion(integration_client, task_id, deal_b)

    resp = integration_client.post(
        "/v1/admin/scheduled-tasks/runs/bulk-delete",
        json={"run_ids": [run_a["id"], run_b["id"]]},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["deleted"] == 2
