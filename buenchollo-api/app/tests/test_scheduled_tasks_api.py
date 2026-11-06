"""Tests de integración del panel de tareas programadas. Requieren
PostgreSQL real (excluidos del CI con -m "not integration")."""
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from app.core.security import require_admin
from app.main import app
from app.modules.catalog.infrastructure.repository import CatalogRepository
from app.modules.products.domain.entities import ProductPreview

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
    # (Task 7) — este test no toca `enabled` deliberadamente (ver finding 5
    # de la revisión final): con la tarea real activada, el job horario del
    # contenedor `buenchollo-scheduler` podría, en teoría, observar
    # enabled=True mientras dure el test y disparar una ejecución automática
    # real. Solo se prueban frequency_preset/run_hour/config, que no tienen
    # ese riesgo; se capturan y restauran igual que antes.
    original = integration_client.get("/v1/admin/scheduled-tasks").json()
    original_task = next(t for t in original if t["id"] == task_id)

    try:
        response = integration_client.put(
            f"/v1/admin/scheduled-tasks/{task_id}",
            json={"frequency_preset": "daily", "run_hour": 6, "config": {"price_tolerance_percent": 15}},
        )

        assert response.status_code == 200, response.text
        updated = response.json()
        assert updated["frequency_preset"] == "daily"
        assert updated["run_hour"] == 6
        assert updated["config"]["price_tolerance_percent"] == 15
    finally:
        integration_client.put(
            f"/v1/admin/scheduled-tasks/{task_id}",
            json={
                "frequency_preset": original_task["frequency_preset"],
                "run_hour": original_task["run_hour"],
                "config": original_task["config"],
            },
        )


def test_preview_sin_candidatos_devuelve_lista_vacia(integration_client):
    task_id = _get_price_check_task_id(integration_client)

    with _only_listing("B0NOEXIST0", None):
        response = integration_client.post(f"/v1/admin/scheduled-tasks/{task_id}/preview")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidates"] == []


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


@contextmanager
def _only_listing(asin: str, product: ProductPreview | None):
    """Limita la revisión al listing del chollo de prueba y simula la respuesta
    de Amazon: `confirm` revisa TODO el catálogo y sin esto tocaría los
    chollos reales de la BD."""
    original = CatalogRepository.get_checkable

    async def _filtered(self):
        return [(listing, deal) for listing, deal in await original(self) if listing.external_id == asin]

    with patch.object(CatalogRepository, "get_checkable", _filtered), patch(
        "app.modules.scheduled_tasks.application.factory.AmazonProductClient"
    ) as client_cls:
        client_cls.return_value.get_product_previews.side_effect = lambda asins: {
            a: (product if a == asin else None) for a in asins
        }
        yield


def _run_price_increase(client, task_id: str, deal: dict) -> dict:
    product = ProductPreview(current_price=deal["current_price"] + 20, in_stock=True)
    with _only_listing(deal["external_id"], product):
        resp = client.post(f"/v1/admin/scheduled-tasks/{task_id}/confirm")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_confirm_termina_la_oferta_sin_borrar_el_deal(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0TESTPRC1")
    try:
        run = _run_price_increase(integration_client, task_id, deal)
        assert run["trigger_type"] == "manual"
        assert run["total_checked"] == 1
        assert run["total_affected"] == 1

        detail = integration_client.get(f"/v1/deals/{deal['slug']}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["status"] == "expired"
        assert body["offer_end_reason"] == "price_increase"
        assert body["current_price"] == deal["current_price"] + 20
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_confirm_reactiva_y_el_registro_lo_indica(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0TESTRCT1")
    try:
        _run_price_increase(integration_client, task_id, deal)
        back = ProductPreview(current_price=deal["current_price"], in_stock=True)
        with _only_listing(deal["external_id"], back):
            resp = integration_client.post(f"/v1/admin/scheduled-tasks/{task_id}/confirm")
        assert resp.status_code == 200, resp.text

        detail = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{resp.json()['id']}").json()
        assert [(i["transition"], i["reason"]) for i in detail["items"]] == [("reactivated", "deal_again")]
        assert integration_client.get(f"/v1/deals/{deal['slug']}").json()["status"] == "active"
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_list_runs_devuelve_el_run_recien_creado(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RUNLST01")
    try:
        run = _run_price_increase(integration_client, task_id, deal)

        resp = integration_client.get(f"/v1/admin/scheduled-tasks/{task_id}/runs")

        assert resp.status_code == 200, resp.text
        assert run["id"] in [r["id"] for r in resp.json()]
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_get_run_detail_incluye_los_items(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RUNDETL1")
    try:
        run = _run_price_increase(integration_client, task_id, deal)

        resp = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}")

        assert resp.status_code == 200, resp.text
        detail = resp.json()
        assert len(detail["items"]) == 1
        assert detail["items"][0]["deal_id_snapshot"] == deal["id"]
        assert detail["items"][0]["transition"] == "offer_ended"
        assert "restored_at" not in detail["items"][0]
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_el_endpoint_de_restaurar_ya_no_existe(integration_client):
    resp = integration_client.post("/v1/admin/scheduled-tasks/runs/items/cualquiera/restore")
    assert resp.status_code in (404, 405)


def test_update_rechaza_config_fuera_de_rango(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    resp = integration_client.put(
        f"/v1/admin/scheduled-tasks/{task_id}", json={"config": {"purge_after_days": 2}}
    )
    assert resp.status_code == 422


def test_delete_run_lo_elimina(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0DELRUN01")
    try:
        run = _run_price_increase(integration_client, task_id, deal)

        resp = integration_client.delete(f"/v1/admin/scheduled-tasks/runs/{run['id']}")
        assert resp.status_code == 204

        detail_resp = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}")
        assert detail_resp.status_code == 404
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_bulk_delete_runs_borra_varios(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal_a = _create_deal(integration_client, asin="B0BULK0001")
    deal_b = _create_deal(integration_client, asin="B0BULK0002")
    try:
        run_a = _run_price_increase(integration_client, task_id, deal_a)
        run_b = _run_price_increase(integration_client, task_id, deal_b)

        resp = integration_client.post(
            "/v1/admin/scheduled-tasks/runs/bulk-delete",
            json={"run_ids": [run_a["id"], run_b["id"]]},
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["deleted"] == 2

        assert integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run_a['id']}").status_code == 404
        assert integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run_b['id']}").status_code == 404
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal_a['id']}")
        integration_client.delete(f"/v1/deals/admin/{deal_b['id']}")
