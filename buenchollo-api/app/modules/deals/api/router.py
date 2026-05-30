import logging
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.deals.application.deal_service import DealService
from app.modules.deals.domain.exceptions import DealNotFound
from app.modules.deals.api.schemas import DealCardResponse, DealDetailResponse, DealCreate, DealUpdate, VoteRequest, VoteResponse
from app.core.security import require_admin, get_current_user
from app.modules.alerts.infrastructure.repository import AlertRepository
from app.modules.alerts.application.alert_matcher import AlertMatcher
from app.modules.notifications.infrastructure.repository import NotificationRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deals", tags=["deals"])


def get_deal_repository(db: AsyncSession = Depends(get_db)) -> DealRepository:
    return DealRepository(db)


def get_deal_service(db: AsyncSession = Depends(get_db)) -> DealService:
    """Construye DealService con su repo y AlertMatcher inyectado. Toda la
    orquestación (incluida la notificación de alertas) queda en la capa de
    aplicación; el router se limita a hablar HTTP."""
    repo = DealRepository(db)
    matcher = AlertMatcher(AlertRepository(db), NotificationRepository(db))
    return DealService(repo, matcher)


# ── Endpoints públicos ────────────────────────────────────────────────────────

@router.get("/latest", response_model=list[DealCardResponse])
async def get_latest_deals(
    limit: int = Query(8, ge=1, le=50),
    repo: DealRepository = Depends(get_deal_repository)
):
    return await repo.get_latest_active(limit=limit)


@router.get("/popular", response_model=list[DealCardResponse])
async def get_popular_deals(
    limit: int = Query(4, ge=1, le=50),
    repo: DealRepository = Depends(get_deal_repository)
):
    return await repo.get_popular_active(limit=limit)


@router.get("", response_model=list[DealCardResponse])
async def search_deals(
    category_id: str | None = None,
    store_id: str | None = None,
    search: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: DealRepository = Depends(get_deal_repository)
):
    return await repo.search_active(
        category_id=category_id, store_id=store_id, search=search, limit=limit, offset=offset
    )


# ── Endpoints autenticados ────────────────────────────────────────────────────

@router.get("/favorites", response_model=list[DealCardResponse])
async def get_favorites(
    repo: DealRepository = Depends(get_deal_repository),
    current_user=Depends(get_current_user),
):
    return await repo.get_favorites(str(current_user.id))


@router.get("/{deal_id}/favorite")
async def get_favorite_status(
    deal_id: str,
    repo: DealRepository = Depends(get_deal_repository),
    current_user=Depends(get_current_user),
) -> dict:
    is_fav = await repo.is_favorite(deal_id, str(current_user.id))
    return {"is_favorited": is_fav}


@router.post("/{deal_id}/favorite")
async def toggle_favorite(
    deal_id: str,
    repo: DealRepository = Depends(get_deal_repository),
    current_user=Depends(get_current_user),
) -> dict:
    user_id = str(current_user.id)
    deal = await repo.get_by_id(deal_id)
    if not deal:
        raise DealNotFound(deal_id)
    if await repo.is_favorite(deal_id, user_id):
        await repo.remove_favorite(deal_id, user_id)
        return {"is_favorited": False}
    await repo.add_favorite(deal_id, user_id)
    return {"is_favorited": True}


@router.post("/{deal_id}/vote", response_model=VoteResponse)
@limiter.limit("30/minute")  # anti-spam de votos
async def vote_on_deal(
    request: Request,
    deal_id: str,
    vote_in: VoteRequest,
    service: DealService = Depends(get_deal_service),
    current_user=Depends(get_current_user),
):
    deal = await service.repo.get_by_id(deal_id)
    if not deal:
        raise DealNotFound(deal_id)
    result = await service.process_vote(deal_id, str(current_user.id), vote_in.vote)
    return VoteResponse(**result)


@router.get("/{deal_id}/my-vote")
async def get_my_vote(
    deal_id: str,
    repo: DealRepository = Depends(get_deal_repository),
    current_user=Depends(get_current_user),
) -> dict:
    my_vote = await repo.get_user_vote(deal_id, str(current_user.id))
    return {"my_vote": my_vote or 0}


@router.post("/{deal_id}/click")
@limiter.limit("60/minute")  # anti-spam de contadores; endpoint público sin auth
async def track_click(
    request: Request,
    deal_id: str,
    repo: DealRepository = Depends(get_deal_repository),
) -> dict:
    """Incrementa el contador de clicks del chollo. Endpoint público (lo dispara
    cualquier visitante al pulsar el enlace de afiliado)."""
    new_count = await repo.increment_click_count(deal_id)
    if new_count is None:
        raise DealNotFound(deal_id)
    return {"click_count": new_count}


