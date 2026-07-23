"""Tests de integración de comentarios de artículos del blog.

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
def override_auth():
    app.dependency_overrides[require_admin] = mock_require_admin
    app.dependency_overrides[get_current_user] = mock_require_admin
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def ensure_mock_profile():
    """Igual que en test_blog_api.py: `blog_posts.author_id` tiene FK
    obligatoria a `profiles`, que no existe en el Postgres efímero del CI."""
    import asyncio

    from sqlalchemy import text as sa_text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import get_settings

    async def _seed():
        settings = get_settings()
        engine = create_async_engine(settings.database_url, connect_args={"statement_cache_size": 0})
        async with engine.begin() as conn:
            await conn.execute(
                sa_text(
                    "INSERT INTO profiles (id, user_id, display_name) "
                    "VALUES (gen_random_uuid(), CAST(:uid AS uuid), 'Test Admin') "
                    "ON CONFLICT (user_id) DO NOTHING"
                ),
                {"uid": MockUser.id},
            )
        await engine.dispose()

    asyncio.run(_seed())
    yield


def _create_post(client) -> str:
    cat_slug = f"cat-{str(uuid.uuid4())[:8]}"
    category = client.post(
        "/v1/blog/admin/categories", json={"name": cat_slug, "slug": cat_slug}
    ).json()
    slug = f"post-{str(uuid.uuid4())[:8]}"
    post = client.post(
        "/v1/blog/admin/posts",
        json={
            "title": "Artículo con comentarios",
            "slug": slug,
            "excerpt": "Resumen",
            "content": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}]},
            "cover_image_url": "https://cdn.example.com/cover.png",
            "cover_image_alt": "Portada",
            "category_id": category["id"],
        },
    ).json()
    return post["id"]


def test_crear_listar_y_borrar_comentario(integration_client):
    post_id = _create_post(integration_client)

    create = integration_client.post(f"/v1/blog/posts/{post_id}/comments", json={"content": "Muy útil, gracias"})
    assert create.status_code == 201, create.text
    comment = create.json()
    assert comment["content"] == "Muy útil, gracias"
    assert comment["blog_post_id"] == post_id

    listing = integration_client.get(f"/v1/blog/posts/{post_id}/comments")
    assert listing.status_code == 200
    assert any(c["id"] == comment["id"] for c in listing.json()["comments"])

    delete = integration_client.delete(f"/v1/blog/comments/{comment['id']}")
    assert delete.status_code == 204

    listing2 = integration_client.get(f"/v1/blog/posts/{post_id}/comments")
    assert not any(c["id"] == comment["id"] for c in listing2.json()["comments"])


def test_respuesta_a_comentario_de_otro_post_es_invalida(integration_client):
    post_a = _create_post(integration_client)
    post_b = _create_post(integration_client)
    parent = integration_client.post(f"/v1/blog/posts/{post_a}/comments", json={"content": "Comentario raíz"}).json()

    reply = integration_client.post(
        f"/v1/blog/posts/{post_b}/comments", json={"content": "Respuesta cruzada", "parent_id": parent["id"]}
    )
    assert reply.status_code == 400


def test_votar_comentario_actualiza_contadores(integration_client):
    post_id = _create_post(integration_client)
    comment = integration_client.post(f"/v1/blog/posts/{post_id}/comments", json={"content": "Voto de prueba"}).json()

    vote = integration_client.post(f"/v1/blog/comments/{comment['id']}/vote", json={"vote": 1})
    assert vote.status_code == 200
    assert vote.json()["my_vote"] == 1

    listing = integration_client.get(f"/v1/blog/posts/{post_id}/comments/with-my-votes")
    updated = next(c for c in listing.json()["comments"] if c["id"] == comment["id"])
    assert updated["votes_up"] == 1
    assert updated["my_vote"] == 1

    # repetir el mismo voto lo retira
    vote_again = integration_client.post(f"/v1/blog/comments/{comment['id']}/vote", json={"vote": 1})
    assert vote_again.json()["my_vote"] == 0


def test_solo_el_autor_puede_borrar_su_comentario(integration_client):
    post_id = _create_post(integration_client)
    comment = integration_client.post(f"/v1/blog/posts/{post_id}/comments", json={"content": "No me borres"}).json()

    async def other_user():
        class Other:
            id = "11111111-1111-1111-1111-111111111111"
        return Other()

    app.dependency_overrides[get_current_user] = other_user
    try:
        delete = integration_client.delete(f"/v1/blog/comments/{comment['id']}")
        assert delete.status_code == 403
    finally:
        app.dependency_overrides[get_current_user] = lambda: MockUser()
