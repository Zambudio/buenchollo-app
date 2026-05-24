from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.categories.infrastructure.repository import CategoryRepository
from app.modules.categories.api.schemas import CategoryResponse, CategoryCreate
from app.modules.categories.domain.models import Category
from app.core.security import require_admin

router = APIRouter(prefix="/categories", tags=["categories"])

def get_category_repository(db: AsyncSession = Depends(get_db)) -> CategoryRepository:
    return CategoryRepository(db)

@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    has_deals: bool = Query(False),
    repo: CategoryRepository = Depends(get_category_repository),
) -> list[CategoryResponse]:
    """Retrieve active categories. Con has_deals=true solo devuelve las que tienen deals activos."""
    if has_deals:
        return await repo.get_with_active_deals()
    return await repo.get_all_active()

@router.get("/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(
    slug: str,
    repo: CategoryRepository = Depends(get_category_repository)
) -> CategoryResponse:
    """Retrieve a category by its slug."""
    category = await repo.get_by_slug(slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.get("/admin/all", response_model=list[CategoryResponse])
async def get_all_admin_categories(
    repo: CategoryRepository = Depends(get_category_repository),
    current_user = Depends(require_admin)
) -> list[CategoryResponse]:
    """Admin: Retrieve all categories (including inactive)."""
    return await repo.get_all_admin()

@router.post("/admin", response_model=CategoryResponse)
async def create_category(
    category_in: CategoryCreate,
    repo: CategoryRepository = Depends(get_category_repository),
    current_user = Depends(require_admin)
) -> CategoryResponse:
    """Admin: Create a new category."""
    new_category = Category(**category_in.model_dump())
    created = await repo.create(new_category)
    return created

@router.delete("/admin/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    repo: CategoryRepository = Depends(get_category_repository),
    current_user = Depends(require_admin)
):
    """Admin: Delete a category."""
    category = await repo.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    await repo.delete(category)
