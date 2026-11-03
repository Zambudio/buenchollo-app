from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ValidationError
from app.modules.submissions.application.check_link import existing_deal_summary, resolve_link
from app.modules.submissions.domain.exceptions import SubmissionConflictError
from app.modules.submissions.domain.models import PENDING, DealSubmission
from app.modules.submissions.domain.rules import ensure_quota

if TYPE_CHECKING:
    from app.modules.submissions.api.schemas import SubmissionCreate


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
        if data.subcategory_id and await self.category_repo.get_by_id(data.subcategory_id) is None:
            raise ValidationError("La subcategoría seleccionada no existe")

    async def execute(self, user_id: str, data: "SubmissionCreate", amazon_tag: str) -> DealSubmission:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        ensure_quota(
            await self.repo.count_pending_by_user(user_id),
            await self.repo.count_since(user_id, since),
        )

        resolved = await resolve_link(
            data.url, self.repo, amazon_tag=amazon_tag, asin_resolver=self.asin_resolver
        )
        if resolved.status in ("published", "upcoming", "in_review"):
            existing = (
                existing_deal_summary(resolved.live_deal) if resolved.status == "published" else None
            )
            raise SubmissionConflictError(resolved.status, existing)

        await self._ensure_categories(data)

        link = resolved.link
        submission = DealSubmission(
            user_id=user_id,
            status=PENDING,
            original_url=data.url,
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
            raise SubmissionConflictError("in_review") from exc
