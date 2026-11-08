"""Adaptador de Awin (publisher). Dos integraciones distintas:

1. Publisher API (`AWIN_ACCESS_TOKEN`, Bearer, 20 llamadas/min por usuario):
   - `POST /publishers/{publisherId}/linkbuilder/generate` → enlace de seguimiento.
   - `GET  /publishers/{publisherId}/programmes?relationship=...` → adhesión.
2. Feeds de producto (`AWIN_FEED_API_KEY`, clave distinta):
   - Lista de feeds: `https://ui.awin.com/productdata-darwin-download/publisher/{pid}/{key}/1/feedList`
     (CSV con Advertiser ID, Membership Status, Feed ID, Last Imported, URL...).
   - Cada feed se descarga desde la URL que trae esa lista (lleva la clave:
     nunca se guarda ni se loguea sin redactar).

Documentación: help.awin.com/apidocs/generatelink, /apidocs/get-program-information,
/developers/docs/product-feed-list-download (consultadas 2026-11-08).
"""

from __future__ import annotations

import csv
import gzip
import io
import zipfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from app.core.config import Settings
from app.modules.affiliates.domain.offers import html_to_text, normalize_product_url, parse_money
from app.modules.affiliates.infrastructure.http import MinuteRateLimiter, NetworkError, SafeHttp

API_BASE = "https://api.awin.com"
FEED_LIST_URL = "https://ui.awin.com/productdata-darwin-download/publisher/{pid}/{key}/1/feedList"
ALLOWED_HOSTS = frozenset({"api.awin.com", "ui.awin.com", "productdata.awin.com"})
AWIN_TRACKING_HOSTS = frozenset({"www.awin1.com", "awin1.com", "tidd.ly"})
RELATIONSHIPS = ("joined", "pending", "suspended", "rejected")

# Un único limitador por proceso: la cuota de Awin es por usuario, no por petición.
_LIMITER: MinuteRateLimiter | None = None


def _limiter(per_minute: int) -> MinuteRateLimiter:
    global _LIMITER
    if _LIMITER is None or _LIMITER.per_minute != per_minute:
        _LIMITER = MinuteRateLimiter(per_minute)
    return _LIMITER


class AwinLinkUnavailable(NetworkError):
    """Awin no ha devuelto un enlace válido para ese anunciante/destino."""


