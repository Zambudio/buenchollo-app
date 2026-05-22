import logging
import re
import time
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.deals.infrastructure.repository import DealRepository
from app.modules.deals.api.schemas import DealCardResponse, DealDetailResponse, DealCreate, DealUpdate, VoteRequest, VoteResponse
from app.modules.deals.domain.models import Deal
from app.core.security import require_admin, get_current_user

logger = logging.getLogger(__name__)


def _auto_slug(title: str) -> str:
    """Genera un slug URL-safe desde el título como fallback del backend."""
    slug = title.lower().strip()
    # Normalizar caracteres acentuados
    for src, dst in [("áàäâ", "a"), ("éèëê", "e"), ("íìïî", "i"), ("óòöô", "o"), ("úùüû", "u"), ("ñ", "n")]:
        for ch in src:
            slug = slug.replace(ch, dst)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return f"{slug}-{int(time.time() * 1000):x}"

router = APIRouter(prefix="/deals", tags=["deals"])

def get_deal_repository(db: AsyncSession = Depends(get_db)) -> DealRepository:
    return DealRepository(db)

@router.get("/latest", response_model=list[DealCardResponse])
async def get_latest_deals(
    limit: int = Query(8, ge=1, le=50),
    repo: DealRepository = Depends(get_deal_repository)
) -> list[DealCardResponse]:
    """Retrieve the latest active deals."""
    deals = await repo.get_latest_active(limit=limit)
    return deals

@router.get("/popular", response_model=list[DealCardResponse])
async def get_popular_deals(
    limit: int = Query(4, ge=1, le=50),
    repo: DealRepository = Depends(get_deal_repository)
) -> list[DealCardResponse]:
    """Retrieve the most popular deals based on temperature."""
    deals = await repo.get_popular_active(limit=limit)
    return deals

@router.get("", response_model=list[DealCardResponse])
async def search_deals(
    category_id: str | None = None,
    store_id: str | None = None,
    search: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    repo: DealRepository = Depends(get_deal_repository)
) -> list[DealCardResponse]:
    """Retrieve active deals with optional filtering."""
    deals = await repo.search_active(
        category_id=category_id,
        store_id=store_id,
        search=search,
        limit=limit
    )
    return deals

@router.post("/{deal_id}/vote", response_model=VoteResponse)
async def vote_on_deal(
    deal_id: str,
    vote_in: VoteRequest,
    repo: DealRepository = Depends(get_deal_repository),
    current_user = Depends(get_current_user),
) -> VoteResponse:
    """Votar en un chollo (👍/👎). Repetir el mismo voto lo anula (toggle off)."""
    deal = await repo.get_by_id(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    user_id = str(current_user.id)
    current_vote = await repo.get_user_vote(deal_id, user_id)

    if current_vote == vote_in.vote:
        await repo.delete_vote(deal_id, user_id)
        my_vote = 0
    else:
        await repo.upsert_vote(deal_id, user_id, vote_in.vote)
        my_vote = vote_in.vote

    # Recalcular contadores directamente desde deal_votes y actualizar deals en un solo paso.
    # No dependemos del trigger trg_votes_recalc (problemas de visibilidad en asyncpg).
    row = (await repo.session.execute(
        text("""
            UPDATE deals SET
                votes_up    = (SELECT COUNT(*) FROM deal_votes WHERE deal_id = CAST(:id AS uuid) AND vote = 1),
                votes_down  = (SELECT COUNT(*) FROM deal_votes WHERE deal_id = CAST(:id AS uuid) AND vote = -1),
                temperature = (SELECT COALESCE(SUM(vote), 0) FROM deal_votes WHERE deal_id = CAST(:id AS uuid))
            WHERE id = CAST(:id AS uuid)
            RETURNING temperature, votes_up, votes_down
        """),
        {"id": deal_id},
    )).mappings().first()
    return VoteResponse(
        temperature=row["temperature"] if row else 0,
        votes_up=row["votes_up"] if row else 0,
        votes_down=row["votes_down"] if row else 0,
        my_vote=my_vote,
    )


@router.get("/{deal_id}/my-vote")
async def get_my_vote(
    deal_id: str,
    repo: DealRepository = Depends(get_deal_repository),
    current_user = Depends(get_current_user),
) -> dict:
    """Devuelve el voto actual del usuario para un chollo (-1, 0 o 1)."""
    user_id = str(current_user.id)
    my_vote = await repo.get_user_vote(deal_id, user_id)
    return {"my_vote": my_vote or 0}


@router.get("/{slug}", response_model=DealDetailResponse)
async def get_deal_by_slug(
    slug: str,
    repo: DealRepository = Depends(get_deal_repository)
) -> DealDetailResponse:
    """Retrieve a deal by its slug."""
    deal = await repo.get_by_slug(slug)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal

@router.get("/admin/all", response_model=list[DealDetailResponse])
async def get_all_admin_deals(
    status: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    repo: DealRepository = Depends(get_deal_repository),
    _auth = Depends(require_admin)
) -> list[DealDetailResponse]:
    """Admin: Retrieve all deals."""
    deals = await repo.get_all_admin(status=status, limit=limit)
    return deals

@router.post("/admin", response_model=DealDetailResponse)
async def create_deal(
    deal_in: DealCreate,
    repo: DealRepository = Depends(get_deal_repository),
    current_user = Depends(require_admin)
) -> DealDetailResponse:
    """Admin: Create a new deal."""
    # exclude_none=True evita pasar NULL explícito a campos con server_default en la BD
    # (p.ej. published_at, created_at), dejando que PostgreSQL aplique sus defaults.
    deal_data = deal_in.model_dump(exclude_none=True)

    # Slug fallback: si el cliente no lo envió, lo generamos en el servidor
    if not deal_data.get("slug"):
        deal_data["slug"] = _auto_slug(deal_data["title"])

    # FK created_by: solo asignamos el user_id si el perfil existe en la BD
    # para evitar IntegrityError por violación de FK con la tabla profiles.
    user_id = str(current_user.id)
    profile_check = await repo.session.execute(
        text("SELECT 1 FROM profiles WHERE user_id::text = :uid LIMIT 1"),
        {"uid": user_id},
    )
    if profile_check.scalar():
        deal_data["created_by"] = user_id
        logger.debug("created_by asignado a user_id=%s", user_id)
    else:
        deal_data.pop("created_by", None)
        logger.warning("Perfil no encontrado para user_id=%s; created_by quedará NULL", user_id)

    new_deal = Deal(**deal_data)
    created = await repo.create(new_deal)
    return await repo.get_by_id(created.id)

@router.put("/admin/{deal_id}", response_model=DealDetailResponse)
async def update_deal(
    deal_id: str,
    deal_in: DealUpdate,
    repo: DealRepository = Depends(get_deal_repository),
    _auth = Depends(require_admin)
) -> DealDetailResponse:
    """Admin: Update an existing deal."""
    deal = await repo.get_by_id(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
        
    update_data = deal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deal, field, value)
        
    await repo.update(deal)
    return await repo.get_by_id(deal_id)

@router.delete("/admin/{deal_id}", status_code=204)
async def delete_deal(
    deal_id: str,
    repo: DealRepository = Depends(get_deal_repository),
    _auth = Depends(require_admin)
):
    """Admin: Delete a deal."""
    deal = await repo.get_by_id(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    await repo.delete(deal)
