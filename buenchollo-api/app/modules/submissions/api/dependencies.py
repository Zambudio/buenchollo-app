from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import AuthenticatedUser, get_current_user
from app.modules.submissions.domain.exceptions import ProfileIncompleteError
from app.modules.submissions.domain.rules import is_profile_complete
from app.modules.submissions.infrastructure.repository import SubmissionRepository
from app.modules.users.infrastructure.repository import ProfileRepository


def get_submission_repository(db: AsyncSession = Depends(get_db)) -> SubmissionRepository:
    return SubmissionRepository(db)


async def get_profile_repository(db: AsyncSession = Depends(get_db)) -> ProfileRepository:
    return ProfileRepository(db)


async def require_complete_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
) -> AuthenticatedUser:
    profile = await profile_repo.get_by_user_id(user.id)
    if not is_profile_complete(profile):
        raise ProfileIncompleteError()
    return user
