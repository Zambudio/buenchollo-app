"""Endpoints de autenticación, perfil de usuario y agregados de admin.

El router se limita a hablar HTTP: recibe la petición, resuelve auth,
delega al `UserService` y devuelve la respuesta. Toda la lógica vive en
la capa de aplicación.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.modules.users.application.user_service import CurrentUser, UserService
from app.modules.users.infrastructure.repository import ProfileRepository

router = APIRouter(tags=["auth"])


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)
    bio: str = Field(default="", max_length=300)
    avatar_url: str | None = Field(default=None, max_length=2048)


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Ensambla UserService con su repositorio (composition root distribuido,
    ADR-007)."""
    return UserService(ProfileRepository(db))


@router.get("/auth/me")
async def get_me(
    current_user=Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Resumen del usuario autenticado: id, email, roles, perfil y username."""
    user = CurrentUser(id=str(current_user.id), email=current_user.email)
    return await service.get_me_overview(user)


@router.get("/users/me/profile")
async def get_my_profile(
    current_user=Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    return await service.get_my_profile(str(current_user.id))


@router.put("/users/me/profile")
async def update_my_profile(
    payload: ProfileUpdate,
    current_user=Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    return await service.update_my_profile(
        str(current_user.id),
        display_name=payload.display_name,
        bio=payload.bio,
        avatar_url=payload.avatar_url,
        update_avatar="avatar_url" in payload.model_fields_set,
    )


@router.get("/users/me/stats")
async def get_my_stats(
    current_user=Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    return await service.get_my_stats(str(current_user.id))


@router.get("/admin/stats")
async def admin_stats(
    service: UserService = Depends(get_user_service),
    _auth=Depends(require_admin),
) -> dict:
    """Contadores agregados para el dashboard del admin."""
    return await service.get_admin_stats()


@router.get("/admin/users")
async def admin_list_users(
    service: UserService = Depends(get_user_service),
    _auth=Depends(require_admin),
) -> list[dict]:
    """Lista todos los perfiles con sus roles."""
    return await service.list_admin_users()


@router.get("/admin/audit")
async def admin_list_audit_log(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None, description="Filtro exacto por action (deal.create, etc.)"),
    target_type: str | None = Query(None, description="Filtro por tipo de entidad"),
    user_id: str | None = Query(None, description="Filtro por id de admin"),
    service: UserService = Depends(get_user_service),
    _auth=Depends(require_admin),
) -> list[dict]:
    """Audit log de acciones admin críticas. Paginado y filtrable."""
    return await service.list_audit_log(
        limit=limit, offset=offset, action=action,
        target_type=target_type, user_id=user_id,
    )
