from datetime import datetime
from typing import Literal
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
    # Redes de afiliación: línea de envío y programa del chollo. El aviso
    # adicional se lee de ese programa en la BD. Vacíos en Amazon → el texto
    # queda exactamente como antes.
    shipping_info: str | None = Field(default=None, max_length=200)
    affiliate_program_id: UUID | None = None
    # Obsoleto: se ignora (el aviso lo decide el servidor). Se acepta para no
    # romper una pestaña del panel abierta con la versión anterior.
    notice: str | None = Field(default=None, max_length=300)
    # Chollo ya guardado: la IA reescribe la línea de venta (✏️) a partir de
    # `copy_context` (descripción larga) con el motor elegido en el admin.
    ai_copy: bool = False
    provider: Literal["omniroute", "openai", "auto"] | None = None
    copy_context: str | None = Field(default=None, max_length=10_000)


class TelegramGenerateResponse(BaseModel):
    text: str
    suggested_categories: list[str]
    # Copy escrito por la IA (None si no se pidió o la IA falló y se usó `description`).
    ai_copy: str | None = None
    # El mismo post adaptado a WhatsApp (emojis estándar), para compartirlo a mano.
    whatsapp_text: str = ""


class WhatsAppTextRequest(BaseModel):
    text: str = Field(max_length=10_000)


class WhatsAppTextResponse(BaseModel):
    text: str


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
    # Versión WhatsApp editada en el panel; si falta se deriva de `text`.
    whatsapp_text: str | None = Field(default=None, max_length=10_000)

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


class WeeklyDigestResponse(BaseModel):
    # Pie de foto de la publicación de Telegram (máx. 1024 caracteres).
    telegram_text: str | None
    # Texto completo (respaldo sin imagen; base de la versión WhatsApp).
    full_text: str | None = None
    whatsapp_text: str | None
    count: int
    sent: bool
