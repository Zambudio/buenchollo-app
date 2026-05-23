from pydantic import BaseModel


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

    # Flujo rápido (legado, se usa si text es None)
    title: str | None = None
    current_price: float | None = None
    previous_price: float | None = None
    discount_percentage: int | None = None
    short_description: str | None = None
    affiliate_url: str | None = None
    public_url: str | None = None
