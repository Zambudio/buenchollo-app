from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from datetime import datetime

# Límites razonables para los campos de texto de un chollo. Defensa en
# profundidad (admin-only) ante payloads abusivos. Ver SECURITY_AUDIT.md
# SEC-05.
_TITLE_MAX = 200
_SHORT_DESC_MAX = 300
_DESC_MAX = 10_000
_URL_MAX = 2048
_BRAND_MAX = 100
_STATUS_MAX = 16
_SLUG_MAX = 200
_EXTERNAL_ID_MAX = 64

class StoreBasic(BaseModel):
    name: str
    slug: str
    model_config = ConfigDict(from_attributes=True)

class CategoryBasic(BaseModel):
    name: str
    slug: str
    model_config = ConfigDict(from_attributes=True)

class DealCardResponse(BaseModel):
    id: str
    title: str
    slug: str
    image_url: str | None = None
    images: list[str] = []
    current_price: float
    previous_price: float | None = None
    discount_percentage: int | None = None
    temperature: int
    published_at: datetime | None = None
    created_at: datetime | None = None
    
    store: StoreBasic | None = None
    category: CategoryBasic | None = None
    subcategory: CategoryBasic | None = None
    
    model_config = ConfigDict(from_attributes=True)

class DealDetailResponse(DealCardResponse):
    description: str | None = None
    short_description: str | None = None
    affiliate_url: str | None = None
    status: str
    expires_at: datetime | None = None
    scheduled_for: datetime | None = None
    shipping_info: str | None = None
    comment_count: int = 0
    favorite_count: int = 0
    votes_up: int = 0
    votes_down: int = 0
    click_count: int = 0
    store_id: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    external_id: str | None = None
    show_keepa_chart: bool = False

    model_config = ConfigDict(from_attributes=True)

class VoteRequest(BaseModel):
    vote: Literal[-1, 1]

class VoteResponse(BaseModel):
    temperature: int
    votes_up: int
    votes_down: int
    my_vote: int  # -1, 0 o 1

class DealCreate(BaseModel):
    title: str = Field(min_length=3, max_length=_TITLE_MAX)
    slug: str | None = Field(default=None, max_length=_SLUG_MAX)
    short_description: str | None = Field(default=None, max_length=_SHORT_DESC_MAX)
    description: str | None = Field(default=None, max_length=_DESC_MAX)
    image_url: str | None = Field(default=None, max_length=_URL_MAX)
    images: list[str] = Field(default_factory=list, max_length=20)
    current_price: float = Field(gt=0)
    previous_price: float | None = Field(default=None, gt=0)
    discount_percentage: int | None = Field(default=None, ge=0, le=100)
    shipping_info: str | None = Field(default=None, max_length=200)
    affiliate_url: str = Field(max_length=_URL_MAX)
    store_id: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    brand: str | None = Field(default=None, max_length=_BRAND_MAX)
    status: str = Field(default="active", max_length=_STATUS_MAX)
    expires_at: datetime | None = None
    scheduled_for: datetime | None = None
    published_at: datetime | None = None
    source: str = Field(default="manual", max_length=_STATUS_MAX)
    external_id: str | None = Field(default=None, max_length=_EXTERNAL_ID_MAX)
    show_keepa_chart: bool = False

class DealUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=_TITLE_MAX)
    slug: str | None = Field(default=None, max_length=_SLUG_MAX)
    short_description: str | None = Field(default=None, max_length=_SHORT_DESC_MAX)
    description: str | None = Field(default=None, max_length=_DESC_MAX)
    image_url: str | None = Field(default=None, max_length=_URL_MAX)
    images: list[str] | None = Field(default=None, max_length=20)
    current_price: float | None = Field(default=None, gt=0)
    previous_price: float | None = Field(default=None, gt=0)
    discount_percentage: int | None = Field(default=None, ge=0, le=100)
    shipping_info: str | None = Field(default=None, max_length=200)
    affiliate_url: str | None = Field(default=None, max_length=_URL_MAX)
    store_id: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    brand: str | None = Field(default=None, max_length=_BRAND_MAX)
    status: str | None = Field(default=None, max_length=_STATUS_MAX)
    expires_at: datetime | None = None
    scheduled_for: datetime | None = None
    published_at: datetime | None = None
    external_id: str | None = Field(default=None, max_length=_EXTERNAL_ID_MAX)
    show_keepa_chart: bool | None = None
