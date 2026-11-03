from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qsl, urlsplit

from app.modules.affiliates.domain.links import (
    CanonicalLink,
    clean_url,
    is_amazon_host,
)

AMAZON_FOREIGN_MARKETPLACE = "amazon_foreign_marketplace"
THIRD_PARTY_AFFILIATE_REMOVED = "third_party_affiliate_removed"
NOT_AFFILIABLE = "not_affiliable"

_AFFILIATE_PREFIXES = ("aff_", "affiliate")
_AFFILIATE_EXACT = frozenset({"clickref", "irclickid"})


class AffiliateRewriter(Protocol):
    def matches(self, link: CanonicalLink) -> bool: ...

    def rewrite(self, link: CanonicalLink) -> str: ...

    def warnings(self, link: CanonicalLink) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class RewriteResult:
    url: str
    warnings: tuple[str, ...]


def _has_affiliate_param(link: CanonicalLink) -> bool:
    amazon = is_amazon_host(link.host)
    for name, _ in parse_qsl(urlsplit(link.url).query, keep_blank_values=True):
        lowered = name.lower()
        if lowered in _AFFILIATE_EXACT or lowered.startswith(_AFFILIATE_PREFIXES):
            return True
        if lowered == "tag" and not amazon:
            return True
    return False


class AmazonEsRewriter:
    def __init__(self, tag: str) -> None:
        self._tag = tag

    def matches(self, link: CanonicalLink) -> bool:
        return link.host == "amazon.es" and link.asin is not None

    def rewrite(self, link: CanonicalLink) -> str:
        return f"{link.canonical_url}?tag={self._tag}"

    def warnings(self, link: CanonicalLink) -> tuple[str, ...]:
        return ()


class AmazonOtherRewriter:
    def matches(self, link: CanonicalLink) -> bool:
        return is_amazon_host(link.host)

    def rewrite(self, link: CanonicalLink) -> str:
        return link.canonical_url if link.asin else clean_url(link.url)

    def warnings(self, link: CanonicalLink) -> tuple[str, ...]:
        if link.asin and link.host != "amazon.es":
            return (AMAZON_FOREIGN_MARKETPLACE,)
        return (NOT_AFFILIABLE,)


class GenericRewriter:
    def matches(self, link: CanonicalLink) -> bool:
        return True

    def rewrite(self, link: CanonicalLink) -> str:
        return clean_url(link.url)

    def warnings(self, link: CanonicalLink) -> tuple[str, ...]:
        if _has_affiliate_param(link):
            return (THIRD_PARTY_AFFILIATE_REMOVED, NOT_AFFILIABLE)
        return (NOT_AFFILIABLE,)


REWRITERS: list[Callable[[str], AffiliateRewriter]] = [
    AmazonEsRewriter,
    lambda _tag: AmazonOtherRewriter(),
    lambda _tag: GenericRewriter(),
]


def rewrite_affiliate_link(link: CanonicalLink, *, amazon_tag: str) -> RewriteResult:
    for factory in REWRITERS:
        rewriter = factory(amazon_tag)
        if rewriter.matches(link):
            return RewriteResult(url=rewriter.rewrite(link), warnings=rewriter.warnings(link))
    raise RuntimeError("GenericRewriter debe aceptar cualquier enlace")
