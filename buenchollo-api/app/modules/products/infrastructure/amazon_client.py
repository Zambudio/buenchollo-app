"""Amazon Creators API adapter — HTTP directo con requests, sin SDK externo."""

import ipaddress
import logging
import re
import socket
import time
import urllib.parse
import urllib.request
from typing import Any

import requests

from app.core.config import Settings
from app.modules.products.application.preview_product_from_url import ProductProviderUnavailableError
from app.modules.products.domain.entities import ProductPreview

logger = logging.getLogger(__name__)

ASIN_RE = re.compile(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})")
DIRECT_ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")

# Allowlist de hosts contra los que aceptamos hacer follow del redirect
# al resolver una URL acortada. Defensa anti-SSRF (SECURITY_AUDIT.md SEC-06):
# un admin malicioso o un token comprometido NO podrá usar este endpoint
# para escanear la LAN del NAS ni atacar servicios internos.
_ALLOWED_HOSTS = {
    "amazon.com", "www.amazon.com",
    "amazon.es", "www.amazon.es",
    "amazon.co.uk", "www.amazon.co.uk",
    "amazon.de", "www.amazon.de",
    "amazon.fr", "www.amazon.fr",
    "amazon.it", "www.amazon.it",
    "amazon.co.jp", "www.amazon.co.jp",
    "amazon.com.mx", "www.amazon.com.mx",
    "amzn.to", "amzn.eu", "a.co",
    "m.media-amazon.com", "media-amazon.com",
}


def _is_allowed_host(url: str) -> bool:
    """True si el host de `url` está en la allowlist de Amazon."""
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return host in _ALLOWED_HOSTS


def _resolves_to_private_ip(url: str) -> bool:
    """True si el host del URL resuelve a una IP privada/loopback/reservada.

    Bloqueo SSRF: evita que un atacante engañe el resolver para tocar
    servicios internos del NAS (192.168.x.x, 10.x.x.x, 127.0.0.1).
    """
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if not host:
            return True  # rechazar por defecto si no podemos analizar
        for family, _type, _proto, _canon, sockaddr in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return True
    except (socket.gaierror, ValueError, OSError):
        return True  # si el DNS falla, rechazamos por defecto
    return False

RESOURCES = [
    "itemInfo.title",
    "itemInfo.byLineInfo",
    "itemInfo.features",
    "itemInfo.productInfo",
    "itemInfo.technicalInfo",
    "itemInfo.classifications",
    "images.primary.large",
    "images.variants.large",
    "offersV2.listings.price",
    "offersV2.listings.availability",
    "offersV2.listings.dealDetails",
    "offersV2.listings.isBuyBoxWinner",
    "offersV2.listings.merchantInfo",
    "customerReviews.starRating",
    "customerReviews.count",
    "browseNodeInfo.browseNodes",
]

_AUTH_ENDPOINTS: dict[str, str] = {
    "2.1": "https://creatorsapi.auth.us-east-1.amazoncognito.com/oauth2/token",
    "2.2": "https://creatorsapi.auth.eu-south-2.amazoncognito.com/oauth2/token",
    "2.3": "https://creatorsapi.auth.us-west-2.amazoncognito.com/oauth2/token",
    "3.1": "https://api.amazon.com/auth/o2/token",
    "3.2": "https://api.amazon.co.uk/auth/o2/token",
    "3.3": "https://api.amazon.co.jp/auth/o2/token",
}

ITEMS_ENDPOINT = "https://creatorsapi.amazon/catalog/v1/getItems"


def _j(obj: Any, *keys: str, default: Any = None) -> Any:
    """Recorre dicts anidados de forma segura."""
    for key in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(key)
        if obj is None:
            return default
    return obj if obj is not None else default


