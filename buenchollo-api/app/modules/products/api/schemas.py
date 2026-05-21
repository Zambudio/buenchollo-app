"""Pydantic schemas for the products API."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductPreviewFromUrlRequest(BaseModel):
    """Request payload for previewing a product from a URL or ASIN."""

    url: str = Field(..., min_length=1, examples=["https://www.amazon.es/dp/B08TEST123"])

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """Reject blank values after trimming whitespace."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("La URL no puede estar vacía.")
        return cleaned


class ProductPreviewResponse(BaseModel):
    """Normalized response returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    brand: str
    asin: str
    product_url: str
    affiliate_url: str
    image_url: str
    current_price: float = 0.0
    original_price: float = 0.0
    discount_percentage: int = 0
    store: str = "Amazon"
    category: str
    category_id: str | None = None
    subcategory_id: str | None = None
    description: str
    short_description: str = ""
    long_description: str = ""
    telegram_text: str
    images: list[str] = []
    expires_at: str | None = None

    @field_validator("current_price", "original_price", mode="before")
    @classmethod
    def default_float(cls, value: float | None) -> float:
        """Return zero for missing numeric values in the public response."""
        return 0.0 if value is None else value

    @field_validator("discount_percentage", mode="before")
    @classmethod
    def default_int(cls, value: int | None) -> int:
        """Return zero for missing discount values in the public response."""
        return 0 if value is None else value

