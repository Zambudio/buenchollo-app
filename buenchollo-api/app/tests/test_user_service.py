"""Tests unitarios del UserService.

Mockea `ProfileRepository` con `AsyncMock`; no requiere BD ni red.
Verifica el cableado de los casos de uso y el manejo de excepciones.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.modules.users.application.user_service import CurrentUser, UserService
from app.modules.users.domain.exceptions import ProfileNotFound


def _build_service(**repo_overrides):
    """Construye un UserService con un repo MagicMock y los métodos async
    sobreescribibles. Por defecto los métodos devuelven valores neutros."""
    repo = MagicMock()
    repo.get_user_roles = AsyncMock(return_value=[])
    repo.get_by_user_id = AsyncMock(return_value=None)
    repo.update_profile = AsyncMock(return_value=None)
    repo.get_user_stats = AsyncMock(return_value={"comments_made": 0})
    repo.list_admin_users = AsyncMock(return_value=[])
    repo.get_admin_stats = AsyncMock(return_value={"deals": 0})

    for name, value in repo_overrides.items():
        setattr(repo, name, value)

    return UserService(repo), repo


# ── /auth/me ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me_overview_devuelve_admin_true_si_rol_admin():
    profile = SimpleNamespace(
        display_name="Pedro",
        avatar_url="https://x.com/a.png",
        username="pedrillo",
    )
    service, _ = _build_service(
        get_user_roles=AsyncMock(return_value=["user", "admin"]),
        get_by_user_id=AsyncMock(return_value=profile),
    )

    result = await service.get_me_overview(CurrentUser(id="u1", email="a@b.es"))

    assert result == {
        "user_id": "u1",
        "email": "a@b.es",
        "roles": ["user", "admin"],
        "is_admin": True,
        "has_profile": True,
        "needs_onboarding": False,
        "display_name": "Pedro",
        "avatar_url": "https://x.com/a.png",
        "username": "pedrillo",
    }


@pytest.mark.asyncio
async def test_get_me_overview_sin_perfil_devuelve_has_profile_false():
    service, _ = _build_service(
        get_user_roles=AsyncMock(return_value=["user"]),
        get_username=AsyncMock(return_value=None),
    )

    result = await service.get_me_overview(CurrentUser(id="u1", email=None))

    assert result["is_admin"] is False
    assert result["has_profile"] is False
    assert result["needs_onboarding"] is True
    assert result["display_name"] is None
    assert result["avatar_url"] is None
    assert result["username"] is None


# ── perfil propio ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_my_profile_devuelve_esqueleto_si_no_existe():
    service, _ = _build_service()

    result = await service.get_my_profile("u1")

    assert result == {
        "user_id": "u1",
        "display_name": None,
        "bio": None,
        "avatar_url": None,
        "username": None,
    }


@pytest.mark.asyncio
async def test_get_my_profile_serializa_la_entidad():
    profile = SimpleNamespace(
        user_id="u1",
        display_name="Pedro",
        bio="Hola",
        avatar_url="https://x.com/a.png",
        username="pedrillo",
    )
    service, _ = _build_service(get_by_user_id=AsyncMock(return_value=profile))

    result = await service.get_my_profile("u1")

    assert result["display_name"] == "Pedro"
    assert result["bio"] == "Hola"
    assert result["username"] == "pedrillo"


@pytest.mark.asyncio
async def test_update_my_profile_trunca_a_los_limites_de_bd():
    captured = {}

    async def fake_update(user_id, display_name, bio, avatar_url=None, update_avatar=False):
        captured.update({
            "display_name": display_name,
            "bio": bio,
            "avatar_url": avatar_url,
            "update_avatar": update_avatar,
        })
        return SimpleNamespace(
            user_id=user_id,
            display_name=display_name,
            bio=bio,
            avatar_url=avatar_url,
            username=None,
        )

    service, _ = _build_service(update_profile=AsyncMock(side_effect=fake_update))

    nombre_largo = "x" * 80   # > 50
    bio_larga = "y" * 500     # > 300

    await service.update_my_profile(
        "u1",
        display_name=nombre_largo,
        bio=bio_larga,
        avatar_url="https://x.com/avatar.png",
    )

    assert len(captured["display_name"]) == 50
    assert len(captured["bio"]) == 300
    assert captured["avatar_url"] == "https://x.com/avatar.png"
    assert captured["update_avatar"] is True


@pytest.mark.asyncio
async def test_update_my_profile_permita_borrar_avatar():
    captured = {}

    async def fake_update(user_id, display_name, bio, avatar_url=None, update_avatar=False):
        captured.update({"avatar_url": avatar_url, "update_avatar": update_avatar})
        return SimpleNamespace(
            user_id=user_id,
            display_name=display_name,
            bio=bio,
            avatar_url=avatar_url,
            username=None,
        )

    service, _ = _build_service(update_profile=AsyncMock(side_effect=fake_update))

    result = await service.update_my_profile(
        "u1",
        display_name="Pedro",
        bio="",
        avatar_url=None,
        update_avatar=True,
    )

    assert captured == {"avatar_url": None, "update_avatar": True}
    assert result["avatar_url"] is None


@pytest.mark.asyncio
async def test_update_my_profile_lanza_profile_not_found_si_no_existe():
    service, _ = _build_service(update_profile=AsyncMock(return_value=None))

    with pytest.raises(ProfileNotFound):
        await service.update_my_profile("u1", display_name="x", bio="")


# ── admin ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_helpers_delegan_al_repo():
    expected_users = [{"user_id": "u1", "roles": ["admin"]}]
    expected_stats = {"deals": 12, "active": 8, "favs": 4, "alerts": 0, "comments": 5, "users": 3}
    service, repo = _build_service(
        list_admin_users=AsyncMock(return_value=expected_users),
        get_admin_stats=AsyncMock(return_value=expected_stats),
    )

    assert await service.list_admin_users() == expected_users
    repo.list_admin_users.assert_awaited_once_with(limit=200)

    assert await service.get_admin_stats() == expected_stats
    repo.get_admin_stats.assert_awaited_once()
