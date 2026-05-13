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
    description: str = ""
    telegram_text: str = ""
    features: list[str] = field(default_factory=list)
    currency: str = "EUR"

