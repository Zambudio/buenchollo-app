"""Casos de uso del módulo users.

Concentra la lógica de aplicación relacionada con autenticación de usuario,
perfil, estadísticas y agregados de administración. El router se limita a
hablar HTTP y delegar; el service no conoce FastAPI ni `HTTPException`.

Las excepciones de dominio (`ProfileNotFound`) se lanzan desde aquí y el
handler global en `main.py` las traduce al status HTTP.
"""
from dataclasses import dataclass

from app.modules.users.domain.exceptions import ProfileNotFound
from app.modules.users.infrastructure.repository import ProfileRepository


@dataclass(frozen=True)
class CurrentUser:
    """Snapshot mínimo del usuario autenticado, desacoplado del SDK de Supabase.

    El router resuelve el JWT y construye este objeto al llamar al service,
    de modo que la capa application no depende del modelo `User` de Supabase.
    """
    id: str
    email: str | None


class UserService:
    """Casos de uso del dominio users."""

    def __init__(self, repo: ProfileRepository) -> None:
        self.repo = repo

    # ── /auth/me ─────────────────────────────────────────────────────────────

    async def get_me_overview(self, user: CurrentUser) -> dict:
        """Devuelve resumen del usuario autenticado: identificador, email,
        roles, si tiene perfil y el username (si lo hay).

        Endpoint diagnóstico: comprueba en un único ida-y-vuelta que el JWT
        está bien validado y que las tablas auxiliares responden.
        """
        roles = await self.repo.get_user_roles(user.id)
        username = await self.repo.get_username(user.id)
        return {
            "user_id": user.id,
            "email": user.email,
            "roles": roles,
            "is_admin": "admin" in roles,
            "has_profile": username is not None,
            "username": username,
        }

    # ── Perfil del usuario actual ────────────────────────────────────────────

    async def get_my_profile(self, user_id: str) -> dict:
        """Devuelve el perfil del usuario o un esqueleto con valores nulos.

        Convención: si el trigger `handle_new_user` no se disparó (caso raro),
        respondemos con un perfil vacío en lugar de 404 para que la UI pueda
        mostrar el formulario inicial.
        """
        profile = await self.repo.get_by_user_id(user_id)
        if not profile:
            return {
                "user_id": user_id,
                "display_name": None,
                "bio": None,
                "avatar_url": None,
                "username": None,
            }
        return {
            "user_id": str(profile.user_id),
            "display_name": profile.display_name,
            "bio": profile.bio,
            "avatar_url": profile.avatar_url,
            "username": profile.username,
        }

    async def update_my_profile(self, user_id: str, display_name: str, bio: str) -> dict:
        """Actualiza `display_name` y `bio`. Trunca a los límites de la BD
        (50 y 300 caracteres respectivamente) para evitar errores 500 por
        violación de longitud."""
        updated = await self.repo.update_profile(
            user_id,
            display_name=display_name.strip()[:50],
            bio=bio.strip()[:300],
        )
        if not updated:
            raise ProfileNotFound()
        return {
            "user_id": str(updated.user_id),
            "display_name": updated.display_name,
            "bio": updated.bio,
            "avatar_url": updated.avatar_url,
            "username": updated.username,
        }

    async def get_my_stats(self, user_id: str) -> dict:
        return await self.repo.get_user_stats(user_id)

    # ── Admin ────────────────────────────────────────────────────────────────

    async def list_admin_users(self, limit: int = 200) -> list[dict]:
        return await self.repo.list_admin_users(limit=limit)

    async def get_admin_stats(self) -> dict:
        return await self.repo.get_admin_stats()
