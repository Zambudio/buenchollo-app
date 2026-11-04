from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import AuthenticatedUser, get_current_user
from app.modules.emails.application.rendering import EmailBranding
from app.modules.emails.infrastructure.smtp import get_email_sender
from app.modules.submissions.application.notifier import (
    SubmissionNotifier,
    supabase_user_email_lookup,
)
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
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    profile = await profile_repo.get_by_user_id(user.id)
    complete = is_profile_complete(profile)
    # Cierra la transacción de solo lectura: la conexión vuelve al pool (3+2 por
    # worker, TD-11) en vez de quedar retenida durante la E/S externa del
    # endpoint (Amazon, Pillow, Storage). La siguiente consulta la re-adquiere.
    await db.rollback()
    if not complete:
        raise ProfileIncompleteError()
    return user


def get_submission_notifier(settings: Settings = Depends(get_settings)) -> SubmissionNotifier:
    return SubmissionNotifier(
        get_email_sender(), EmailBranding(), settings, supabase_user_email_lookup(settings)
    )
