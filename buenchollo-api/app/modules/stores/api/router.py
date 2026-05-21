from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.stores.infrastructure.repository import StoreRepository
from app.modules.stores.api.schemas import StoreResponse

router = APIRouter(prefix="/stores", tags=["stores"])

def get_store_repository(db: AsyncSession = Depends(get_db)) -> StoreRepository:
    return StoreRepository(db)

@router.get("", response_model=list[StoreResponse])
async def list_stores(
    repo: StoreRepository = Depends(get_store_repository)
) -> list[StoreResponse]:
    """Retrieve all active stores."""
    stores = await repo.get_all_active()
    return stores
