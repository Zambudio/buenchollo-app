"""Endpoints de autenticación y perfil de usuario."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint de diagnóstico: devuelve el usuario autenticado y su rol.
    Útil para verificar que el JWT se captura y valida correctamente.
    """
    user_id = str(current_user.id)

    # Comprobar si tiene rol admin en user_roles
    result = await db.execute(
        text("SELECT role FROM user_roles WHERE user_id::text = :uid LIMIT 5"),
        {"uid": user_id},
    )
    roles = [row[0] for row in result.fetchall()]

    # Comprobar si existe perfil
    profile_result = await db.execute(
        text("SELECT username FROM profiles WHERE user_id::text = :uid LIMIT 1"),
        {"uid": user_id},
    )
    profile_row = profile_result.fetchone()

    return {
        "user_id": user_id,
        "email": current_user.email,
        "roles": roles,
        "is_admin": "admin" in roles,
        "has_profile": profile_row is not None,
        "username": profile_row[0] if profile_row else None,
    }
