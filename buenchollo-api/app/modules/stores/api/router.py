"""Endpoints del módulo stores.

NOTA arquitectónica (F2.5, 2026-05-27):
Stores es CRUD admin trivial sin reglas de negocio: list, list-admin,
create, update, delete. Como en `categories`, no tiene capa `application/`
a propósito — crear un `StoreService` que sólo delegue al repo sería
boilerplate puro (YAGNI). Cuando aparezca la primera regla que justifique
un caso de uso (p. ej. validar template de URL de afiliado o detectar
duplicados por dominio), extraer el service en ese momento siguiendo el
patrón de `users/application/user_service.py`.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import audit_log
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
    db: AsyncSession = Depends(get_db),
    repo: StoreRepository = Depends(get_store_repository),
    current_user=Depends(require_admin),
):
    store = Store(**store_in.model_dump())
    created = await repo.create(store)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="store.create",
        target_type="store",
        target_id=str(created.id),
        payload={"name": created.name, "slug": created.slug, "domain": created.domain},
    )
    return created


@router.put("/admin/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: str,
    store_in: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    repo: StoreRepository = Depends(get_store_repository),
    current_user=Depends(require_admin),
):
    store = await repo.get_by_id(store_id)
    if not store:
        raise StoreNotFound()
    diff = store_in.model_dump(exclude_unset=True)
    for field, value in diff.items():
        setattr(store, field, value)
    updated = await repo.update(store)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="store.update",
        target_type="store",
        target_id=store_id,
        payload={"changed_fields": list(diff.keys())},
    )
    return updated


@router.delete("/admin/{store_id}", status_code=204)
async def delete_store(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    repo: StoreRepository = Depends(get_store_repository),
    current_user=Depends(require_admin),
):
    store = await repo.get_by_id(store_id)
    if not store:
        raise StoreNotFound()
    await repo.delete(store)
    await audit_log(
        db,
        user_id=str(current_user.id),
        action="store.delete",
        target_type="store",
        target_id=store_id,
        payload={"name": store.name, "slug": store.slug},
    )
