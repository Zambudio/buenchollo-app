from datetime import date

from pydantic import BaseModel


class TopProductResponse(BaseModel):
    id: str
    title: str
    image_url: str | None
    deal_slug: str | None
    deal_status: str | None = None
    current_price: float | None = None
    vote_count: int
    position: int


class VoteResponse(BaseModel):
    voted: bool


class PricePointResponse(BaseModel):
    date: date
    price: float
    low_price: float
    store_id: str | None = None


class PriceStatsResponse(BaseModel):
    days_tracked: int
    first_seen: date | None
    all_time_low: float | None
    all_time_low_on: date | None
    window_days: int
    window_low: float | None
    window_high: float | None
    window_average: float | None


class PriceHistoryResponse(BaseModel):
    product_id: str
    stats: PriceStatsResponse
    points: list[PricePointResponse]
