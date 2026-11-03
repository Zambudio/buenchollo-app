from typing import Any

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.submissions.domain.models import PENDING, WITHDRAWN, DealSubmission


class ListMySubmissionsUseCase:
    def __init__(self, repo: Any) -> None:
        self.repo = repo

    async def execute(self, user_id: str, limit: int, offset: int) -> list[DealSubmission]:
        return await self.repo.list_by_user(user_id, limit, offset)


class WithdrawSubmissionUseCase:
    def __init__(self, repo: Any) -> None:
        self.repo = repo

    async def execute(self, user_id: str, submission_id: str) -> None:
        submission = await self.repo.get(submission_id)
        if submission is None or submission.user_id != user_id:
            raise NotFoundError("Propuesta no encontrada")
        if submission.status != PENDING or not await self.repo.claim_pending(
            submission_id, WITHDRAWN
        ):
            raise ConflictError("Solo se pueden retirar propuestas pendientes")
