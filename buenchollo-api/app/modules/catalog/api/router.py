from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import AuthenticatedUser, get_current_user
from app.modules.catalog.api.schemas import PriceHistoryResponse, TopProductResponse, VoteResponse
from app.modules.catalog.application.price_history_service import PriceHistoryService
from app.modules.catalog.domain.price_history import DEFAULT_WINDOW_DAYS
from app.modules.catalog.infrastructure.repository import CatalogRepository
from app.modules.catalog.application.top_service import TopService
from app.modules.catalog.infrastructure.top_repository import TopRepository

router = APIRouter(prefix="/catalog", tags=["catalog"])

# Coincide con el tamaño de lote que usa el frontend al consultar sus votos.
MAX_VOTE_LOOKUP = 50


def get_top_service(db: AsyncSession = Depends(get_db)) -> TopService:
    return TopService(TopRepository(db))


@router.get("/tops/{slug}", response_model=list[TopProductResponse])
async def list_top(slug: str, service: TopService = Depends(get_top_service)):
    return await service.list_top(slug)


@router.get("/my-votes", response_model=list[str])
async def my_votes(
    product_ids: list[UUID] = Query(default=[]),
    user: AuthenticatedUser = Depends(get_current_user),
    service: TopService = Depends(get_top_service),
):
    unique_ids = list(dict.fromkeys(str(product_id) for product_id in product_ids))[:MAX_VOTE_LOOKUP]
    return await service.my_votes(unique_ids, user.id)


@router.post("/products/{product_id}/vote", response_model=VoteResponse)
@limiter.limit("30/minute")
async def toggle_vote(
    request: Request,
    product_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: TopService = Depends(get_top_service),
):
    return {"voted": await service.toggle_vote(str(product_id), user.id)}


def get_price_history_service(db: AsyncSession = Depends(get_db)) -> PriceHistoryService:
    return PriceHistoryService(CatalogRepository(db))


@router.get("/products/{product_id}/price-history", response_model=PriceHistoryResponse)
@limiter.limit("60/minute")
async def price_history(
    request: Request,
    product_id: UUID,
    days: int = Query(DEFAULT_WINDOW_DAYS, ge=7, le=365),
    service: PriceHistoryService = Depends(get_price_history_service),
):
    """Histórico de precios del producto (todas sus tiendas): puntos de los
    últimos `days` días y estadísticas (el mínimo histórico abarca todo)."""
    view = await service.get(str(product_id), days)
    return {
        "product_id": view.product_id,
        "stats": asdict(view.stats),
        "points": [
            {"date": p.observed_on, "price": p.price, "low_price": p.low_price, "store_id": p.store_id}
            for p in view.points
        ],
    }
