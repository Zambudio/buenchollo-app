"""Modelo común de una oferta importada de una red de afiliación y sus reglas
(dominio puro, sin I/O).

Separa proveedor (red + programa), tienda, producto y oferta. Lo que la fuente
no trae se queda en `None`: nunca se sustituye por 0, "gratis" o "en stock".

Reglas de publicación como chollo (`publication_blockers`):
- enlace afiliado de la red, título, precio actual, envío, descripción, categoría;
- precio "antes" con significado y evidencia válidos (un PVP recomendado o un
  `original_price` del feed NO lo demuestran) y ahorro exacto calculable;
- imagen con permiso para web y Telegram según el programa;
- programa habilitado y con adhesión `joined`;
- dato de precio no caducado según la política del programa.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# ── Procedencia ──────────────────────────────────────────────────────────────

SOURCE_AWIN_FEED = "awin_feed"
SOURCE_TRADEDOUBLER_API = "tradedoubler_api"
SOURCE_LINK_ONLY = "link_only"
NETWORK_DATA_SOURCES = frozenset({SOURCE_AWIN_FEED, SOURCE_TRADEDOUBLER_API, SOURCE_LINK_ONLY})

# ── Significado del precio de referencia ("antes") ───────────────────────────

REF_NONE = "none"
REF_RRP = "rrp"  # PVP recomendado del fabricante/feed: no prueba un precio anterior
REF_FEED_ORIGINAL = "feed_original_price"  # "precio original" del feed sin fecha: no prueba
REF_PROVIDER_HISTORY_30D = "provider_price_history_30d"  # mínimo de 30 días según el historial de la red
REF_STORE_VERIFIED = "store_strikethrough_verified"  # comprobado a mano en la tienda (tachado)
REF_MANUAL_VERIFIED = "manual_verified"  # otra evidencia aportada a mano
REFERENCE_TYPES = (
    REF_NONE,
    REF_RRP,
    REF_FEED_ORIGINAL,
    REF_PROVIDER_HISTORY_30D,
    REF_STORE_VERIFIED,
    REF_MANUAL_VERIFIED,
)
PROOF_REFERENCE_TYPES = frozenset({REF_PROVIDER_HISTORY_30D, REF_STORE_VERIFIED, REF_MANUAL_VERIFIED})

# Hosts de enlaces de seguimiento que generan las redes para nuestra cuenta.
NETWORK_TRACKING_HOSTS = frozenset(
    {
        "awin1.com",
        "www.awin1.com",
        "tidd.ly",
        "clk.tradedoubler.com",
        "pdt.tradedoubler.com",
        "tracker.tradedoubler.com",
    }
)

# Parámetros de seguimiento ajenos que se quitan del destino. Los demás se
# conservan (variante: color, capacidad, talla, vendedor...).
_STRIP_PARAMS_EXACT = frozenset({"fbclid", "gclid", "msclkid", "srsltid", "irclickid", "clickref", "awc", "tduid"})
_STRIP_PARAMS_PREFIXES = ("utm_", "aff_", "affiliate")


def is_network_tracking_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        host = urlsplit(url.strip()).hostname or ""
    except ValueError:
        return False
    return host.lower() in NETWORK_TRACKING_HOSTS


def _keep_param(name: str) -> bool:
    lowered = name.lower()
    return lowered not in _STRIP_PARAMS_EXACT and not lowered.startswith(_STRIP_PARAMS_PREFIXES)


def destination_url(url: str) -> str:
    """URL de destino para la red: https, sin fragmento ni seguimiento ajeno,
    conservando el resto de parámetros y su orden (pueden fijar la variante)."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if _keep_param(k)]
    return urlunsplit(("https", parts.netloc.lower(), parts.path or "/", urlencode(query), ""))


def normalize_product_url(url: str | None) -> str | None:
    """Clave de comparación exacta de URLs de producto: host sin www, ruta sin
    barra final, parámetros de variante ordenados, sin seguimiento ni fragmento."""
    if not url:
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    host = (parts.hostname or "").lower().removeprefix("www.")
    if not host:
        return None
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"
    query = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if _keep_param(k))
    return urlunsplit(("https", host, path, urlencode(query), ""))[:2048]


