"""Adaptador de Tradedoubler (publisher) — Products API 1.0.

`GET https://api.tradedoubler.com/1.0/products.json;fid={feedId};ean=...;spId=...;q=...;pageSize=N?token=...`
- Token de sistema "PRODUCTS" (Account → Manage tokens; 40 hex).
- Filtros como parámetros matrix (`;clave=valor`) en la ruta; `token` y
  `dateOutputFormat` como query normal.
- No existe búsqueda por URL: se busca por EAN / spId (id de producto de la
  tienda) o por palabras, y se casa exacto contra `sourceProductUrl`.
- `productUrl` = enlace con nuestro seguimiento (preferido); `sourceProductUrl`
  = URL de la tienda sin seguimiento.
`GET https://api.tradedoubler.com/1.0/productFeeds?token=...` → feeds accesibles.

Documentación: https://dev.tradedoubler.com/products/publisher/ (consultada 2026-11-08).
El deeplink sin ficha (`clk.tradedoubler.com/click?p=&a=&url=`) NO figura en esa
documentación: solo se usa si el propietario lo confirmó en el generador de su
cuenta para ese programa (`deeplink_verified_at`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote, urlsplit

from app.core.config import Settings
from app.modules.affiliates.domain.offers import html_to_text, parse_money
from app.modules.affiliates.infrastructure.http import NetworkError, SafeHttp

API_BASE = "https://api.tradedoubler.com/1.0"
ALLOWED_HOSTS = frozenset({"api.tradedoubler.com"})
TD_TRACKING_HOSTS = frozenset({"clk.tradedoubler.com", "pdt.tradedoubler.com", "tracker.tradedoubler.com"})


def _matrix_value(value: str) -> str:
    # ';', '/', '?' y '#' romperían la ruta matrix: se codifican siempre.
    return quote(str(value).strip()[:120], safe="")


class TradedoublerClient:
    def __init__(self, settings: Settings, http: SafeHttp | None = None) -> None:
        self.site_id = (settings.tradedoubler_site_id or "").strip()
        self._token = (settings.tradedoubler_products_token or "").strip()
        self.http = http or SafeHttp(ALLOWED_HOSTS, secrets=(self._token,))

    @property
    def secrets(self) -> tuple[str, ...]:
        return (self._token,) if self._token else ()

    @property
    def configured(self) -> bool:
        return bool(self._token)

    def search_products(
        self,
        feed_id: str,
        *,
        ean: str | None = None,
        sp_id: str | None = None,
        query: str | None = None,
        page_size: int = 10,
    ) -> list[dict]:
        matrix = f";fid={_matrix_value(feed_id)}"
        if ean:
            matrix += f";ean={_matrix_value(ean)}"
        if sp_id:
            matrix += f";spId={_matrix_value(sp_id)}"
        if query:
            matrix += f";q={_matrix_value(query)}"
        matrix += ";sourceproducturl=true;priceHistory=true"
        matrix += f";pageSize={max(1, min(page_size, 50))}"
        status, data = self.http.json(
            "GET",
            f"{API_BASE}/products.json{matrix}",
            params={"token": self._token, "dateOutputFormat": "iso8601"},
        )
        if status == 404:
            return []
        if status != 200 or not isinstance(data, dict):
            code = data.get("code") if isinstance(data, dict) else None
            raise NetworkError(f"Tradedoubler respondió {status}" + (f" ({str(code)[:20]})" if code else "") + ".")
        products = data.get("products") or []
        return [p for p in products if isinstance(p, dict)]

    def product_feeds(self) -> list[dict]:
        status, data = self.http.json("GET", f"{API_BASE}/productFeeds", params={"token": self._token})
        if status != 200 or not isinstance(data, dict):
            raise NetworkError(f"Tradedoubler respondió {status} al listar feeds.")
        feeds = data.get("feeds") or []
        out = []
        for feed in feeds:
            if not isinstance(feed, dict):
                continue
            programs = feed.get("programs") or []
            program_ids = [str(p.get("programId")) for p in programs if isinstance(p, dict) and p.get("programId")]
            out.append(
                {
                    "feed_id": str(feed.get("feedId", "")),
                    "name": str(feed.get("name", ""))[:200],
                    "program_ids": program_ids,
                    "products": feed.get("numberOfProducts"),
                    "last_imported": feed.get("lastModifiedTime") or feed.get("lastUpdated") or feed.get("updated"),
                    "language": feed.get("languageISOCode"),
                }
            )
        return out

    def deeplink(self, program_id: str, destination_url: str) -> str:
        """Formato p=programa, a=site ID. Llamar solo con `deeplink_verified_at`."""
        if not self.site_id:
            raise NetworkError("Falta TRADEDOUBLER_SITE_ID para generar el enlace.")
        return (
            f"https://clk.tradedoubler.com/click?p={quote(str(program_id), safe='')}"
            f"&a={quote(self.site_id, safe='')}&url={quote(destination_url, safe='')}"
        )


# ── Mapeo (puro) ─────────────────────────────────────────────────────────────

def _parse_dt(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _https(url) -> str | None:
    if not isinstance(url, str):
        return None
    parts = urlsplit(url.strip())
    return url.strip()[:2048] if parts.scheme == "https" and parts.hostname else None


def map_td_product(product: dict, feed_id: str) -> dict | None:
    """Producto de la API → dict normalizado. Usa la oferta del feed pedido."""
    offers = [o for o in (product.get("offers") or []) if isinstance(o, dict)]
    offer = next((o for o in offers if str(o.get("feedId")) == str(feed_id)), None)
    if offer is None:
        return None
    identifiers = product.get("identifiers") if isinstance(product.get("identifiers"), dict) else {}
    history: list[tuple[datetime, Decimal]] = []
    for entry in offer.get("priceHistory") or []:
        if not isinstance(entry, dict):
            continue
        price = entry.get("price") if isinstance(entry.get("price"), dict) else {}
        value = parse_money(price.get("value"))
        date = _parse_dt(entry.get("date"))
        if value is not None and date is not None:
            history.append((date, value))
    history.sort()
    current = history[-1][1] if history else None
    currency = None
    for entry in reversed(offer.get("priceHistory") or []):
        if isinstance(entry, dict) and isinstance(entry.get("price"), dict):
            currency = (entry["price"].get("currency") or "")[:3].upper() or None
            break
    images = product.get("productImage")
    image = images.get("url") if isinstance(images, dict) else None
    fields = {
        str(f.get("name"))[:60]: str(f.get("value"))[:300]
        for f in (product.get("fields") or [])
        if isinstance(f, dict) and f.get("name") and f.get("value") not in (None, "")
    }
    availability = str(offer.get("availability") or "").strip().lower()
    in_stock = True if availability in {"in stock", "instock", "available", "in_stock", "yes", "1"} else (
        False if availability in {"out of stock", "outofstock", "unavailable", "out_of_stock", "no", "0"} else None
    )
    sku = identifiers.get("sku") or offer.get("sourceProductId")
    title = html_to_text(product.get("name"), 300)
    if not title:
        return None
    return {
        "product_key": str(offer.get("id") or sku or "")[:64] or None,
        "merchant_product_id": str(sku)[:128] if sku else None,
        "title": title,
        "brand": (str(product.get("brand") or "")[:120]) or None,
        "model": (str(identifiers.get("mpn") or "")[:120]) or None,
        "description": html_to_text(product.get("description") or product.get("shortDescription"), 4000),
        "ean": (str(identifiers.get("ean") or "")[:32]) or None,
        "mpn": (str(identifiers.get("mpn") or "")[:64]) or None,
        "condition": (str(offer.get("condition") or "")[:32]) or None,
        "image_url": _https(image),
        "tracking_url": _https(offer.get("productUrl")),
        "merchant_url": _https(offer.get("sourceProductUrl")),
        "price": current,
        "currency": currency,
        "price_history": history,
        "shipping": ((str(offer["shippingCost"]) if offer.get("shippingCost") is not None else "")[:64]) or None,
        "delivery_time": (str(offer.get("deliveryTime") or "")[:64]) or None,
        "in_stock": in_stock,
        "program_name": str(offer.get("programName") or "")[:120] or None,
        "specs": fields,
        "provider_updated_at": _parse_dt(offer.get("modified")),
    }
