"""Tests de integración para los endpoints de categorías y tiendas."""
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


# ── Categorías ────────────────────────────────────────────────────────────────

def test_list_categories_returns_200(integration_client):
    response = integration_client.get("/categories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_categories_items_have_required_fields(integration_client):
    response = integration_client.get("/categories")
    categories = response.json()
    if categories:
        cat = categories[0]
        assert "id" in cat
        assert "name" in cat
        assert "slug" in cat


def test_get_category_by_invalid_slug_returns_404(integration_client):
    response = integration_client.get("/categories/slug-que-no-existe-jamas")
    assert response.status_code == 404


def test_admin_list_all_categories_returns_200(integration_client):
    response = integration_client.get("/categories/admin/all")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_admin_create_and_delete_category(integration_client):
    unique_id = str(uuid.uuid4())[:8]
    payload = {
        "name": f"Test Category {unique_id}",
        "slug": f"test-category-{unique_id}",
        "description": "Categoría de prueba",
        "is_active": True,
    }
    create_response = integration_client.post("/categories/admin", json=payload)
    assert create_response.status_code == 200, create_response.text
    created = create_response.json()
    assert created["name"] == payload["name"]

    delete_response = integration_client.delete(f"/categories/admin/{created['id']}")
    assert delete_response.status_code == 204, delete_response.text


def test_admin_delete_nonexistent_category_returns_404(integration_client):
    response = integration_client.delete("/categories/admin/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ── Tiendas ───────────────────────────────────────────────────────────────────

def test_list_stores_returns_200(integration_client):
    response = integration_client.get("/stores")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_stores_items_have_required_fields(integration_client):
    response = integration_client.get("/stores")
    stores = response.json()
    if stores:
        store = stores[0]
        assert "id" in store
        assert "name" in store
