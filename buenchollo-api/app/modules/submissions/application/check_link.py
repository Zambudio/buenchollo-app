import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from app.modules.affiliates.domain.links import (
    CanonicalLink,
    InvalidLinkError,
    canonicalize,
    ensure_not_shortened,
    extract_url,
    is_amazon_host,
    is_amazon_short_host,
)
from app.modules.affiliates.domain.rewriters import RewriteResult, rewrite_affiliate_link
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


@dataclass
class ResolvedLink:
    status: LinkStatus
    link: CanonicalLink
    rewritten: RewriteResult
    is_amazon: bool
    store: Any | None
    store_name: str | None
    live_deal: Any | None = None
    previously_published: bool = False


async def _resolve_short_link(
    url: str, asin_resolver: Callable[[str], str | None] | None
) -> CanonicalLink:
    asin = None
    if asin_resolver is not None:
        try:
            asin = await asyncio.to_thread(asin_resolver, url)
        except Exception:
            logger.warning("No se pudo resolver el enlace corto de Amazon", exc_info=True)
    if not asin:
        raise InvalidLinkError("No hemos podido leer ese enlace de Amazon")
    return canonicalize(f"https://www.amazon.es/dp/{asin}")


async def canonical_link(
    raw_url: str, asin_resolver: Callable[[str], str | None] | None = None
) -> CanonicalLink:
    """Normaliza el enlace sin tocar la BD (puede hacer red: enlaces cortos)."""
    url = extract_url(raw_url)
    link = canonicalize(url)
    ensure_not_shortened(link)
    if is_amazon_short_host(link.host):
        link = await _resolve_short_link(url, asin_resolver)
    return link


async def resolve_link(
    raw_url: str,
    repo: Any,
    *,
    amazon_tag: str = "",
    asin_resolver: Callable[[str], str | None] | None = None,
    link: CanonicalLink | None = None,
) -> ResolvedLink:
    if link is None:
        link = await canonical_link(raw_url, asin_resolver)

    is_amazon = is_amazon_host(link.host)
    rewritten = rewrite_affiliate_link(link, amazon_tag=amazon_tag)
    store = await repo.find_store_by_host(link.host)
    resolved = ResolvedLink(
        status="ok",
        link=link,
        rewritten=rewritten,
        is_amazon=is_amazon,
        store=store,
        store_name=store.name if store else ("Amazon" if is_amazon else None),
    )

    live = await repo.find_live_deal(link.asin, link.canonical_url)
    if live is not None:
        resolved.status = "published" if live.status == "active" else "upcoming"
        resolved.live_deal = live
        return resolved

    if await repo.find_pending(link.asin, link.canonical_url) is not None:
        resolved.status = "in_review"
        return resolved

    resolved.previously_published = (
        await repo.find_expired_deal(link.asin, link.canonical_url) is not None
    )
    return resolved


def existing_deal_summary(deal: Any) -> dict[str, Any]:
    return {
        "id": deal.id,
        "slug": deal.slug,
        "title": deal.title,
        "image_url": deal.image_url,
        "current_price": float(deal.current_price),
    }


class CheckLinkUseCase:
    def __init__(
        self,
        repo: Any,
        product_provider: ProductPreviewProvider | None,
        *,
        amazon_tag: str = "",
        asin_resolver: Callable[[str], str | None] | None = None,
        release_db: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self.repo = repo
        self.product_provider = product_provider
        self.amazon_tag = amazon_tag
        self.asin_resolver = asin_resolver
        self.release_db = release_db

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
        resolved = await resolve_link(
            raw_url, self.repo, amazon_tag=self.amazon_tag, asin_resolver=self.asin_resolver
        )
        link = resolved.link
        result = LinkCheckResult(
            status=resolved.status,
            canonical_url=link.canonical_url,
            affiliate_url=resolved.rewritten.url,
            asin=link.asin,
            store_id=resolved.store.id if resolved.store else None,
            store_name=resolved.store_name,
            is_amazon=resolved.is_amazon,
            previously_published=resolved.previously_published,
            warnings=list(resolved.rewritten.warnings),
        )
        if resolved.status == "published":
            result.existing_deal = existing_deal_summary(resolved.live_deal)
        elif resolved.status == "ok" and resolved.is_amazon:
            # Libera la conexión antes de la llamada lenta a Amazon. Tras el
            # rollback los objetos ORM quedan expirados: el resultado ya está
            # construido solo con escalares.
            if self.release_db is not None:
                await self.release_db()
            result.prefill = await self._fetch_prefill(link)
        return result