def extract_asin_from_url(url_or_asin: str) -> str | None:
    """Extrae un ASIN de Amazon a partir de una URL o lo acepta directamente.

    Endurecido contra SSRF (SECURITY_AUDIT.md SEC-06):
    1) Sólo aceptamos URLs cuyo host esté en `_ALLOWED_HOSTS` (Amazon
       multi-marketplace + acortadores oficiales).
    2) Antes del fetch, validamos que el host NO resuelve a una IP privada
       (defensa contra DNS rebinding y errores de allowlist).
    """
    value = url_or_asin.strip().upper()
    if DIRECT_ASIN_RE.match(value):
        return value

    match = ASIN_RE.search(url_or_asin)
    if match:
        return match.group(1)

    if not url_or_asin.lower().startswith("http"):
        return None

    if not _is_allowed_host(url_or_asin):
        logger.warning("URL rechazada por allowlist Amazon: host no permitido")
        return None

    if _resolves_to_private_ip(url_or_asin):
        logger.warning("URL rechazada: el host resuelve a una IP privada/loopback")
        return None

    try:
        request = urllib.request.Request(url_or_asin, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            final_url = response.geturl()
    except Exception:
        logger.info("No se pudo resolver redirección de URL Amazon.", exc_info=True)
        return None

    # Tras el redirect, el host final puede haber cambiado (amzn.to → amazon.es).
    # Re-validamos que sigue dentro de la allowlist.
    if not _is_allowed_host(final_url):
        logger.warning("Redirect llevó a host fuera de la allowlist Amazon")
        return None

    match = ASIN_RE.search(final_url)
    return match.group(1) if match else None


class AmazonProductClient:
    """Obtiene productos de Amazon Creators API mediante HTTP directo."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None:
        if not self.settings.amazon_client_id or not self.settings.amazon_client_secret:
            raise ProductProviderUnavailableError("Faltan credenciales de Amazon en variables de entorno.")

        asin = extract_asin_from_url(url_or_asin)
        if not asin:
            return None

        token = self._get_token()
        item = self._fetch_item(asin, token)
        if not item:
            return None

        return self._map_item(item, asin)

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token

        version = self.settings.amazon_effective_credential_version
        auth_url = _AUTH_ENDPOINTS.get(version)
        if not auth_url:
            raise ProductProviderUnavailableError(f"Versión de credencial no soportada: {version}")

        is_lwa = version.startswith("3.")
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.settings.amazon_client_id,
            "client_secret": self.settings.amazon_client_secret,
            "scope": "creatorsapi::default" if is_lwa else "creatorsapi/default",
        }

        try:
            resp = requests.post(
                auth_url,
                json=payload if is_lwa else None,
                data=None if is_lwa else payload,
                timeout=15,
            )
        except requests.RequestException as exc:
            raise ProductProviderUnavailableError(f"Error obteniendo token Amazon: {exc}") from exc

        if resp.status_code != 200:
            text = resp.text
            if "invalid_client" in text:
                raise ProductProviderUnavailableError(
                    "Amazon rechazó las credenciales (invalid_client). "
                    "Revisa AMAZON_CLIENT_ID y AMAZON_CLIENT_SECRET."
                )
            raise ProductProviderUnavailableError(
                f"Error de autenticación Amazon ({resp.status_code}): {text[:200]}"
            )

        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600) - 30
        return self._token

    def _fetch_item(self, asin: str, token: str) -> dict | None:
        payload = {
            "partnerTag": self.settings.amazon_affiliate_tag,
            "itemIds": [asin],
            "resources": RESOURCES,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "x-marketplace": "www.amazon.es",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(ITEMS_ENDPOINT, json=payload, headers=headers, timeout=15)
        except requests.RequestException as exc:
            raise ProductProviderUnavailableError(f"Error llamando Amazon API: {exc}") from exc

        if resp.status_code != 200:
            text = resp.text
            logger.error("Amazon API error %s: %s", resp.status_code, text[:500])
            if resp.status_code >= 500 or "InternalServerException" in text:
                raise ProductProviderUnavailableError(
                    "Amazon autenticó la petición pero devolvió error interno. Reintenta más tarde."
                )
            raise ProductProviderUnavailableError(f"Amazon rechazó la petición ({resp.status_code})")

        data = resp.json()
        items = _j(data, "itemsResult", "items", default=[]) or []
        if not items:
            logger.info("Amazon no encontró el ASIN %s", asin)
            return None
        return items[0]

    def _map_item(self, item: dict, asin: str) -> ProductPreview:
        product = ProductPreview(asin=item.get("asin") or asin)
        product.product_url = f"https://www.amazon.es/dp/{product.asin}"
        product.affiliate_url = (
            item.get("detailPageURL")
            or f"{product.product_url}?tag={self.settings.amazon_affiliate_tag}"
        )

        raw_title = _j(item, "itemInfo", "title", "displayValue", default="")
        product.title = self._clean_title(raw_title)
        product.brand = _j(item, "itemInfo", "byLineInfo", "brand", "displayValue", default="")
        product.category = self._extract_category(item)
        product.features = _j(item, "itemInfo", "features", "displayValues", default=[]) or []
        product.description = " ".join(product.features[:2]) if product.features else ""
        product.image_url = _j(item, "images", "primary", "large", "url", default="")

        variants = _j(item, "images", "variants", default=[]) or []
        variant_urls = [_j(v, "large", "url") for v in variants if isinstance(v, dict)]
        all_images = []
        if product.image_url:
            all_images.append(product.image_url)
        for url in variant_urls:
            if url and url not in all_images:
                all_images.append(url)
        product.images = all_images

        self._fill_price_data(product, item)
        self._fill_deal_data(product, item)
        return product

    @staticmethod
    def _fill_deal_data(product: ProductPreview, item: dict) -> None:
        listings = _j(item, "offersV2", "listings", default=[]) or []
        if not listings:
            return
        listing = next((e for e in listings if e.get("isBuyBoxWinner")), listings[0])
        deal_end = _j(listing, "dealDetails", "endTime")
        logger.info("DEBUG: ASIN %s - deal_end raw: %s", product.asin, deal_end)
        if deal_end:
            date_part = str(deal_end).split("T")[0]
            product.expires_at = f"{date_part}T23:59:59"

    @staticmethod
    def _clean_title(raw_title: str) -> str:
        if not raw_title:
            return ""
        return re.split(r"(?:,\s+|\s+-\s+|\s+–\s+|\s+—\s+|\s+_\s+|\s+\|\s+|\|)", raw_title)[0].strip()

    @staticmethod
    def _extract_category(item: dict) -> str:
        nodes = _j(item, "browseNodeInfo", "browseNodes", default=[]) or []
        names = [n.get("displayName", "") for n in nodes if isinstance(n, dict)]
        return " > ".join([n for n in names if n][:3])

    @staticmethod
    def _fill_price_data(product: ProductPreview, item: dict) -> None:
        listings = _j(item, "offersV2", "listings", default=[]) or []
        if not listings:
            return
        listing = next((e for e in listings if e.get("isBuyBoxWinner")), listings[0])

        money = _j(listing, "price", "money")
        if isinstance(money, dict):
            product.current_price = money.get("amount")
            product.currency = money.get("currency", "EUR")

        original_money = _j(listing, "price", "savingBasis", "money")
        if isinstance(original_money, dict):
            product.original_price = original_money.get("amount")

        savings_pct = _j(listing, "price", "savings", "percentage")
        if savings_pct:
            product.discount_percentage = int(savings_pct)
        elif (
            product.current_price is not None
            and product.original_price is not None
            and product.original_price > product.current_price
        ):
            product.discount_percentage = round(
                ((product.original_price - product.current_price) / product.original_price) * 100
            )