@router.get("/{slug}", response_model=DealDetailResponse)
async def get_deal_by_slug(
    slug: str,
    repo: DealRepository = Depends(get_deal_repository)
):
    deal = await repo.get_by_slug(slug)
    if not deal:
        raise DealNotFound(slug)
    return deal


# ── Endpoints admin ───────────────────────────────────────────────────────────

@router.get("/admin/all", response_model=list[DealDetailResponse])
async def get_all_admin_deals(
    status: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    repo: DealRepository = Depends(get_deal_repository),
    _auth=Depends(require_admin)
):
    return await repo.get_all_admin(status=status, limit=limit)


@router.post("/admin", response_model=DealDetailResponse)
async def create_deal(
    deal_in: DealCreate,
    db: AsyncSession = Depends(get_db),
    service: DealService = Depends(get_deal_service),
    current_user=Depends(require_admin),
):
    payload = deal_in.model_dump(exclude_none=True)
    created = await service.create_deal(payload, str(current_user.id))
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="deal.create",
        target_type="deal",
        target_id=str(created.id),
        payload={"title": created.title, "status": created.status, "store_id": payload.get("store_id")},
    )
    return created


@router.put("/admin/{deal_id}", response_model=DealDetailResponse)
async def update_deal(
    deal_id: str,
    deal_in: DealUpdate,
    db: AsyncSession = Depends(get_db),
    service: DealService = Depends(get_deal_service),
    current_user=Depends(require_admin),
):
    diff = deal_in.model_dump(exclude_unset=True)
    updated = await service.update_deal(deal_id, diff)
    if not updated:
        raise DealNotFound(deal_id)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="deal.update",
        target_type="deal",
        target_id=deal_id,
        payload={"changed_fields": list(diff.keys())},
    )
    return updated


@router.delete("/admin/{deal_id}", status_code=204)
async def delete_deal(
    deal_id: str,
    db: AsyncSession = Depends(get_db),
    service: DealService = Depends(get_deal_service),
    current_user=Depends(require_admin),
):
    deleted = await service.delete_deal(deal_id)
    if not deleted:
        raise DealNotFound(deal_id)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="deal.delete",
        target_type="deal",
        target_id=deal_id,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint ONE-SHOT — eliminar tras usar
# ──────────────────────────────────────────────────────────────────────────────
#
# Backfill de external_id (ASIN) para chollos antiguos publicados antes de
# que se guardara el ASIN al crearlos. La inmensa mayoría usan affiliate
# links acortados (amzn.to/xxx) que no contienen el ASIN inline: hay que
# seguir el redirect para extraerlo. `extract_asin_from_url` ya lo hace.
#
# Llamar UNA sola vez desde el botón del panel admin. Después borrar este
# endpoint y el botón para no dejar superficie de ataque innecesaria.
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/admin/backfill-external-ids", include_in_schema=False)
async def backfill_external_ids(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    import asyncio
    from sqlalchemy import select, update
    from app.modules.products.infrastructure.amazon_client import extract_asin_from_url
    from app.modules.deals.domain.models import Deal

    result = await db.execute(
        select(Deal.id, Deal.title, Deal.affiliate_url)
        .where(Deal.external_id.is_(None))
        .where(Deal.affiliate_url.is_not(None))
    )
    rows = result.all()

    updated = 0
    failed: list[dict] = []
    seen_asins: dict[str, str] = {}

    for row in rows:
        try:
            # extract_asin_from_url usa urllib síncrono → lo lanzamos en un
            # thread para no bloquear el event loop. ~1s por URL acortada.
            asin = await asyncio.to_thread(extract_asin_from_url, row.affiliate_url)
        except Exception as e:  # noqa: BLE001
            failed.append({"id": str(row.id), "title": row.title, "reason": f"error de red: {e}"})
            continue
        if not asin:
            failed.append({"id": str(row.id), "title": row.title, "reason": "no se pudo extraer ASIN"})
            continue
        if asin in seen_asins:
            failed.append({
                "id": str(row.id),
                "title": row.title,
                "reason": f"colisión con deal {seen_asins[asin]} (mismo ASIN {asin})",
            })
            continue
        seen_asins[asin] = str(row.id)
        await db.execute(update(Deal).where(Deal.id == row.id).values(external_id=asin))
        updated += 1

    await db.commit()

    await audit_log(
        db,
        user_id=str(current_user.id),
        action="deal.backfill_external_ids",
        target_type="deal",
        target_id=None,
        payload={"processed": len(rows), "updated": updated, "failed_count": len(failed)},
    )

    return {"processed": len(rows), "updated": updated, "failed": failed}
