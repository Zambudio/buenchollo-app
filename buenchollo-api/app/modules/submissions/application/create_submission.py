from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ValidationError
from app.modules.affiliates.domain.links import extract_url
from app.modules.submissions.application.check_link import (
    canonical_link,
    existing_deal_summary,
    resolve_link,
)
from app.modules.submissions.domain.exceptions import SubmissionConflictError
from app.modules.submissions.domain.models import PENDING, DealSubmission
from app.modules.submissions.domain.rules import ensure_quota

if TYPE_CHECKING:
    from app.modules.submissions.api.schemas import SubmissionCreate


PENDING_UNIQUE_CONSTRAINTS = (
    "uq_deal_submissions_pending_asin",
    "uq_deal_submissions_pending_canonical",
)


def _is_pending_conflict(exc: IntegrityError) -> bool:
    orig = exc.orig
    names = {
        getattr(orig, "constraint_name", None),
        getattr(getattr(orig, "__cause__", None), "constraint_name", None),
    }
    if names & set(PENDING_UNIQUE_CONSTRAINTS):
        return True
    return any(name in str(orig) for name in PENDING_UNIQUE_CONSTRAINTS)


class CreateSubmissionUseCase:
    def __init__(
        self,
        repo: Any,
        category_repo: Any,
        *,
        asin_resolver: Callable[[str], str | None] | None = None,
    ) -> None:
        self.repo = repo
        self.category_repo = category_repo
        self.asin_resolver = asin_resolver

    async def _ensure_categories(self, data: "SubmissionCreate") -> None:
        if await self.category_repo.get_by_id(data.category_id) is None:
            raise ValidationError("La categoría seleccionada no existe")
        if data.subcategory_id:
            sub = await self.category_repo.get_by_id(data.subcategory_id)
            if sub is None:
                raise ValidationError("La subcategoría seleccionada no existe")
            if str(sub.parent_id) != str(data.category_id):
                raise ValidationError("La subcategoría no pertenece a la categoría seleccionada")

    async def execute(self, user_id: str, data: "SubmissionCreate", amazon_tag: str) -> DealSubmission:
        # Primero la parte sin BD (puede resolver un enlace corto por red), para
        # no retener una conexión del pool durante esa espera.
        link = await canonical_link(data.url, self.asin_resolver)

        since = datetime.now(timezone.utc) - timedelta(hours=24)
        ensure_quota(
            await self.repo.count_pending_by_user(user_id),
            await self.repo.count_since(user_id, since),
        )

        resolved = await resolve_link(data.url, self.repo, amazon_tag=amazon_tag, link=link)
        if resolved.status in ("published", "upcoming", "in_review"):
            existing = (
                existing_deal_summary(resolved.live_deal) if resolved.status == "published" else None
            )
            raise SubmissionConflictError(resolved.status, existing)

        await self._ensure_categories(data)

        submission = DealSubmission(
            user_id=user_id,
            status=PENDING,
            original_url=extract_url(data.url),
            canonical_url=link.canonical_url,
            affiliate_url=resolved.rewritten.url,
            asin=link.asin,
            store_id=resolved.store.id if resolved.store else None,
            store_name=data.store_name or resolved.store_name,
            title=data.title,
            description=data.description,
            current_price=data.current_price,
            previous_price=data.previous_price,
            coupon_code=data.coupon_code,
            shipping_info=data.shipping_info,
            starts_at=data.starts_at,
            expires_at=data.expires_at,
            category_id=data.category_id,
            subcategory_id=data.subcategory_id,
            image_url=data.image_url,
            images=list(data.images),
            warnings=list(resolved.rewritten.warnings),
        )
        try:
            return await self.repo.add(submission)
        except IntegrityError as exc:
            if not _is_pending_conflict(exc):
                raise
            raise SubmissionConflictError("in_review") from exc
