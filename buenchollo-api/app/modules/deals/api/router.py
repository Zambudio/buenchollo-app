import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.deals.application.deal_service import DealService
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
        raise HTTPException(status_code=404, detail="Deal not found")
    if await repo.is_favorite(deal_id, user_id):
        await repo.remove_favorite(deal_id, user_id)
        return {"is_favorited": False}
    await repo.add_favorite(deal_id, user_id)
    return {"is_favorited": True}


@router.post("/{deal_id}/vote", response_model=VoteResponse)
async def vote_on_deal(
    deal_id: str,
    vote_in: VoteRequest,
    service: DealService = Depends(get_deal_service),
    current_user=Depends(get_current_user),
):
    deal = await service.repo.get_by_id(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
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


@router.get("/{slug}", response_model=DealDetailResponse)
async def get_deal_by_slug(
    slug: str,
    repo: DealRepository = Depends(get_deal_repository)
):
    deal = await repo.get_by_slug(slug)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
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
    service: DealService = Depends(get_deal_service),
    current_user=Depends(require_admin),
):
    return await service.create_deal(deal_in.model_dump(exclude_none=True), str(current_user.id))


@router.put("/admin/{deal_id}", response_model=DealDetailResponse)
async def update_deal(
    deal_id: str,
    deal_in: DealUpdate,
    service: DealService = Depends(get_deal_service),
    _auth=Depends(require_admin),
):
    updated = await service.update_deal(deal_id, deal_in.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Deal not found")
    return updated


@router.delete("/admin/{deal_id}", status_code=204)
async def delete_deal(
    deal_id: str,
    service: DealService = Depends(get_deal_service),
    _auth=Depends(require_admin)
):
    deleted = await service.delete_deal(deal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Deal not found")
