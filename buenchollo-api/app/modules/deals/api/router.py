import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.deals.application.deal_service import DealService
from app.modules.deals.api.schemas import DealCardResponse, DealDetailResponse, DealCreate, DealUpdate, VoteRequest, VoteResponse
from app.core.security import require_admin, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deals", tags=["deals"])


def get_deal_repository(db: AsyncSession = Depends(get_db)) -> DealRepository:
    return DealRepository(db)


def get_deal_service(repo: DealRepository = Depends(get_deal_repository)) -> DealService:
    return DealService(repo)


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
    repo: DealRepository = Depends(get_deal_repository)
):
    return await repo.search_active(category_id=category_id, store_id=store_id, search=search, limit=limit)


# ── Endpoints autenticados ────────────────────────────────────────────────────

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
    current_user=Depends(require_admin)
):
    deal_data = deal_in.model_dump(exclude_none=True)
    return await service.create_deal(deal_data, str(current_user.id))


@router.put("/admin/{deal_id}", response_model=DealDetailResponse)
async def update_deal(
    deal_id: str,
    deal_in: DealUpdate,
    service: DealService = Depends(get_deal_service),
    _auth=Depends(require_admin)
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
