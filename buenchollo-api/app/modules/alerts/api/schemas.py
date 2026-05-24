from datetime import datetime
from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    keyword: str | None = Field(None, max_length=200)
    brand: str | None = Field(None, max_length=100)
    category_id: str | None = None
    store_id: str | None = None
    min_price: float | None = Field(None, ge=0)
    max_price: float | None = Field(None, ge=0)
    min_discount: int | None = Field(None, ge=1, le=99)


class AlertUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    keyword: str | None = None
    brand: str | None = None
    category_id: str | None = None
    store_id: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_discount: int | None = None
    is_active: bool | None = None


class CategorySlim(BaseModel):
    id: str
    name: str
    model_config = {"from_attributes": True}


class StoreSlim(BaseModel):
    id: str
    name: str
    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: str
    name: str
    keyword: str | None
    brand: str | None
    category_id: str | None
    store_id: str | None
    min_price: float | None
    max_price: float | None
    min_discount: int | None
    is_active: bool
    last_triggered_at: datetime | None
    created_at: datetime
    category: CategorySlim | None
    store: StoreSlim | None
    model_config = {"from_attributes": True}