class AwinClient:
    def __init__(self, settings: Settings, http: SafeHttp | None = None) -> None:
        self.publisher_id = (settings.awin_publisher_id or "").strip()
        self._token = (settings.awin_access_token or "").strip()
        self._feed_key = (settings.awin_feed_api_key or "").strip()
        self.max_download = settings.awin_feed_max_download_mb * 1024 * 1024
        self.max_uncompressed = settings.awin_feed_max_uncompressed_mb * 1024 * 1024
        self.max_rows = settings.awin_feed_max_rows
        self.http = http or SafeHttp(
            ALLOWED_HOSTS,
            secrets=(self._token, self._feed_key),
            limiter=_limiter(settings.awin_rate_limit_per_minute),
        )

    @property
    def secrets(self) -> tuple[str, ...]:
        return tuple(s for s in (self._token, self._feed_key) if s)

    @property
    def api_configured(self) -> bool:
        return bool(self.publisher_id and self._token)

    @property
    def feeds_configured(self) -> bool:
        return bool(self.publisher_id and self._feed_key)

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    # ── Link Builder ────────────────────────────────────────────────────────

    def generate_link(self, advertiser_id: str, destination_url: str, clickref: str | None = None) -> str:
        body: dict = {"advertiserId": int(advertiser_id), "destinationUrl": destination_url, "shorten": True}
        if clickref:
            body["parameters"] = {"clickref": clickref[:50]}
        status, data = self.http.json(
            "POST", f"{API_BASE}/publishers/{self.publisher_id}/linkbuilder/generate", headers=self._auth(), json=body
        )
        url = (data.get("shortUrl") or data.get("url")) if isinstance(data, dict) else None
        if status != 200 or not isinstance(url, str):
            detail = data.get("description") if isinstance(data, dict) else None
            raise AwinLinkUnavailable(
                "Awin no ha generado el enlace"
                + (f": {str(detail)[:120]}" if detail else f" (HTTP {status})")
                + ". Comprueba que el programa está aprobado y admite Link Builder."
            )
        parts = urlsplit(url)
        if parts.scheme != "https" or (parts.hostname or "").lower() not in AWIN_TRACKING_HOSTS:
            raise AwinLinkUnavailable("Awin devolvió un enlace con un dominio inesperado; no se usa.")
        return url

    # ── Programas / adhesión ────────────────────────────────────────────────

    def programmes_by_relationship(self, country: str = "ES") -> dict[str, str]:
        """{advertiser_id: relationship}. Una llamada por relación (4 en total)."""
        result: dict[str, str] = {}
        for relationship in RELATIONSHIPS:
            status, data = self.http.json(
                "GET",
                f"{API_BASE}/publishers/{self.publisher_id}/programmes",
                headers=self._auth(),
                params={"relationship": relationship, "countryCode": country},
            )
            if status != 200 or not isinstance(data, list):
                raise NetworkError(f"Awin respondió {status} al consultar programas ({relationship}).")
            for item in data:
                if isinstance(item, dict) and item.get("id") is not None:
                    result.setdefault(str(item["id"]), relationship)
        return result

    # ── Feeds ───────────────────────────────────────────────────────────────

    def feed_list(self) -> list[dict]:
        url = FEED_LIST_URL.format(pid=self.publisher_id, key=self._feed_key)
        status, text = self.http.text(url)
        if status != 200:
            raise NetworkError(f"Awin respondió {status} a la lista de feeds.")
        return parse_feed_list(text)

    def download_feed(self, url: str, dest: Path) -> int:
        return self.http.download(url, dest, self.max_download)

    def iter_feed_file(self, path: Path) -> Iterator[dict]:
        yield from iter_feed_rows(path, self.max_uncompressed, self.max_rows)


# ── Parsers (puros, testeables con fixtures) ─────────────────────────────────

def parse_feed_list(text: str) -> list[dict]:
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    for raw in reader:
        row = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
        if not row.get("Feed ID"):
            continue
        rows.append(
            {
                "advertiser_id": row.get("Advertiser ID", ""),
                "advertiser_name": row.get("Advertiser Name", ""),
                "region": row.get("Primary Region", ""),
                "membership_status": row.get("Membership Status", "").lower(),
                "format": row.get("Datafeed Format", ""),
                "feed_id": row.get("Feed ID", ""),
                "name": row.get("Feed Name", ""),
                "language": row.get("Language", ""),
                "last_imported": row.get("Last Imported", ""),
                "last_checked": row.get("Last Checked", ""),
                "products": row.get("No of products", ""),
                "url": row.get("URL", ""),  # contiene la clave: no persistir
            }
        )
    return rows


class _LimitedReader(io.RawIOBase):
    """Corta la descompresión al superar `limit` bytes (zip/gzip bomb)."""

    def __init__(self, raw, limit: int, closer=None) -> None:
        self.raw, self.limit, self.read_total, self.closer = raw, limit, 0, closer

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        try:
            self.raw.close()
            if self.closer is not None:
                self.closer.close()
        finally:
            super().close()

    def readinto(self, buffer) -> int:
        data = self.raw.read(len(buffer))
        self.read_total += len(data)
        if self.read_total > self.limit:
            raise NetworkError("El feed descomprimido supera el tamaño máximo configurado.")
        buffer[: len(data)] = data
        return len(data)


def _open_feed(path: Path, max_uncompressed: int):
    with path.open("rb") as fh:
        magic = fh.read(4)
    closer = None
    if magic[:2] == b"\x1f\x8b":
        raw = gzip.open(path, "rb")
    elif magic == b"PK\x03\x04":
        archive = zipfile.ZipFile(path)
        members = [m for m in archive.infolist() if not m.is_dir()]
        if len(members) != 1:
            archive.close()
            raise NetworkError("El ZIP del feed debe contener un único fichero.")
        raw, closer = archive.open(members[0]), archive
    else:
        raw = path.open("rb")
    return io.TextIOWrapper(io.BufferedReader(_LimitedReader(raw, max_uncompressed, closer)), encoding="utf-8-sig", errors="replace", newline="")


