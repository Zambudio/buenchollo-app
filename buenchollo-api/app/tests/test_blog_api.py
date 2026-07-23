"""Tests de integración del CRUD y publicación de artículos de blog.

Requieren PostgreSQL real. En CI se excluyen con -m "not integration".
"""
import uuid

import pytest

from app.main import app
from app.core.security import get_current_user, require_admin

pytestmark = pytest.mark.integration


class MockUser:
    id = "dbe6e006-4f3e-4be8-8351-7e264ed3acb6"


async def mock_require_admin():
    return MockUser()


@pytest.fixture(autouse=True)
def override_admin():
    app.dependency_overrides[require_admin] = mock_require_admin
    app.dependency_overrides[get_current_user] = mock_require_admin
    yield
    app.dependency_overrides.clear()


def _unique(prefix: str) -> str:
    return f"{prefix}-{str(uuid.uuid4())[:8]}"


def _create_category(client) -> dict:
    slug = _unique("cat")
    response = client.post("/v1/blog/admin/categories", json={"name": slug, "slug": slug})
    assert response.status_code == 200, response.text
    return response.json()


def _publishable_payload(slug: str, category_id: str) -> dict:
    return {
        "title": "Guía de compra de auriculares 2026",
        "slug": slug,
        "excerpt": "Un resumen de las mejores opciones.",
        "content": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Contenido real"}]}]},
        "cover_image_url": "https://cdn.example.com/cover.png",
        "cover_image_alt": "Portada del artículo",
        "category_id": category_id,
    }


def test_crear_borrador_no_es_visible_publicamente(integration_client):
    category = _create_category(integration_client)
    slug = _unique("borrador")
    response = integration_client.post("/v1/blog/admin/posts", json=_publishable_payload(slug, category["id"]))
    assert response.status_code == 200, response.text
    post = response.json()
    assert post["status"] == "draft"

    public_response = integration_client.get(f"/v1/blog/posts/{slug}")
    assert public_response.status_code == 404


def test_publicar_articulo_lo_hace_visible_en_listado_y_por_slug(integration_client):
    category = _create_category(integration_client)
    slug = _unique("publicado")
    created = integration_client.post("/v1/blog/admin/posts", json=_publishable_payload(slug, category["id"])).json()

    publish_response = integration_client.post(f"/v1/blog/admin/posts/{created['id']}/publish")
    assert publish_response.status_code == 200, publish_response.text
    assert publish_response.json()["status"] == "published"

    detail = integration_client.get(f"/v1/blog/posts/{slug}")
    assert detail.status_code == 200
    assert detail.json()["slug"] == slug

    listing = integration_client.get("/v1/blog/posts")
    assert listing.status_code == 200
    slugs = [item["slug"] for item in listing.json()["items"]]
    assert slug in slugs


def test_publicar_sin_campos_obligatorios_falla(integration_client):
    category = _create_category(integration_client)
    slug = _unique("incompleto")
    created = integration_client.post(
        "/v1/blog/admin/posts", json={"title": "Solo título", "slug": slug, "category_id": category["id"]},
    ).json()

    publish_response = integration_client.post(f"/v1/blog/admin/posts/{created['id']}/publish")
    assert publish_response.status_code == 400, publish_response.text


def test_slug_duplicado_devuelve_conflicto(integration_client):
    category = _create_category(integration_client)
    slug = _unique("duplicado")
    payload = _publishable_payload(slug, category["id"])
    first = integration_client.post("/v1/blog/admin/posts", json=payload)
    assert first.status_code == 200, first.text

    payload2 = _publishable_payload(slug, category["id"])
    payload2["title"] = "Otro título"
    second = integration_client.post("/v1/blog/admin/posts", json=payload2)
    assert second.status_code == 409


