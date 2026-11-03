import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from app.modules.affiliates.domain.links import (
    InvalidLinkError,
    canonicalize,
    extract_url,
    is_amazon_host,
    is_amazon_short_host,
)
from app.modules.affiliates.domain.rewriters import rewrite_affiliate_link
from app.modules.products.application.preview_product_from_url import ProductPreviewProvider
from app.modules.submissions.domain.rules import features_to_markdown

logger = logging.getLogger(__name__)

LinkStatus = Literal["published", "upcoming", "in_review", "ok"]


@dataclass
class SubmissionPrefill:
    title: str
    brand: str
    description: str
    current_price: float | None
    previous_price: float | None
    image_url: str
    images: list[str]
    expires_at: datetime | None


@dataclass
class LinkCheckResult:
    status: LinkStatus
    canonical_url: str
    affiliate_url: str
    asin: str | None
    store_id: str | None
    store_name: str | None
    is_amazon: bool
    previously_published: bool = False
    existing_deal: dict[str, Any] | None = None
    prefill: SubmissionPrefill | None = None
    warnings: list[str] = field(default_factory=list)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _build_prefill(product: Any) -> SubmissionPrefill:
    current = product.current_price
    previous = product.original_price
    if current is None or previous is None or previous <= current:
        previous = None
    description = features_to_markdown(product.features or []) or (product.description or "")
    return SubmissionPrefill(
        title=product.title or "",
        brand=product.brand or "",
        description=description,
        current_price=float(current) if current is not None else None,
        previous_price=float(previous) if previous is not None else None,
        image_url=product.image_url or "",
        images=list(product.images or []),
        expires_at=_parse_dt(product.expires_at),
    )


class CheckLinkUseCase:
    def __init__(
        self,
        repo: Any,
        product_provider: ProductPreviewProvider | None,
        *,
        amazon_tag: str = "",
        asin_resolver: Callable[[str], str | None] | None = None,
    ) -> None:
        self.repo = repo
        self.product_provider = product_provider
        self.amazon_tag = amazon_tag
        self.asin_resolver = asin_resolver

    async def _resolve_short_link(self, url: str):
        asin = None
        if self.asin_resolver is not None:
            try:
                asin = await asyncio.to_thread(self.asin_resolver, url)
            except Exception:
                logger.warning("No se pudo resolver el enlace corto de Amazon", exc_info=True)
        if not asin:
            raise InvalidLinkError("No hemos podido leer ese enlace de Amazon")
        return canonicalize(f"https://www.amazon.es/dp/{asin}")

    async def _fetch_prefill(self, link) -> SubmissionPrefill | None:
        if self.product_provider is None:
            return None
        try:
            product = await asyncio.to_thread(
                self.product_provider.get_product_preview, link.asin or link.canonical_url
            )
        except Exception:
            logger.warning("Amazon no disponible para el prefill", exc_info=True)
            return None
        if product is None:
            return None
        return _build_prefill(product)

    async def execute(self, raw_url: str) -> LinkCheckResult:
        url = extract_url(raw_url)
        link = canonicalize(url)
        if is_amazon_short_host(link.host):
            link = await self._resolve_short_link(url)

        is_amazon = is_amazon_host(link.host)
        rewritten = rewrite_affiliate_link(link, amazon_tag=self.amazon_tag)
        store = await self.repo.find_store_by_host(link.host)
        store_name = store.name if store else ("Amazon" if is_amazon else None)

        result = LinkCheckResult(
            status="ok",
            canonical_url=link.canonical_url,
            affiliate_url=rewritten.url,
            asin=link.asin,
            store_id=store.id if store else None,
            store_name=store_name,
            is_amazon=is_amazon,
            warnings=list(rewritten.warnings),
        )

        live = await self.repo.find_live_deal(link.asin, link.canonical_url)
        if live is not None:
            if live.status == "active":
                result.status = "published"
                result.existing_deal = {
                    "id": live.id,
                    "slug": live.slug,
                    "title": live.title,
                    "image_url": live.image_url,
                    "current_price": float(live.current_price),
                }
            else:
                result.status = "upcoming"
            return result

        if await self.repo.find_pending(link.asin, link.canonical_url) is not None:
            result.status = "in_review"
            return result

        result.previously_published = (
            await self.repo.find_expired_deal(link.asin, link.canonical_url) is not None
        )
        if is_amazon:
            result.prefill = await self._fetch_prefill(link)
        return result
