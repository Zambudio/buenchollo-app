import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.affiliates.domain.links import canonicalize, ensure_not_shortened, extract_url
from app.modules.affiliates.domain.rewriters import rewrite_affiliate_link
from app.modules.deals.api.schemas import DealCreate
from app.modules.deals.domain.exceptions import DuplicateDealError
from app.modules.deals.domain.models import Deal
from app.modules.submissions.domain.exceptions import SubmissionNotPendingError
from app.modules.submissions.domain.models import (
    APPROVED,
    PENDING,
    REJECTED,
    DealSubmission,
)

AuditFn = Callable[[str, str, str, dict[str, Any]], Awaitable[None]]

REASON_MIN, REASON_MAX = 3, 500


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class ReviewSubmissionUseCase:
    def __init__(self, repo: Any, deal_service: Any, audit: AuditFn | None = None) -> None:
        self.repo = repo
        self.deal_service = deal_service
        self.audit = audit

    async def _load_pending(self, submission_id: str) -> DealSubmission:
        try:
            uuid.UUID(submission_id)
        except ValueError:
            raise NotFoundError("Propuesta no encontrada") from None
        submission = await self.repo.get(submission_id)
        if submission is None:
            raise NotFoundError("Propuesta no encontrada")
        if submission.status != PENDING:
            raise SubmissionNotPendingError()
        return submission

    async def approve(
        self, submission_id: str, admin_id: str, deal_in: DealCreate, amazon_tag: str
    ) -> Deal:
        submission = await self._load_pending(submission_id)
        external_id = deal_in.external_id or submission.asin
        link = canonicalize(extract_url(deal_in.affiliate_url), asin=external_id)
        ensure_not_shortened(link)

        if not await self.repo.claim_pending(submission_id, APPROVED):
            raise SubmissionNotPendingError()
        # claim_pending es un UPDATE masivo: el objeto cargado queda desfasado.
        submission.status = APPROVED

        payload = deal_in.model_dump(exclude_none=True)
        payload["source"] = "community"
        payload["affiliate_url"] = rewrite_affiliate_link(link, amazon_tag=amazon_tag).url
        if external_id:
            payload["external_id"] = external_id

        live = await self.repo.find_live_deal(external_id, link.canonical_url)
        if live is not None:
            raise DuplicateDealError(
                existing_id=live.id, existing_slug=live.slug, existing_title=live.title
            )

        for expired in await self.repo.find_expired_deals(external_id, link.canonical_url):
            await self.deal_service.delete_deal(expired.id)
            if self.audit is not None:
                await self.audit(
                    "deal.delete",
                    "deal",
                    str(expired.id),
                    {"reason": "replaced_by_submission", "submission_id": submission_id},
                )

        now = datetime.now(timezone.utc)
        if deal_in.scheduled_for is not None and _aware(deal_in.scheduled_for) > now:
            payload["status"] = "scheduled"

        deal = await self.deal_service.create_deal(payload, user_id=submission.user_id)
        submission.deal_id = deal.id
        submission.reviewed_by = admin_id
        submission.reviewed_at = now
        return deal

    async def reject(self, submission_id: str, admin_id: str, reason: str) -> DealSubmission:
        reason = (reason or "").strip()
        if not REASON_MIN <= len(reason) <= REASON_MAX:
            raise ValidationError(
                f"El motivo debe tener entre {REASON_MIN} y {REASON_MAX} caracteres"
            )
        submission = await self._load_pending(submission_id)
        if not await self.repo.claim_pending(submission_id, REJECTED):
            raise SubmissionNotPendingError()
        submission.status = REJECTED
        submission.rejection_reason = reason
        submission.reviewed_by = admin_id
        submission.reviewed_at = datetime.now(timezone.utc)
        return submission
