from pydantic import BaseModel, ConfigDict


class StoreResponse(BaseModel):
    id: str
    name: str
    slug: str
    domain: str | None = None
    logo_url: str | None = None
    affiliate_id: str | None = None
    affiliate_url_template: str | None = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class StoreCreate(BaseModel):
    name: str
    slug: str
    domain: str | None = None
    logo_url: str | None = None
    affiliate_id: str | None = None
    affiliate_url_template: str | None = None
    is_active: bool = True


class StoreUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    domain: str | None = None
    logo_url: str | None = None
    affiliate_id: str | None = None
    affiliate_url_template: str | None = None
    is_active: bool | None = None
