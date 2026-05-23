from pydantic import BaseModel, ConfigDict
from typing import Literal
from datetime import datetime

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

    model_config = ConfigDict(from_attributes=True)

class VoteRequest(BaseModel):
    vote: Literal[-1, 1]

class VoteResponse(BaseModel):
    temperature: int
    votes_up: int
    votes_down: int
    my_vote: int  # -1, 0 o 1

class DealCreate(BaseModel):
    title: str
    slug: str | None = None
    short_description: str | None = None
    description: str | None = None
    image_url: str | None = None
    images: list[str] = []
    current_price: float
    previous_price: float | None = None
    discount_percentage: int | None = None
    shipping_info: str | None = None
    affiliate_url: str
    store_id: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    brand: str | None = None
    status: str = "active"
    expires_at: datetime | None = None
    scheduled_for: datetime | None = None
    published_at: datetime | None = None
    source: str = "manual"

class DealUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    short_description: str | None = None
    description: str | None = None
    image_url: str | None = None
    images: list[str] | None = None
    current_price: float | None = None
    previous_price: float | None = None
    discount_percentage: int | None = None
    shipping_info: str | None = None
    affiliate_url: str | None = None
    store_id: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    brand: str | None = None
    status: str | None = None
    expires_at: datetime | None = None
    scheduled_for: datetime | None = None
    published_at: datetime | None = None
