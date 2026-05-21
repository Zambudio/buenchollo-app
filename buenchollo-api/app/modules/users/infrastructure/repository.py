from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.users.domain.models import Profile

class ProfileRepository:
    """Repository for managing user profiles in the database."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: str) -> Profile | None:
        result = await self.session.execute(select(Profile).where(Profile.user_id == user_id))
        return result.scalars().first()
