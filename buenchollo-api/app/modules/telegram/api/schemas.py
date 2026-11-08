from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ── Canal ─────────────────────────────────────────────────────────────────────

class TelegramChannel(BaseModel):
    id: str
    name: str


# ── Generación de post ────────────────────────────────────────────────────────

class TelegramGenerateRequest(BaseModel):
    title: str
    current_price: float
    previous_price: float | None = None
    discount_percentage: int | None = None
    description: str | None = None          # descripción corta o larga
    affiliate_url: str = ""
    expires_at: str | None = None           # ISO string
    # Redes de afiliación: línea de envío y aviso adicional del programa.
    # Vacíos en Amazon → el texto queda exactamente como antes.
    shipping_info: str | None = Field(default=None, max_length=200)
    notice: str | None = Field(default=None, max_length=300)


class TelegramGenerateResponse(BaseModel):
    text: str
    suggested_categories: list[str]


# ── Categorías ────────────────────────────────────────────────────────────────

class TelegramCategoryAddRequest(BaseModel):
    category: str                           # p.ej. "#NuevoProducto" o "NuevoProducto"


class TelegramCategoriesResponse(BaseModel):
    categories: list[str]


# ── Publicación ───────────────────────────────────────────────────────────────

class TelegramNotifyRequest(BaseModel):
    """
    Soporta dos flujos:
    - Panel completo: text + entities + image_url + channel_id
    - Checkbox rápido (legado): title + current_price + ... (construye el texto en el backend)
    """
    # Flujo panel: texto ya generado y editado por el usuario
    text: str | None = None
    entities: list[dict] | None = None
    image_url: str | None = None
    channel_id: str | None = None           # si None → usa TELEGRAM_MAIN_CHANNEL_ID
    # Chollo al que pertenece (para registrar la publicación). Si el panel no lo
    # conoce, se busca por el ASIN de `affiliate_url`.
    deal_id: UUID | None = None

    # Flujo rápido (legado, se usa si text es None)
    title: str | None = None
    current_price: float | None = None
    previous_price: float | None = None
    discount_percentage: int | None = None
    short_description: str | None = None
    affiliate_url: str | None = None
    public_url: str | None = None


class TelegramPublicationResponse(BaseModel):
    id: str
    deal_id: str | None = None
    channel_kind: str
    source: str
    text: str
    image_url: str | None = None
    price: float | None = None
    previous_price: float | None = None
    discount_percentage: int | None = None
    sent_at: datetime
    # El mismo texto con el precio actual del chollo (None si no se puede corregir).
    repriced_text: str | None = None

    model_config = ConfigDict(from_attributes=True)
