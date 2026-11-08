"""Adhesión a programas y guarda de publicación de chollos de redes."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from app.core.exceptions import ValidationError
from app.modules.affiliates.domain.models import (
    MEMBERSHIP_JOINED,
    MEMBERSHIP_NOT_JOINED,
    MEMBERSHIP_UNKNOWN,
    NETWORK_AWIN,
    NETWORK_TRADEDOUBLER,
    AffiliateProgram,
)
from app.modules.affiliates.domain.offers import (
    NETWORK_DATA_SOURCES,
    ProgramPolicy,
    PublishCandidate,
    describe_blockers,
    is_network_tracking_url,
    parse_money,
    publication_blockers,
)
from app.modules.affiliates.infrastructure.awin_client import AwinClient
from app.modules.affiliates.infrastructure.repository import AffiliateRepository
from app.modules.affiliates.infrastructure.tradedoubler_client import TradedoublerClient


class PublicationBlocked(ValidationError):
    """El chollo de una red de afiliación no cumple las reglas para publicarse."""

    def __init__(self, blockers: list[str]) -> None:
        self.blockers = blockers
        detail = "; ".join(b["message"] for b in describe_blockers(blockers))
        super().__init__(f"No se puede publicar todavía (guárdalo como borrador): {detail}.")


def policy_of(program: AffiliateProgram | None) -> ProgramPolicy:
    if program is None:
        return ProgramPolicy(False, MEMBERSHIP_UNKNOWN, (), 24)
    return ProgramPolicy(
        enabled=program.enabled,
        membership_status=program.membership_status,
        image_channels=tuple((program.restrictions or {}).get("image_channels") or ()),
        max_data_age_hours=program.max_data_age_hours,
    )


def candidate_from(data: dict) -> PublishCandidate:
    def dt(value):
        if value is None or isinstance(value, datetime):
            return value
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def money(value) -> Decimal | None:
        return parse_money(value) if value not in (None, "") else None

    return PublishCandidate(
        affiliate_url=data.get("affiliate_url"),
        title=data.get("title"),
        current_price=money(data.get("current_price")),
        previous_price=money(data.get("previous_price")),
        reference_type=data.get("price_reference_type"),
        reference_evidence=data.get("price_reference_evidence"),
        shipping_info=data.get("shipping_info"),
        short_description=data.get("short_description"),
        category_id=data.get("category_id"),
        image_url=data.get("image_url"),
        provider_updated_at=dt(data.get("data_provider_updated_at")),
        price_verified_at=dt(data.get("price_verified_at")),
    )


def needs_network_rules(data: dict) -> bool:
    return data.get("data_source") in NETWORK_DATA_SOURCES or bool(data.get("affiliate_program_id")) or is_network_tracking_url(
        data.get("affiliate_url")
    )


class PublicationGuard:
    """Usada por DealService (alta/edición) y por Telegram. Los borradores
    (`draft`) siempre se pueden guardar; publicar exige cumplir las reglas."""

    def __init__(self, repo: AffiliateRepository) -> None:
        self.repo = repo

    async def blockers_for(self, data: dict, now: datetime | None = None) -> list[str]:
        program = await self.repo.get_program(data["affiliate_program_id"]) if data.get("affiliate_program_id") else None
        return publication_blockers(candidate_from(data), policy_of(program), now or datetime.now(timezone.utc))

    async def ensure_publishable(self, data: dict) -> None:
        if data.get("status", "active") == "draft" or not needs_network_rules(data):
            return
        blockers = await self.blockers_for(data)
        if blockers:
            raise PublicationBlocked(blockers)


async def refresh_membership(repo: AffiliateRepository, awin: AwinClient, td: TradedoublerClient) -> list[dict]:
    """Consulta a las redes el estado real de adhesión. Awin: programmes por
    relación. Tradedoubler: un programa con feeds accesibles al token se marca
    `joined`; sin feeds no se deduce nada (queda como estaba si era manual)."""
    now = datetime.now(timezone.utc)
    programs = await repo.list_programs()
    report: list[dict] = []
    if awin.api_configured and any(p.network == NETWORK_AWIN for p in programs):
        relations = await asyncio.to_thread(awin.programmes_by_relationship, "ES")
        for p in (p for p in programs if p.network == NETWORK_AWIN):
            p.membership_status = relations.get(str(p.advertiser_id), MEMBERSHIP_NOT_JOINED)
            p.membership_checked_at, p.membership_source = now, "api"
            await repo.save(p)
            report.append({"program": p.name, "network": p.network, "membership_status": p.membership_status})
    if td.configured and any(p.network == NETWORK_TRADEDOUBLER for p in programs):
        feeds = await asyncio.to_thread(td.product_feeds)
        for p in (p for p in programs if p.network == NETWORK_TRADEDOUBLER):
            mine = [f for f in feeds if str(p.advertiser_id) in f["program_ids"]]
            known = {str(f.get("feed_id")): dict(f) for f in p.feeds or []}
            for f in mine:
                entry = known.setdefault(f["feed_id"], {"feed_id": f["feed_id"], "selected": False})
                entry.update({k: f[k] for k in ("name", "products", "last_imported", "language")})
                entry["available"] = True
            p.feeds = list(known.values())
            if mine:
                p.membership_status, p.membership_source = MEMBERSHIP_JOINED, "api_feeds"
            elif p.membership_source != "manual":
                p.membership_status, p.membership_source = MEMBERSHIP_UNKNOWN, "api_feeds"
            p.membership_checked_at = now
            await repo.save(p)
            report.append(
                {"program": p.name, "network": p.network, "membership_status": p.membership_status, "feeds": len(mine)}
            )
    return report
