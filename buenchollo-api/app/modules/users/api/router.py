"""Endpoints de autenticación y perfil de usuario."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.modules.users.infrastructure.repository import ProfileRepository

router = APIRouter(tags=["auth"])


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)
    bio: str = Field(default="", max_length=300)


def get_profile_repository(db: AsyncSession = Depends(get_db)) -> ProfileRepository:
    return ProfileRepository(db)


@router.get("/auth/me")
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


@router.get("/users/me/profile")
async def get_my_profile(
    current_user=Depends(get_current_user),
    repo: ProfileRepository = Depends(get_profile_repository),
) -> dict:
    profile = await repo.get_by_user_id(str(current_user.id))
    if not profile:
        return {"user_id": str(current_user.id), "display_name": None, "bio": None, "avatar_url": None, "username": None}
    return {
        "user_id": str(profile.user_id),
        "display_name": profile.display_name,
        "bio": profile.bio,
        "avatar_url": profile.avatar_url,
        "username": profile.username,
    }


@router.put("/users/me/profile")
async def update_my_profile(
    payload: ProfileUpdate,
    current_user=Depends(get_current_user),
    repo: ProfileRepository = Depends(get_profile_repository),
) -> dict:
    updated = await repo.update_profile(
        str(current_user.id),
        display_name=payload.display_name.strip()[:50],
        bio=payload.bio.strip()[:300],
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return {
        "user_id": str(updated.user_id),
        "display_name": updated.display_name,
        "bio": updated.bio,
        "avatar_url": updated.avatar_url,
        "username": updated.username,
    }


@router.get("/users/me/stats")
async def get_my_stats(
    current_user=Depends(get_current_user),
    repo: ProfileRepository = Depends(get_profile_repository),
) -> dict:
    return await repo.get_user_stats(str(current_user.id))


@router.get("/admin/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_admin),
) -> dict:
    """Contadores agregados para el dashboard del admin. Ejecuta los 6 counts en
    una sola consulta SQL para evitar 6 round-trips."""
    row = (
        await db.execute(
            text(
                "SELECT "
                "  (SELECT COUNT(*) FROM public.deals) AS deals, "
                "  (SELECT COUNT(*) FROM public.deals WHERE status = 'active') AS active, "
                "  (SELECT COUNT(*) FROM public.favorites) AS favs, "
                "  (SELECT COUNT(*) FROM public.alerts) AS alerts, "
                "  (SELECT COUNT(*) FROM public.deal_comments) AS comments, "
                "  (SELECT COUNT(*) FROM public.profiles) AS users"
            )
        )
    ).mappings().first()
    return dict(row) if row else {"deals": 0, "active": 0, "favs": 0, "alerts": 0, "comments": 0, "users": 0}


@router.get("/admin/users")
async def admin_list_users(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_admin),
) -> list[dict]:
    """Lista todos los perfiles con sus roles (sólo admin)."""
    result = await db.execute(
        text(
            "SELECT p.user_id::text AS user_id, "
            "       p.display_name, "
            "       p.username, "
            "       p.avatar_url, "
            "       p.created_at, "
            "       COALESCE("
            "         array_agg(r.role::text) FILTER (WHERE r.role IS NOT NULL), "
            "         ARRAY[]::text[]"
            "       ) AS roles "
            "FROM public.profiles p "
            "LEFT JOIN public.user_roles r ON r.user_id = p.user_id "
            "GROUP BY p.user_id, p.display_name, p.username, p.avatar_url, p.created_at "
            "ORDER BY p.created_at DESC "
            "LIMIT 200"
        )
    )
    return [
        {
            "user_id": row["user_id"],
            "display_name": row["display_name"],
            "username": row["username"],
            "avatar_url": row["avatar_url"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "roles": list(row["roles"]) if row["roles"] else [],
        }
        for row in result.mappings().all()
    ]
