from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Network = Literal["awin", "tradedoubler"]
Membership = Literal["unknown", "joined", "pending", "rejected", "suspended", "notjoined"]

_DOMAIN_RE = r"^(?=.{3,253}$)(?!-)[a-z0-9-]+(\.[a-z0-9-]+)+(/[a-z0-9._-]+)*$"


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    network: str
    advertiser_id: str
    name: str
    store_id: str | None = None
    domains: list[str] = []
    country: str
    currency: str
    membership_status: str
    membership_checked_at: datetime | None = None
    membership_source: str | None = None
    promo_spaces: list[str] = []
    feeds: list[dict[str, Any]] = []
    supports_import: bool
    supports_links: bool
    deeplink_verified_at: datetime | None = None
    restrictions: dict[str, Any] = {}
    disclosure_text: str | None = None
    max_data_age_hours: int
    enabled: bool
    notes: str | None = None
    updated_at: datetime | None = None


class Restrictions(BaseModel):
    marketplace: bool | None = None
    third_party_sellers: str | None = Field(default=None, max_length=200)
    image_channels: list[Literal["web", "telegram"]] = []
    channels: list[str] = Field(default_factory=list, max_length=10)
    notes: str | None = Field(default=None, max_length=1000)


class ProgramWrite(BaseModel):
    network: Network | None = None
    advertiser_id: str | None = Field(default=None, pattern=r"^\d{1,12}$")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    store_id: str | None = None
    domains: list[str] | None = Field(default=None, max_length=10)
    promo_spaces: list[str] | None = Field(default=None, max_length=10)
    membership_status: Membership | None = None
    selected_feed_ids: list[str] | None = Field(default=None, max_length=20)
    supports_import: bool | None = None
    supports_links: bool | None = None
    deeplink_verified: bool | None = None
    restrictions: Restrictions | None = None
    disclosure_text: str | None = Field(default=None, max_length=300)
    max_data_age_hours: int | None = Field(default=None, ge=1, le=24 * 14)
    enabled: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("domains")
    @classmethod
    def clean_domains(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        import re

        out = []
        for raw in value:
            domain = raw.strip().lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").rstrip("/")
            if not re.match(_DOMAIN_RE, domain):
                raise ValueError(f"Dominio no válido: {raw[:60]}")
            out.append(domain)
        return out


class ImportRequestIn(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    program_id: str | None = None
    product_key: str | None = Field(default=None, max_length=64)
    ean: str | None = Field(default=None, pattern=r"^\d{8,14}$")
    sku: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9._\-]+$")
    link_only: bool = False


class ImportResponse(BaseModel):
    status: str
    message: str
    stage: str
    program: dict[str, Any] | None = None
    program_options: list[dict[str, Any]] = []
    link: dict[str, Any] = {}
    offer: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None
    missing: list[str] = []
    blockers: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    existing_deal: dict[str, Any] | None = None
    warnings: list[str] = []


class ReadinessRequest(BaseModel):
    affiliate_program_id: str | None = None
    data_source: str | None = None
    affiliate_url: str | None = Field(default=None, max_length=2048)
    title: str | None = Field(default=None, max_length=200)
    current_price: float | None = None
    previous_price: float | None = None
    price_reference_type: str | None = Field(default=None, max_length=32)
    price_reference_evidence: str | None = Field(default=None, max_length=500)
    shipping_info: str | None = Field(default=None, max_length=200)
    short_description: str | None = Field(default=None, max_length=300)
    category_id: str | None = None
    image_url: str | None = Field(default=None, max_length=2048)
    data_provider_updated_at: datetime | None = None
    price_verified_at: datetime | None = None


class ReadinessResponse(BaseModel):
    applies: bool
    ready: bool
    blockers: list[dict[str, Any]]
    savings_amount: str | None = None
    discount_percentage: int | None = None


class SyncRequest(BaseModel):
    program_id: str | None = None
    force: bool = False


class IntegrationStatus(BaseModel):
    awin_publisher_api: bool
    awin_feeds: bool
    tradedoubler_products: bool
    tradedoubler_site_id: bool
