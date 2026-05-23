from pydantic import BaseModel


class TelegramNotifyRequest(BaseModel):
    title: str
    current_price: float
    previous_price: float | None = None
    discount_percentage: int | None = None
    short_description: str | None = None
    image_url: str | None = None
    affiliate_url: str
    public_url: str | None = None
