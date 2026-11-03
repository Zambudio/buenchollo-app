import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from urllib.parse import unquote, urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import get_settings
from app.modules.submissions.domain.models import APPROVED, DealSubmission
from app.modules.submissions.domain.rules import MAX_IMAGES


class CheckLinkRequest(BaseModel):
    url: str = Field(..., max_length=2048)


class ImageFromUrlRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


class ImageUploadResponse(BaseModel):
    url: str
    width: int
    height: int


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


AMAZON_IMAGE_HOSTS = frozenset({"m.media-amazon.com", "images-na.ssl-images-amazon.com"})
BUCKET_PATH = "/storage/v1/object/public/deal-images/submissions/"


_UNSAFE_CHARS = re.compile(r"[\\\s\x00-\x1f\x7f]")


def allowed_bucket_prefix() -> str | None:
    base = (get_settings().supabase_url or "").strip().rstrip("/").removesuffix("/rest/v1").rstrip("/")
    return f"{base}{BUCKET_PATH}" if base else None


def _has_dot_segments(path: str) -> bool:
    return any(unquote(segment) in ("..", ".") for segment in path.split("/"))


def is_allowed_image(url: str) -> bool:
    if _UNSAFE_CHARS.search(url) or "%5c" in url.lower():
        return False
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password or port not in (None, 443):
        return False
    if parsed.params or parsed.fragment or _has_dot_segments(parsed.path):
        return False
    host = (parsed.hostname or "").lower()
    if host in AMAZON_IMAGE_HOSTS:
        return True
    prefix = allowed_bucket_prefix()
    if not prefix:
        return False
    allowed = urlparse(prefix)
    return (
        host == (allowed.hostname or "").lower()
        and parsed.path.startswith(allowed.path)
        and len(parsed.path) > len(allowed.path)
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class SubmissionCreate(BaseModel):
    url: str = Field(..., max_length=2048)
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    current_price: Decimal = Field(..., gt=0, le=100_000, decimal_places=2)
    previous_price: Decimal | None = Field(default=None, gt=0, le=100_000, decimal_places=2)
    coupon_code: str | None = Field(default=None, max_length=64)
    shipping_info: str | None = Field(default=None, max_length=120)
    store_name: str | None = Field(default=None, max_length=80)
    category_id: str
    subcategory_id: str | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    images: list[str] = Field(default_factory=list, max_length=MAX_IMAGES)
    image_url: str | None = None

    @field_validator("image_url", mode="after")
    @classmethod
    def _empty_image_url(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @field_validator("title", "coupon_code", "shipping_info", "store_name", "description", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("coupon_code", "shipping_info", "store_name", "description")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("images")
    @classmethod
    def _images_allowed(cls, value: list[str]) -> list[str]:
        for image in value:
            if len(image) > 2048 or not is_allowed_image(image):
                raise ValueError("Imagen no permitida: sube la imagen a BuenChollo o usa una de Amazon")
        return value

    @model_validator(mode="after")
    def _cross_checks(self) -> "SubmissionCreate":
        if self.previous_price is not None and self.previous_price <= self.current_price:
            raise ValueError("El precio anterior debe ser mayor que el precio actual")
        if self.image_url and self.image_url not in self.images:
            raise ValueError("La imagen principal debe estar entre las imágenes")
        if self.expires_at is not None:
            expires = _aware(self.expires_at)
            if expires <= datetime.now(timezone.utc):
                raise ValueError("La fecha de fin debe ser futura")
            if self.starts_at is not None and expires <= _aware(self.starts_at):
                raise ValueError("La fecha de fin debe ser posterior a la de inicio")
        return self


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    title: str
    description: str | None = None
    original_url: str
    affiliate_url: str
    current_price: float
    previous_price: float | None = None
    coupon_code: str | None = None
    shipping_info: str | None = None
    store_id: str | None = None
    store_name: str | None = None
    category_id: str | None = None
    subcategory_id: str | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    image_url: str | None = None
    images: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    deal_slug: str | None = None
    created_at: datetime | None = None


def to_submission_response(sub: DealSubmission) -> SubmissionResponse:
    response = SubmissionResponse.model_validate(sub)
    if sub.status == APPROVED and sub.deal_id:
        response.deal_slug = sub.deal.slug
    return response
