"""Domain entities used by product preview workflows."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ProductPreview:
    """Normalized product information returned by the product preview use case."""

    title: str = ""
    brand: str = ""
    asin: str = ""
    product_url: str = ""
    affiliate_url: str = ""
    image_url: str = ""
    current_price: float | None = None
    original_price: float | None = None
    discount_percentage: int | None = None
    store: str = "Amazon"
    category: str = ""
    category_id: str | None = None
    subcategory_id: str | None = None
    description: str = ""
    short_description: str = ""
    long_description: str = ""
    telegram_text: str = ""
    expires_at: str | None = None
    features: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    currency: str = "EUR"
    in_stock: bool = False
    shipping_type: str | None = None
