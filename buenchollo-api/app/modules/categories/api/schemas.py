from pydantic import BaseModel, ConfigDict

class CategoryBase(BaseModel):
    name: str
    slug: str
    icon: str | None = None
    display_order: int = 0
    is_active: bool = True

class CategoryResponse(CategoryBase):
    id: str
    parent_id: str | None = None
    model_config = ConfigDict(from_attributes=True)

class CategoryCreate(CategoryBase):
    parent_id: str | None = None
