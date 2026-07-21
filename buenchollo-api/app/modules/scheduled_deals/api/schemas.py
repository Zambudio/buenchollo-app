from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.scheduled_deals.domain.models import ScheduledDealStatus


class ScheduledDealCreate(BaseModel):
    asin: str = Field(min_length=10, max_length=10, pattern=r"^[A-Z0-9]{10}$")
    title: str = Field(min_length=3, max_length=200)
    slug: str | None = Field(default=None, max_length=200)
    description_web: str = Field(default="", max_length=10_000)
    short_description: str | None = Field(default=None, max_length=300)
    telegram_text: str = Field(default="", max_length=4096)
    telegram_channel_id: str | None = Field(default=None, min_length=1, max_length=100)
    offer_price: float = Field(gt=0)
    regular_price: float | None = Field(default=None, gt=0)
    discount_percentage: int = Field(default=0, ge=0, le=100)
    image_url: str | None = Field(default=None, max_length=2048)
    images: list[str] = Field(default_factory=list, max_length=20)
    affiliate_url: str = Field(min_length=1, max_length=2048)
    store_name: str = Field(default="Amazon", max_length=100)
    store_id: str | None = None
    category_id: str
    subcategory_id: str | None = None
    brand: str | None = Field(default=None, max_length=100)
    shipping_info: str | None = Field(default=None, max_length=200)
    expires_at: datetime | None = None
    scheduled_at: datetime
    source: str = Field(default="manual", max_length=16)
    show_keepa_chart: bool = False

    @field_validator("asin", mode="before")
    @classmethod
    def normalize_asin(cls, value: str) -> str:
        return value.strip().upper()


class ScheduledDealUpdate(BaseModel):
    asin: str | None = Field(default=None, min_length=10, max_length=10, pattern=r"^[A-Z0-9]{10}$")
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description_web: str | None = Field(default=None, max_length=10_000)
    short_description: str | None = Field(default=None, max_length=300)
    telegram_text: str | None = Field(default=None, max_length=4096)
    telegram_channel_id: str | None = Field(default=None, min_length=1, max_length=100)
    offer_price: float | None = Field(default=None, gt=0)
    regular_price: float | None = Field(default=None, gt=0)
    discount_percentage: int | None = Field(default=None, ge=0, le=100)
    image_url: str | None = Field(default=None, max_length=2048)
    images: list[str] | None = Field(default=None, max_length=20)
    affiliate_url: str | None = Field(default=None, min_length=1, max_length=2048)
    store_name: str | None = Field(default=None, max_length=100)
    store_id: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    brand: str | None = Field(default=None, max_length=100)
    shipping_info: str | None = Field(default=None, max_length=200)
    expires_at: datetime | None = None
    scheduled_at: datetime | None = None
    show_keepa_chart: bool | None = None

    @field_validator("asin", mode="before")
    @classmethod
    def normalize_asin(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class ScheduledDateUpdate(BaseModel):
    scheduled_at: datetime


class ScheduledDealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    deal_id: str
    asin: str
    title: str
    description_web: str
    telegram_text: str
    telegram_channel_id: str | None = None
    offer_price: float
    regular_price: float | None = None
    discount_percentage: int
    image_url: str | None = None
    affiliate_url: str
    store_name: str
    category_id: str
    scheduled_at: datetime
    status: ScheduledDealStatus
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime


ScheduleStatusLiteral = Literal[
    "programado", "publicado", "cancelado_precio", "cancelado_stock", "error"
]
