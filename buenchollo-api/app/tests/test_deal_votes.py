"""Tests de integración para votos de chollos (temperatura + my-votes bulk).

Requieren PostgreSQL real. En CI se excluyen con -m "not integration";
en local se ejecutan junto a los unitarios.

Nota: `deal_votes.user_id` tiene FK contra la tabla real de usuarios, así
que no podemos fabricar UUIDs de usuario arbitrarios como en otros tests.
Reutilizamos el mismo usuario "admin" de prueba que ya usa el resto de la
suite de integración (test_deals_api.py) — es una fila real existente.
El voto se limpia solo al borrar el deal de prueba (ON DELETE CASCADE).
"""
import uuid
import pytest
from app.main import app
from app.core.security import require_admin, get_current_user

pytestmark = pytest.mark.integration


class MockAdmin:
    id = "dbe6e006-4f3e-4be8-8351-7e264ed3acb6"


async def mock_require_admin():
    return MockAdmin()


async def mock_get_current_user():
    return MockAdmin()


def _create_test_deal(client, suffix: str) -> str:
    payload = {
        "title": f"API Test Deal - Votes {suffix}",
        "slug": f"api-test-deal-votes-{suffix}",
        "current_price": 9.99,
        "affiliate_url": "https://amazon.es/dp/B000000002",
        "status": "active",
        "source": "manual",
    }
    response = client.post("/v1/deals/admin", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_vote_persiste_y_aparece_en_my_vote_y_en_el_bloque(integration_client):
    app.dependency_overrides[require_admin] = mock_require_admin
    app.dependency_overrides[get_current_user] = mock_get_current_user
    unique_id = str(uuid.uuid4())[:8]
    deal_id = _create_test_deal(integration_client, unique_id)

    try:
        # Votar arriba
        vote_resp = integration_client.post(f"/v1/deals/{deal_id}/vote", json={"vote": 1})
        assert vote_resp.status_code == 200, vote_resp.text
        body = vote_resp.json()
        assert body["temperature"] == 1
        assert body["votes_up"] == 1
        assert body["my_vote"] == 1

        # Simula "recargar la página": nueva petición GET /my-vote (no reusa
        # el resultado del POST anterior)
        my_vote_resp = integration_client.get(f"/v1/deals/{deal_id}/my-vote")
        assert my_vote_resp.status_code == 200, my_vote_resp.text
        assert my_vote_resp.json()["my_vote"] == 1

        # Y lo mismo por el endpoint en bloque que usa la grid de portada/explorar
        bulk_resp = integration_client.get(f"/v1/deals/my-votes?ids={deal_id}")
        assert bulk_resp.status_code == 200, bulk_resp.text
        assert bulk_resp.json() == {deal_id: 1}

        # El chollo, tal y como lo devuelve el listado público, refleja la
        # temperatura actualizada (contador global, no depende de quién mira)
        list_resp = integration_client.get("/v1/deals")
        assert list_resp.status_code == 200, list_resp.text
        listed = next((d for d in list_resp.json() if d["id"] == deal_id), None)
        assert listed is not None, "el deal recién votado no aparece en /v1/deals"
        assert listed["temperature"] == 1

        # Cambiar el voto a abajo: el bloque debe reflejar -1, no seguir en 1
        vote_down = integration_client.post(f"/v1/deals/{deal_id}/vote", json={"vote": -1})
        assert vote_down.status_code == 200, vote_down.text
        assert vote_down.json()["my_vote"] == -1

        bulk_resp_2 = integration_client.get(f"/v1/deals/my-votes?ids={deal_id}")
        assert bulk_resp_2.json() == {deal_id: -1}
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides[require_admin] = mock_require_admin
        integration_client.delete(f"/v1/deals/admin/{deal_id}")
        app.dependency_overrides.clear()


def test_my_votes_bloque_vacio_si_no_hay_ids(integration_client):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    try:
        resp = integration_client.get("/v1/deals/my-votes?ids=")
        assert resp.status_code == 200, resp.text
        assert resp.json() == {}
    finally:
        app.dependency_overrides.clear()