_SPEC_COLUMNS = (
    "colour",
    "Fashion:size",
    "size",
    "dimensions",
    "product_type",
    "specifications",
    "delivery_time",
    "warranty",
    "condition",
    "base_price",
    "valid_to",
)


def _first(row: dict, *names: str) -> str | None:
    for name in names:
        value = (row.get(name) or "").strip()
        if value:
            return value
    return None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_stock(row: dict) -> bool | None:
    value = (_first(row, "in_stock", "stock_status") or "").lower()
    if value in {"1", "yes", "true", "in stock", "instock", "in_stock", "available"}:
        return True
    if value in {"0", "no", "false", "out of stock", "outofstock", "out_of_stock", "unavailable"}:
        return False
    return None


def _https_or_none(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    return url[:2048] if parts.scheme == "https" and parts.hostname else None


def map_feed_row(row: dict) -> dict | None:
    """Fila CSV del feed → campos de `AffiliateFeedProduct`. Los nombres de
    columna admiten las variantes conocidas; lo ausente queda en None."""
    product_key = _first(row, "aw_product_id", "product_id")
    merchant_product_id = _first(row, "merchant_product_id")
    title = html_to_text(_first(row, "product_name"), 300)
    if not (product_key or merchant_product_id) or not title:
        return None
    merchant_url = _https_or_none(_first(row, "merchant_deep_link", "deep_link"))
    specs = {k: v[:300] for k in _SPEC_COLUMNS if (v := (row.get(k) or "").strip())}
    return {
        "product_key": (product_key or merchant_product_id)[:64],
        "merchant_product_id": merchant_product_id[:128] if merchant_product_id else None,
        "normalized_url": normalize_product_url(merchant_url),
        "merchant_url": merchant_url,
        "tracking_url": _https_or_none(_first(row, "aw_deep_link")),
        "title": title,
        "brand": (_first(row, "brand_name") or "")[:120] or None,
        "model": (_first(row, "model_number", "product_model") or "")[:120] or None,
        "description": html_to_text(_first(row, "description", "product_short_description"), 4000),
        "ean": (_first(row, "ean", "product_GTIN", "upc") or "")[:32] or None,
        "mpn": (_first(row, "mpn") or "")[:64] or None,
        "colour": (_first(row, "colour") or "")[:64] or None,
        "condition": (_first(row, "condition") or "")[:32] or None,
        "price": parse_money(_first(row, "search_price", "store_price", "display_price")),
        "currency": (_first(row, "currency") or "")[:3].upper() or None,
        "rrp_price": parse_money(_first(row, "rrp_price")),
        "delivery_cost": (_first(row, "delivery_cost") or "")[:64] or None,
        "in_stock": _parse_stock(row),
        "image_url": _https_or_none(_first(row, "merchant_image_url", "large_image", "aw_image_url")),
        "category": (_first(row, "merchant_category", "category_name") or "")[:200] or None,
        "specs": specs,
        "provider_updated_at": _parse_dt(_first(row, "last_updated")),
    }


def iter_feed_rows(path: Path, max_uncompressed: int, max_rows: int) -> Iterator[dict]:
    csv.field_size_limit(1024 * 1024)
    with _open_feed(path, max_uncompressed) as text:
        reader = csv.DictReader(text)
        columns = set(reader.fieldnames or [])
        if "product_name" not in columns or not columns.intersection({"aw_product_id", "product_id", "merchant_product_id"}):
            raise NetworkError("Formato de feed no compatible: se requiere CSV Awin con identificador y product_name.")
        for count, raw in enumerate(reader, start=1):
            if count > max_rows:
                raise NetworkError("El feed supera el número máximo de filas configurado.")
            mapped = map_feed_row(raw)
            if mapped is not None:
                yield mapped
