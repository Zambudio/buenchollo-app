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

    with patch(
        "app.modules.scheduled_tasks.api.router.AmazonProductClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.get_product_previews.side_effect = (
            lambda asins: {asin: None for asin in asins}
        )
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

    # Si cualquier aserción entre la creación y la confirmación de borrado
    # falla, el deal de prueba se quedaría publicado permanentemente en
    # producción (y su ASIN, con índice único, rompería el siguiente run de
    # la suite) — best-effort cleanup en `finally` (ver finding 4).
    try:
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
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


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
    # Best-effort cleanup si algo falla entre crear el deal y confirmar su
    # borrado (ver finding 4): sin esto, un assert que reviente a mitad de
    # camino deja el deal huérfano y activo en producción.
    try:
        run = _confirm_deletion(integration_client, task_id, deal)

        resp = integration_client.get(f"/v1/admin/scheduled-tasks/{task_id}/runs")

        assert resp.status_code == 200, resp.text
        run_ids = [r["id"] for r in resp.json()]
        assert run["id"] in run_ids
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_get_run_detail_incluye_los_items(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RUNDETAIL1")
    try:
        run = _confirm_deletion(integration_client, task_id, deal)

        resp = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}")

        assert resp.status_code == 200, resp.text
        detail = resp.json()
        assert len(detail["items"]) == 1
        assert detail["items"][0]["deal_id_snapshot"] == deal["id"]
        assert detail["items"][0]["restored_at"] is None
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_restore_item_recrea_el_deal_activo(integration_client):
    # `confirm` borra el deal original; `restore` crea uno NUEVO, activo y
    # permanente (visible en buenchollotech.com). No hay BD de test separada
    # (ver task-8-report.md / task-9-brief.md), así que hay que borrarlo
    # explícitamente al terminar, incluso si una aserción posterior falla.
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RESTORE001")
    # Envuelve TODO el cuerpo (no solo el bloque de /restore de más abajo):
    # si `_confirm_deletion` lanza antes de llegar a crear el restaurado, el
    # deal original de `_create_deal` también quedaría huérfano (finding 4).
    try:
        run = _confirm_deletion(integration_client, task_id, deal)
        detail = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}").json()
        item_id = detail["items"][0]["id"]

        # El id se captura DENTRO del try, junto con la propia llamada a
        # /restore y su aserción de status — si cualquiera de ellas lanza
        # después de que el deal ya se haya persistido, el finally debe seguir
        # pudiendo limpiarlo. Se inicializa a None por si /restore ni siquiera
        # llega a devolver un 200.
        restored_id = None
        try:
            resp = integration_client.post(f"/v1/admin/scheduled-tasks/runs/items/{item_id}/restore")
            assert resp.status_code == 200, resp.text
            restored = resp.json()
            restored_id = restored["id"]
            assert restored["status"] == "active"
            assert restored["external_id"] == "B0RESTORE001"

            detail_after = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}").json()
            assert detail_after["items"][0]["restored_at"] is not None
        finally:
            if restored_id is not None:
                cleanup_resp = integration_client.delete(f"/v1/deals/admin/{restored_id}")
                assert cleanup_resp.status_code == 204, cleanup_resp.text
    finally:
        # Best-effort: si `_confirm_deletion` ya tuvo éxito, este deal ya no
        # existe y se espera un 404, que es correcto — es solo la red de
        # seguridad para cuando falla antes de llegar ahí.
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_restore_item_ya_restaurado_devuelve_409(integration_client):
    # La primera llamada a /restore SÍ crea un deal activo permanente (igual
    # que en test_restore_item_recrea_el_deal_activo) aunque el objetivo del
    # test sea la segunda llamada (409) — hay que limpiar el deal restaurado
    # en la primera, no solo comprobar el 409 de la segunda.
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0RESTORE002")
    # Igual que en test_restore_item_recrea_el_deal_activo: envuelve todo el
    # cuerpo para que un fallo entre crear el deal y confirmar su borrado no
    # deje un huérfano (finding 4).
    try:
        run = _confirm_deletion(integration_client, task_id, deal)
        detail = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}").json()
        item_id = detail["items"][0]["id"]

        # La primera llamada a /restore es la que crea el deal activo permanente
        # (la segunda, bajo test para el 409, nunca llega a crear nada). Igual
        # que en test_restore_item_recrea_el_deal_activo, la llamada y su
        # aserción de status van DENTRO del try para que un fallo ahí no impida
        # la limpieza si el deal ya quedó persistido.
        restored_id = None
        try:
            first_restore = integration_client.post(f"/v1/admin/scheduled-tasks/runs/items/{item_id}/restore")
            assert first_restore.status_code == 200, first_restore.text
            restored_id = first_restore.json()["id"]

            resp = integration_client.post(f"/v1/admin/scheduled-tasks/runs/items/{item_id}/restore")

            assert resp.status_code == 409
        finally:
            if restored_id is not None:
                cleanup_resp = integration_client.delete(f"/v1/deals/admin/{restored_id}")
                assert cleanup_resp.status_code == 204, cleanup_resp.text
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_delete_run_lo_elimina(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal = _create_deal(integration_client, asin="B0DELETERUN1")
    try:
        run = _confirm_deletion(integration_client, task_id, deal)

        resp = integration_client.delete(f"/v1/admin/scheduled-tasks/runs/{run['id']}")
        assert resp.status_code == 204

        detail_resp = integration_client.get(f"/v1/admin/scheduled-tasks/runs/{run['id']}")
        assert detail_resp.status_code == 404
    finally:
        integration_client.delete(f"/v1/deals/admin/{deal['id']}")


def test_bulk_delete_runs_borra_varios(integration_client):
    task_id = _get_price_check_task_id(integration_client)
    deal_a = _create_deal(integration_client, asin="B0BULK000001")
    deal_b = _create_deal(integration_client, asin="B0BULK000002")
    try:
        run_a = _confirm_deletion(integration_client, task_id, deal_a)
        run_b = _confirm_deletion(integration_client, task_id, deal_b)

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
