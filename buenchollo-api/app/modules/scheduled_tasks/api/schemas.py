from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_FrequencyPreset = Literal["daily", "weekly", "biweekly", "monthly"]
_Reason = Literal["price_increase", "no_longer_deal", "out_of_stock"]


class ScheduledTaskResponse(BaseModel):
    id: str
    task_type: str
    enabled: bool
    frequency_preset: str
    run_hour: int
    config: dict
    last_run_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class ScheduledTaskUpdate(BaseModel):
    enabled: bool | None = None
    frequency_preset: _FrequencyPreset | None = None
    run_hour: int | None = Field(default=None, ge=0, le=23)
    config: dict | None = None


class CandidateSchema(BaseModel):
    deal_id: str
    title: str
    slug: str
    image_url: str | None = None
    description: str | None = None
    store_id: str | None = None
    store_name: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    external_id: str
    affiliate_url: str
    source_url: str | None = None
    old_price: Decimal
    new_price: Decimal | None = None
    reason: _Reason


class PreviewResponse(BaseModel):
    total_checked: int
    candidates: list[CandidateSchema]


class ConfirmRequest(BaseModel):
    total_checked: int
    candidates: list[CandidateSchema]


class RunResponse(BaseModel):
    id: str
    trigger_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    total_checked: int
    total_affected: int
    triggered_by: str | None
    error_message: str | None
    model_config = ConfigDict(from_attributes=True)
