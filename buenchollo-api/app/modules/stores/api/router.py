from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_admin
from app.modules.stores.domain.exceptions import StoreNotFound
from app.modules.stores.domain.models import Store
from app.modules.stores.infrastructure.repository import StoreRepository
from app.modules.stores.api.schemas import StoreResponse, StoreCreate, StoreUpdate

router = APIRouter(prefix="/stores", tags=["stores"])


def get_store_repository(db: AsyncSession = Depends(get_db)) -> StoreRepository:
    return StoreRepository(db)


@router.get("", response_model=list[StoreResponse])
async def list_stores(
    has_deals: bool = Query(False),
    repo: StoreRepository = Depends(get_store_repository),
):
    """Con has_deals=true solo devuelve tiendas con deals activos."""
    if has_deals:
        return await repo.get_with_active_deals()
    return await repo.get_all_active()


@router.get("/admin/all", response_model=list[StoreResponse])
async def list_all_stores(
    repo: StoreRepository = Depends(get_store_repository),
    _auth=Depends(require_admin),
):
    return await repo.get_all()


@router.post("/admin", response_model=StoreResponse, status_code=201)
async def create_store(
    store_in: StoreCreate,
    repo: StoreRepository = Depends(get_store_repository),
    _auth=Depends(require_admin),
):
    store = Store(**store_in.model_dump())
    return await repo.create(store)


@router.put("/admin/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: str,
    store_in: StoreUpdate,
    repo: StoreRepository = Depends(get_store_repository),
    _auth=Depends(require_admin),
):
    store = await repo.get_by_id(store_id)
    if not store:
        raise StoreNotFound()
    for field, value in store_in.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    return await repo.update(store)


@router.delete("/admin/{store_id}", status_code=204)
async def delete_store(
    store_id: str,
    repo: StoreRepository = Depends(get_store_repository),
    _auth=Depends(require_admin),
):
    store = await repo.get_by_id(store_id)
    if not store:
        raise StoreNotFound()
    await repo.delete(store)