def test_archivar_deja_de_ser_visible_publicamente(integration_client):
    category = _create_category(integration_client)
    slug = _unique("archivado")
    created = integration_client.post("/v1/blog/admin/posts", json=_publishable_payload(slug, category["id"])).json()
    integration_client.post(f"/v1/blog/admin/posts/{created['id']}/publish")

    archive_response = integration_client.post(f"/v1/blog/admin/posts/{created['id']}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    public_response = integration_client.get(f"/v1/blog/posts/{slug}")
    assert public_response.status_code == 404


def test_eliminar_articulo(integration_client):
    category = _create_category(integration_client)
    slug = _unique("borrar")
    created = integration_client.post("/v1/blog/admin/posts", json=_publishable_payload(slug, category["id"])).json()

    delete_response = integration_client.delete(f"/v1/blog/admin/posts/{created['id']}")
    assert delete_response.status_code == 204

    get_response = integration_client.get(f"/v1/blog/admin/posts/{created['id']}")
    assert get_response.status_code == 404


def test_filtro_por_categoria_publica(integration_client):
    category = _create_category(integration_client)
    slug = _unique("filtrado")
    created = integration_client.post("/v1/blog/admin/posts", json=_publishable_payload(slug, category["id"])).json()
    integration_client.post(f"/v1/blog/admin/posts/{created['id']}/publish")

    response = integration_client.get("/v1/blog/posts", params={"category": category["slug"]})
    assert response.status_code == 200
    slugs = [item["slug"] for item in response.json()["items"]]
    assert slug in slugs


def test_listado_admin_pagina_y_filtra_por_estado(integration_client):
    category = _create_category(integration_client)
    slug = _unique("paginado")
    integration_client.post("/v1/blog/admin/posts", json=_publishable_payload(slug, category["id"]))

    response = integration_client.get("/v1/blog/admin/posts", params={"status": "draft", "page": 1, "page_size": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert all(item["status"] == "draft" for item in body["items"])


def test_categorias_publicas_solo_muestran_activas(integration_client):
    slug = _unique("cat-inactiva")
    inactive = integration_client.post("/v1/blog/admin/categories", json={"name": slug, "slug": slug, "is_active": False}).json()

    response = integration_client.get("/v1/blog/categories")
    assert response.status_code == 200
    assert inactive["id"] not in [c["id"] for c in response.json()]


def test_sitemap_solo_incluye_publicados(integration_client):
    category = _create_category(integration_client)
    slug = _unique("sitemap")
    created = integration_client.post("/v1/blog/admin/posts", json=_publishable_payload(slug, category["id"])).json()
    integration_client.post(f"/v1/blog/admin/posts/{created['id']}/publish")

    response = integration_client.get("/v1/blog/sitemap")
    assert response.status_code == 200
    assert slug in [entry["slug"] for entry in response.json()]


def test_endpoints_admin_rechazan_sin_autenticacion():
    from fastapi.testclient import TestClient

    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as anon_client:
        response = anon_client.get("/v1/blog/admin/posts")
    assert response.status_code in (401, 403)


def test_votar_articulo_y_repetir_voto_lo_retira(integration_client):
    category = _create_category(integration_client)
    slug = _unique("votable")
    created = integration_client.post("/v1/blog/admin/posts", json=_publishable_payload(slug, category["id"])).json()
    integration_client.post(f"/v1/blog/admin/posts/{created['id']}/publish")

    vote = integration_client.post(f"/v1/blog/posts/{created['id']}/vote", json={"vote": 1})
    assert vote.status_code == 200, vote.text
    assert vote.json() == {"votes_up": 1, "votes_down": 0, "my_vote": 1}

    my_vote = integration_client.get(f"/v1/blog/posts/{created['id']}/my-vote")
    assert my_vote.json() == {"my_vote": 1}

    detail = integration_client.get(f"/v1/blog/posts/{slug}")
    assert detail.json()["votes_up"] == 1

    again = integration_client.post(f"/v1/blog/posts/{created['id']}/vote", json={"vote": 1})
    assert again.json() == {"votes_up": 0, "votes_down": 0, "my_vote": 0}
