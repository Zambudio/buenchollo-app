from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_FrequencyPreset = Literal["daily", "weekly", "biweekly", "monthly"]
_Reason = Literal[
    "price_increase", "no_longer_deal", "out_of_stock", "not_found",
    "deal_again", "listing_purged", "product_purged",
]
_Transition = Literal["offer_ended", "reactivated", "purged"]

# Rangos admitidos para las claves conocidas de la config de price_check.
_CONFIG_RANGES = {
    "price_tolerance_percent": (0, 100),
    "min_discount_percent": (0, 90),
    "purge_after_days": (7, 365),
}


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

    @field_validator("config")
    @classmethod
    def _check_config_ranges(cls, config: dict | None) -> dict | None:
        for key, (low, high) in _CONFIG_RANGES.items():
            if config is None or key not in config:
                continue
            value = config[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
                raise ValueError(f"{key} debe ser un número entre {low} y {high}")
        return config


class CandidateSchema(BaseModel):
    deal_id: str
    title: str
    slug: str
    image_url: str | None = None
    description: str | None = None
    short_description: str | None = None
    store_id: str | None = None
    store_name: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    external_id: str
    affiliate_url: str
    source_url: str | None = None
    old_price: Decimal
    previous_price: Decimal | None = None
    discount_percentage: int | None = None
    new_price: Decimal | None = None
    reason: _Reason
    transition: _Transition


class PreviewResponse(BaseModel):
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


class RunItemResponse(BaseModel):
    id: str
    deal_id_snapshot: str
    title: str
    slug: str
    image_url: str | None = None
    short_description: str | None = None
    store_name: str | None = None
    old_price: Decimal
    previous_price: Decimal | None = None
    discount_percentage: int | None = None
    new_price: Decimal | None = None
    reason: str
    transition: str
    model_config = ConfigDict(from_attributes=True)


class RunDetailResponse(RunResponse):
    items: list[RunItemResponse]


class BulkDeleteRunsRequest(BaseModel):
    run_ids: list[str]


class BulkDeleteRunsResponse(BaseModel):
    deleted: int
