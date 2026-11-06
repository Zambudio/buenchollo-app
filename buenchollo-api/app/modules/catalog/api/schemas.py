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
