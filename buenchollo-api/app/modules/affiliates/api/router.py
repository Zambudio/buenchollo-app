"""Endpoints admin de redes de afiliación (Awin / Tradedoubler).

Todo exige `require_admin`; las credenciales viven solo en el servidor y no
aparecen en ninguna respuesta (solo booleanos de "configurado").
"""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.rate_limit import limiter
from app.core.security import require_admin
from app.modules.affiliates.api.schemas import (
    ImportRequestIn,
    ImportResponse,
    IntegrationStatus,
    ProgramResponse,
    ProgramWrite,
    ReadinessRequest,
    ReadinessResponse,
    SyncRequest,
)
from app.modules.affiliates.application.feed_sync_job import run_awin_feed_sync_async
from app.modules.affiliates.application.import_offer import ImportOfferUseCase, ImportRequest, result_to_dict
from app.modules.affiliates.application.programs import (
    PublicationGuard,
    candidate_from,
    needs_network_rules,
    refresh_membership,
)
from app.modules.affiliates.domain.models import AffiliateProgram
from app.modules.affiliates.domain.offers import describe_blockers, savings
from app.modules.affiliates.infrastructure.awin_client import AwinClient
from app.modules.affiliates.infrastructure.repository import AffiliateRepository
from app.modules.affiliates.infrastructure.tradedoubler_client import TradedoublerClient

router = APIRouter(prefix="/affiliates", tags=["affiliates"], dependencies=[Depends(require_admin)])


class ProgramNotFound(NotFoundError):
    """Programa de afiliación inexistente."""


def get_repo(db: AsyncSession = Depends(get_db)) -> AffiliateRepository:
    return AffiliateRepository(db)


@router.get("/status", response_model=IntegrationStatus)
async def integration_status(settings: Settings = Depends(get_settings)) -> IntegrationStatus:
    return IntegrationStatus(
        awin_publisher_api=bool(settings.awin_publisher_id and settings.awin_access_token),
        awin_feeds=bool(settings.awin_publisher_id and settings.awin_feed_api_key),
        tradedoubler_products=bool(settings.tradedoubler_products_token),
        tradedoubler_site_id=bool(settings.tradedoubler_site_id),
    )


@router.get("/programs", response_model=list[ProgramResponse])
async def list_programs(repo: AffiliateRepository = Depends(get_repo)):
    return await repo.list_programs()


def _apply(program: AffiliateProgram, data: ProgramWrite) -> list[str]:
    changes = data.model_dump(exclude_unset=True)
    now = datetime.now(timezone.utc)
    if "membership_status" in changes:
        program.membership_status = changes.pop("membership_status")
        program.membership_checked_at, program.membership_source = now, "manual"
    if "selected_feed_ids" in changes:
        selected = set(changes.pop("selected_feed_ids") or [])
        feeds = [dict(f) for f in program.feeds or []]
        known = {str(f.get("feed_id")) for f in feeds}
        feeds += [{"feed_id": fid, "selected": False} for fid in selected - known]
        for feed in feeds:
            feed["selected"] = str(feed.get("feed_id")) in selected
        program.feeds = feeds
    if "deeplink_verified" in changes:
        program.deeplink_verified_at = now if changes.pop("deeplink_verified") else None
    if "restrictions" in changes:
        program.restrictions = changes.pop("restrictions") or {}
    for field, value in changes.items():
        setattr(program, field, value)
    return list(data.model_dump(exclude_unset=True).keys())


@router.post("/programs", response_model=ProgramResponse, status_code=201)
async def create_program(
    data: ProgramWrite,
    db: AsyncSession = Depends(get_db),
    repo: AffiliateRepository = Depends(get_repo),
    current_user=Depends(require_admin),
):
    if not (data.network and data.advertiser_id and data.name):
        from app.core.exceptions import ValidationError

        raise ValidationError("network, advertiser_id y name son obligatorios.")
    program = AffiliateProgram(network=data.network, advertiser_id=data.advertiser_id, name=data.name, domains=[], feeds=[])
    _apply(program, data)
    program = await repo.save(program)
    await audit_log(db, user_id=str(current_user.id), action="affiliate_program.create", target_type="affiliate_program",
                    target_id=program.id, payload={"network": program.network, "advertiser_id": program.advertiser_id})
    return program


@router.put("/programs/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: str,
    data: ProgramWrite,
    db: AsyncSession = Depends(get_db),
    repo: AffiliateRepository = Depends(get_repo),
    current_user=Depends(require_admin),
):
    program = await repo.get_program(program_id)
    if program is None:
        raise ProgramNotFound("Programa no encontrado")
    changed = _apply(program, data)
    program = await repo.save(program)
    await audit_log(db, user_id=str(current_user.id), action="affiliate_program.update", target_type="affiliate_program",
                    target_id=program_id, payload={"changed_fields": changed})
    return program


@router.post("/programs/refresh-membership")
@limiter.limit("3/minute")
async def refresh_programs_membership(
    request: Request, repo: AffiliateRepository = Depends(get_repo), settings: Settings = Depends(get_settings)
) -> dict:
    awin, td = AwinClient(settings), TradedoublerClient(settings)
    try:
        return {"results": await refresh_membership(repo, awin, td)}
    finally:
        awin.http.close()
        td.http.close()


@router.post("/feeds/sync", status_code=202)
@limiter.limit("2/minute")
async def sync_feeds(
    request: Request,
    payload: SyncRequest,
    background: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Lanza la sincronización en segundo plano; nunca dentro de la petición."""
    background.add_task(run_awin_feed_sync_async, settings, program_id=payload.program_id, force=payload.force)
    return {"accepted": True}


@router.post("/import", response_model=ImportResponse)
@limiter.limit("20/minute")
async def import_offer(
    request: Request,
    payload: ImportRequestIn,
    repo: AffiliateRepository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
) -> dict:
    awin, td = AwinClient(settings), TradedoublerClient(settings)
    try:
        result = await ImportOfferUseCase(repo, awin, td).execute(
            ImportRequest(
                url=payload.url,
                program_id=payload.program_id,
                product_key=payload.product_key,
                ean=payload.ean,
                sku=payload.sku,
                link_only=payload.link_only,
            )
        )
    finally:
        awin.http.close()
        td.http.close()
    return result_to_dict(result)


@router.post("/readiness", response_model=ReadinessResponse)
async def readiness(payload: ReadinessRequest, repo: AffiliateRepository = Depends(get_repo)) -> ReadinessResponse:
    data = payload.model_dump()
    if not needs_network_rules(data):
        return ReadinessResponse(applies=False, ready=True, blockers=[])
    blockers = await PublicationGuard(repo).blockers_for(data)
    c = candidate_from(data)
    calc = savings(c.current_price, c.previous_price)
    return ReadinessResponse(
        applies=True,
        ready=not blockers,
        blockers=describe_blockers(blockers),
        savings_amount=f"{calc[0]:.2f}" if calc else None,
        discount_percentage=calc[1] if calc else None,
    )
