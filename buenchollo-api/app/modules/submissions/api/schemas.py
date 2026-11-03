from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CheckLinkRequest(BaseModel):
    url: str = Field(..., max_length=2048)


class ExistingDealOut(BaseModel):
    id: str
    slug: str
    title: str
    image_url: str | None = None
    current_price: float | None = None


class SubmissionPrefillOut(BaseModel):
    title: str = ""
    brand: str = ""
    description: str = ""
    current_price: float | None = None
    previous_price: float | None = None
    image_url: str = ""
    images: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class LinkCheckResponse(BaseModel):
    status: Literal["published", "upcoming", "in_review", "ok"]
    canonical_url: str
    affiliate_url: str
    asin: str | None = None
    store_id: str | None = None
    store_name: str | None = None
    is_amazon: bool
    previously_published: bool = False
    existing_deal: ExistingDealOut | None = None
    prefill: SubmissionPrefillOut | None = None
    warnings: list[str] = Field(default_factory=list)
