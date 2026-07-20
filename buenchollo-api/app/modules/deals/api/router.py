import logging
from typing import Literal
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.deals.application.deal_service import DealService
from app.modules.deals.domain.exceptions import DealNotFound
from app.modules.deals.api.schemas import (
    DealCardResponse,
    DealCreate,
    DealDetailResponse,
    DealPageResponse,
    DealUpdate,
    VoteRequest,
    VoteResponse,
)
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
    subcategory_id: str | None = None,
    store_id: str | None = None,
    search: str | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_discount: int | None = Query(None, ge=0, le=100),
    sort: Literal["recent", "popular", "discount", "price_asc"] = "recent",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: DealRepository = Depends(get_deal_repository)
):
    return await repo.search_active(
        category_id=category_id,
        subcategory_id=subcategory_id,
        store_id=store_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/page", response_model=DealPageResponse)
async def get_deals_page(
    category_id: str | None = None,
    subcategory_id: str | None = None,
    store_id: str | None = None,
    search: str | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_discount: int | None = Query(None, ge=0, le=100),
    sort: Literal["recent", "popular", "discount", "price_asc"] = "popular",
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=48),
    repo: DealRepository = Depends(get_deal_repository),
):
    """Pagina estable de chollos filtrados, con total para el paginador."""
    filters = {
        "category_id": category_id,
        "subcategory_id": subcategory_id,
        "store_id": store_id,
        "search": search,
        "min_price": min_price,
        "max_price": max_price,
        "min_discount": min_discount,
    }
    total = await repo.count_active(**filters)
    total_pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(page, total_pages)
    items = await repo.search_active(
        **filters,
        sort=sort,
        limit=page_size,
        offset=(current_page - 1) * page_size,
    )
    return DealPageResponse(
        items=items,
        page=current_page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
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


@router.get("/my-votes")
async def get_my_votes_bulk(
    ids: str = Query(..., description="IDs de chollos separados por coma"),
    repo: DealRepository = Depends(get_deal_repository),
    current_user=Depends(get_current_user),
) -> dict[str, int]:
    """Votos del usuario actual para un lote de chollos (grid de portada/explorar),
    evitando una petición por tarjeta."""
    deal_ids = [d for d in ids.split(",") if d]
    return await repo.get_user_votes_bulk(deal_ids, str(current_user.id))


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
