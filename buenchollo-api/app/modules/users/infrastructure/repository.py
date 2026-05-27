"""Repositorio del módulo users.

Encapsula toda la persistencia relacionada con perfiles, roles, stats por
usuario y agregados del panel admin. La capa `application/UserService`
consume estos métodos sin construir SQL.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.modules.users.domain.models import Profile


class ProfileRepository:
    """Repositorio de perfiles y vistas relacionadas con usuarios."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Perfil del usuario actual ────────────────────────────────────────────

    async def get_by_user_id(self, user_id: str) -> Profile | None:
        result = await self.session.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        return result.scalars().first()

    async def update_profile(
        self, user_id: str, display_name: str, bio: str
    ) -> Profile | None:
        profile = await self.get_by_user_id(user_id)
        if not profile:
            return None
        profile.display_name = display_name
        profile.bio = bio
        await self.session.flush()
        return profile

    async def get_username(self, user_id: str) -> str | None:
        result = await self.session.execute(
            text("SELECT username FROM public.profiles WHERE user_id::text = :uid LIMIT 1"),
            {"uid": user_id},
        )
        row = result.fetchone()
        return row[0] if row else None

    # ── Roles ────────────────────────────────────────────────────────────────

    async def get_user_roles(self, user_id: str) -> list[str]:
        """Devuelve los roles del usuario (tabla `user_roles`)."""
        result = await self.session.execute(
            text("SELECT role FROM public.user_roles WHERE user_id::text = :uid LIMIT 5"),
            {"uid": user_id},
        )
        return [row[0] for row in result.fetchall()]

    # ── Stats ────────────────────────────────────────────────────────────────

    _ZERO_STATS = {
        "comments_made": 0,
        "comments_received": 0,
        "likes_given": 0,
        "likes_received": 0,
        "dislikes_received": 0,
        "deal_votes_cast": 0,
        "favorites_count": 0,
    }

    async def get_user_stats(self, user_id: str) -> dict:
        """RPC `public.get_user_stats(_user_id uuid)` definida en Supabase."""
        row = (
            await self.session.execute(
                text("SELECT * FROM public.get_user_stats(CAST(:uid AS uuid))"),
                {"uid": user_id},
            )
        ).mappings().first()
        return dict(row) if row else dict(self._ZERO_STATS)

    # ── Admin ────────────────────────────────────────────────────────────────

    async def list_admin_users(self, limit: int = 200) -> list[dict]:
        """Lista de perfiles con sus roles agregados."""
        result = await self.session.execute(
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
                "LIMIT :limit"
            ),
            {"limit": limit},
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

    _ZERO_ADMIN_STATS = {
        "deals": 0,
        "active": 0,
        "favs": 0,
        "alerts": 0,
        "comments": 0,
        "users": 0,
    }

    async def get_admin_stats(self) -> dict:
        """6 counts agregados para el panel admin, en una sola query."""
        row = (
            await self.session.execute(
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
        return dict(row) if row else dict(self._ZERO_ADMIN_STATS)
