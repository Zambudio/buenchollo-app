from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.modules.users.domain.models import Profile

class ProfileRepository:
    """Repository for managing user profiles in the database."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: str) -> Profile | None:
        result = await self.session.execute(select(Profile).where(Profile.user_id == user_id))
        return result.scalars().first()

    async def update_profile(self, user_id: str, display_name: str, bio: str) -> Profile | None:
        profile = await self.get_by_user_id(user_id)
        if not profile:
            return None
        profile.display_name = display_name
        profile.bio = bio
        await self.session.flush()
        return profile

    async def get_user_stats(self, user_id: str) -> dict:
        """Llama a la función RPC `public.get_user_stats(_user_id uuid)` definida
        en Supabase y devuelve un dict con los contadores."""
        row = (
            await self.session.execute(
                text("SELECT * FROM public.get_user_stats(CAST(:uid AS uuid))"),
                {"uid": user_id},
            )
        ).mappings().first()
        if not row:
            return {
                "comments_made": 0,
                "comments_received": 0,
                "likes_given": 0,
                "likes_received": 0,
                "dislikes_received": 0,
                "deal_votes_cast": 0,
                "favorites_count": 0,
            }
        return dict(row)