def url_matches(url: str, domains: list[str]) -> bool:
    """Un dominio del registro casa con el host exacto o un subdominio. Si la
    entrada lleva ruta (`samsung.com/es`), la ruta de la URL debe empezar por ella."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().removeprefix("www.")
    path = (parts.path or "/").lower()
    for entry in domains:
        entry = entry.lower().strip().removeprefix("www.")
        d, _, prefix = entry.partition("/")
        if not d or not (host == d or host.endswith("." + d)):
            continue
        if prefix and not (path == "/" + prefix.rstrip("/") or path.startswith("/" + prefix.rstrip("/") + "/")):
            continue
        return True
    return False


def slug_keywords(url: str, limit: int = 6) -> list[str]:
    """Palabras del último tramo útil de la ruta, para proponer candidatos por
    título. Nunca sirven para elegir un producto automáticamente."""
    path = urlsplit(url).path
    segments = [s for s in path.split("/") if s and not s.isdigit()]
    if not segments:
        return []
    slug = max(segments, key=len)
    slug = re.sub(r"\.(html?|php|aspx?)$", "", slug, flags=re.I)
    words = [w for w in re.split(r"[-_+.\s]+", slug) if len(w) >= 2 and not re.fullmatch(r"p?\d{1,3}", w)]
    return words[:limit]


# ── Texto externo: siempre datos, nunca instrucciones ────────────────────────

class _TextExtractor(HTMLParser):
    _BLOCK = {"p", "br", "li", "div", "tr", "h1", "h2", "h3", "h4", "ul", "ol"}
    _SKIP = {"script", "style", "iframe", "object", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip += 1
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip:
            self._skip -= 1
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏‪-‮⁦-⁩]")


def html_to_text(value: str | None, max_len: int = 4000) -> str | None:
    """HTML/texto del proveedor → texto plano sin etiquetas, scripts ni
    caracteres de control. El resultado se trata siempre como dato."""
    if not value:
        return None
    parser = _TextExtractor()
    try:
        parser.feed(value)
        parser.close()
        text = "".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]*>", " ", value)
    text = html.unescape(text)
    text = _CONTROL_RE.sub("", text)
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    if not text:
        return None
    return text[:max_len].rstrip()


def short_summary(description: str | None, max_len: int = 160) -> str | None:
    """Resumen corto con frases completas del propio texto del proveedor (no
    inventa nada; si no cabe una frase, corta por palabra)."""
    if not description:
        return None
    flat = re.sub(r"\s+", " ", description).strip()
    sentences = re.split(r"(?<=[.!?])\s+", flat)
    out = ""
    for sentence in sentences:
        candidate = f"{out} {sentence}".strip()
        if len(candidate) > max_len:
            break
        out = candidate
    if not out:
        out = flat[:max_len].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return out


# ── Dinero exacto ────────────────────────────────────────────────────────────

_CENT = Decimal("0.01")


def parse_money(value) -> Decimal | None:
    """'1.299,95' / '1299.95' / 'EUR 12.5' / 12.5 → Decimal con 2 decimales.
    Vacío, no numérico o negativo → None (nunca 0 por defecto)."""
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        raw = str(value)
    else:
        raw = re.sub(r"[^\d,.\-]", "", str(value))
        if not raw or raw in {"-", ".", ","}:
            return None
        if "," in raw and "." in raw:
            if raw.rfind(",") > raw.rfind("."):
                raw = raw.replace(".", "").replace(",", ".")
            else:
                raw = raw.replace(",", "")
        elif "," in raw:
            raw = raw.replace(",", ".")
    try:
        amount = Decimal(raw).quantize(_CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None
    if amount < 0 or not amount.is_finite():
        return None
    return amount


def savings(current: Decimal | None, previous: Decimal | None) -> tuple[Decimal, int] | None:
    """Ahorro exacto en euros y porcentaje entero (redondeo half-up, igual que
    `calculateDiscount` del panel). None si no hay un "antes" mayor que el precio."""
    if current is None or previous is None or current <= 0 or previous <= current:
        return None
    amount = (previous - current).quantize(_CENT, rounding=ROUND_HALF_UP)
    pct = ((previous - current) / previous * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return amount, int(pct)


def lowest_price_last_30_days(
    history: list[tuple[datetime, Decimal]], current: Decimal, now: datetime
) -> Decimal | None:
    """Precio de referencia tipo Omnibus: el mínimo de los 30 días anteriores a
    la bajada actual, según el historial de precios del proveedor para ESTA
    misma oferta. None si el historial no lo permite o no hay rebaja real."""
    points = sorted((d, p) for d, p in history if d is not None and p is not None and d <= now)
    if not points:
        return None
    # Inicio de la bajada actual: último cambio a `current` (o menor) desde un precio mayor.
    start = None
    for i in range(len(points) - 1, -1, -1):
        if points[i][1] > current:
            start = points[i + 1][0] if i + 1 < len(points) else now
            break
    if start is None:
        return None
    window = [p for d, p in points if start - timedelta(days=30) <= d < start]
    # Precio vigente al comenzar la ventana (último anterior a ella).
    before = [p for d, p in points if d < start - timedelta(days=30)]
    if before:
        window.append(before[-1])
    if not window:
        return None
    lowest = min(window)
    return lowest if lowest > current else None


# ── Caducidad del dato ───────────────────────────────────────────────────────

FRESH = "fresh"
STALE = "stale"
UNKNOWN_AGE = "unknown"


def data_freshness(
    provider_updated_at: datetime | None,
    price_verified_at: datetime | None,
    max_age_hours: int,
    now: datetime,
) -> str:
    """Una consulta reciente no prueba un dato reciente: cuenta la fecha de
    actualización que declara el proveedor o la comprobación manual en tienda."""
    reference = max((d for d in (provider_updated_at, price_verified_at) if d is not None), default=None)
    if reference is None:
        return UNKNOWN_AGE
    return FRESH if now - reference <= timedelta(hours=max(1, max_age_hours)) else STALE


# ── Modelo común ─────────────────────────────────────────────────────────────

@dataclass
class ProviderRef:
    network: str
    program_id: str
    advertiser_id: str
    program_name: str
    feed_id: str | None = None


@dataclass
class ProductData:
    product_key: str | None = None  # id estable de producto/variante en la red
    merchant_product_id: str | None = None  # SKU de la tienda
    title: str | None = None
    brand: str | None = None
    model: str | None = None
    description: str | None = None
    features: list[str] = field(default_factory=list)
    specs: dict[str, str] = field(default_factory=dict)
    ean: str | None = None
    mpn: str | None = None
    colour: str | None = None
    condition: str | None = None
    seller: str | None = None
    image_url: str | None = None
    category_hint: str | None = None


@dataclass
class OfferData:
    current_price: Decimal | None = None
    currency: str | None = None
    tax_note: str | None = None
    reference_price: Decimal | None = None
    reference_type: str = REF_NONE
    reference_evidence: str | None = None
    rrp_price: Decimal | None = None
    shipping: str | None = None
    in_stock: bool | None = None
    coupon: str | None = None


@dataclass
class ImportedOffer:
    provider: ProviderRef
    store_name: str
    store_id: str | None
    original_url: str
    destination_url: str
    affiliate_url: str | None
    link_source: str | None  # awin_linkbuilder | tradedoubler_product | tradedoubler_deeplink
    product: ProductData | None
    offer: OfferData | None
    data_source: str
    provider_updated_at: datetime | None
    imported_at: datetime

    @property
    def external_id(self) -> str | None:
        """Identidad estable tienda+producto+variante para deduplicar chollos
        (no por título)."""
        if not self.product or not (self.product.product_key or self.product.merchant_product_id):
            return None
        key = self.product.product_key or self.product.merchant_product_id
        return f"{self.provider.network[:2]}:{self.provider.advertiser_id}:{key}"[:64]


def missing_fields(offer: ImportedOffer) -> list[str]:
    """Campos que el editor necesita y la fuente no ha dado."""
    missing: list[str] = []
    p, o = offer.product, offer.offer
    if not offer.affiliate_url:
        missing.append("affiliate_url")
    if not p or not p.title:
        missing.append("title")
    if not o or o.current_price is None:
        missing.append("current_price")
    if not o or o.reference_price is None or o.reference_type not in PROOF_REFERENCE_TYPES:
        missing.append("previous_price_evidence")
    if not o or not o.shipping:
        missing.append("shipping_info")
    if not p or not p.image_url:
        missing.append("image_url")
    if not p or not p.description:
        missing.append("description")
    if not o or o.in_stock is None:
        missing.append("availability")
    missing.append("category")  # siempre la elige una persona en el editor
    return missing


# ── Reglas de publicación ────────────────────────────────────────────────────

BLOCKER_MESSAGES = {
    "program_disabled": "El programa de afiliación está deshabilitado",
    "program_not_joined": "El programa no figura como aprobado (adhesión distinta de 'joined')",
    "affiliate_url": "Falta el enlace afiliado generado por la red",
    "title": "Falta el nombre del producto",
    "current_price": "Falta el precio actual",
    "previous_price": "Falta un precio anterior mayor que el actual",
    "reference_not_proof": "El precio anterior no está justificado (un PVP o 'precio original' del feed no lo prueba)",
    "reference_evidence": "Falta la evidencia del precio anterior",
    "savings": "No se puede calcular el ahorro exacto",
    "shipping_info": "Falta la información de envío",
    "short_description": "Falta la descripción corta",
    "category": "Falta la categoría",
    "image": "Falta la imagen principal",
    "image_rights": "El programa no autoriza (o no consta) el uso de imágenes en web y Telegram",
    "stale_data": "El precio está caducado: actualízalo o compruébalo en la tienda",
    "unknown_data_age": "Se desconoce la fecha real del precio: compruébalo en la tienda",
}


@dataclass(frozen=True)
class ProgramPolicy:
    enabled: bool
    membership_status: str
    image_channels: tuple[str, ...]
    max_data_age_hours: int


@dataclass(frozen=True)
class PublishCandidate:
    affiliate_url: str | None
    title: str | None
    current_price: Decimal | None
    previous_price: Decimal | None
    reference_type: str | None
    reference_evidence: str | None
    shipping_info: str | None
    short_description: str | None
    category_id: str | None
    image_url: str | None
    provider_updated_at: datetime | None
    price_verified_at: datetime | None


def publication_blockers(c: PublishCandidate, policy: ProgramPolicy, now: datetime) -> list[str]:
    blockers: list[str] = []
    if not policy.enabled:
        blockers.append("program_disabled")
    if policy.membership_status != "joined":
        blockers.append("program_not_joined")
    if not c.affiliate_url or not is_network_tracking_url(c.affiliate_url):
        blockers.append("affiliate_url")
    if not (c.title or "").strip():
        blockers.append("title")
    if c.current_price is None or c.current_price <= 0:
        blockers.append("current_price")
    if c.previous_price is None or c.current_price is None or c.previous_price <= c.current_price:
        blockers.append("previous_price")
    elif (c.reference_type or REF_NONE) not in PROOF_REFERENCE_TYPES:
        blockers.append("reference_not_proof")
    elif not (c.reference_evidence or "").strip():
        blockers.append("reference_evidence")
    if "previous_price" not in blockers and savings(c.current_price, c.previous_price) is None:
        blockers.append("savings")
    if not (c.shipping_info or "").strip():
        blockers.append("shipping_info")
    if not (c.short_description or "").strip():
        blockers.append("short_description")
    if not c.category_id:
        blockers.append("category")
    if not c.image_url:
        blockers.append("image")
    elif not {"web", "telegram"} <= set(policy.image_channels):
        blockers.append("image_rights")
    freshness = data_freshness(c.provider_updated_at, c.price_verified_at, policy.max_data_age_hours, now)
    if freshness == STALE:
        blockers.append("stale_data")
    elif freshness == UNKNOWN_AGE:
        blockers.append("unknown_data_age")
    return blockers


def describe_blockers(blockers: list[str]) -> list[dict]:
    return [{"code": b, "message": BLOCKER_MESSAGES.get(b, b)} for b in blockers]
