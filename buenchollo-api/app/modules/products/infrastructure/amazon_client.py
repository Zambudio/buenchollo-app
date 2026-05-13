"""Amazon Creators API adapter for product previews."""

import logging
import re
import urllib.request
from typing import Any

from app.core.config import Settings
from app.modules.products.application.preview_product_from_url import ProductProviderUnavailableError
from app.modules.products.domain.entities import ProductPreview

try:
    from amazon_creatorsapi import AmazonCreatorsApi
    from amazon_creatorsapi.core.marketplaces import Country
    from creatorsapi_python_sdk.models.get_items_request_content import GetItemsRequestContent
    from creatorsapi_python_sdk.models.get_items_resource import GetItemsResource
except ImportError:
    AmazonCreatorsApi = None
    Country = None
    GetItemsRequestContent = None

    class _MissingGetItemsResource:
        def __getattr__(self, name: str) -> str:
            return name

    GetItemsResource = _MissingGetItemsResource()


logger = logging.getLogger(__name__)

ASIN_RE = re.compile(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})")
DIRECT_ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")

RESOURCES = [
    GetItemsResource.ITEM_INFO_DOT_TITLE,
    GetItemsResource.ITEM_INFO_DOT_BY_LINE_INFO,
    GetItemsResource.ITEM_INFO_DOT_FEATURES,
    GetItemsResource.ITEM_INFO_DOT_PRODUCT_INFO,
    GetItemsResource.ITEM_INFO_DOT_TECHNICAL_INFO,
    GetItemsResource.ITEM_INFO_DOT_CLASSIFICATIONS,
    GetItemsResource.IMAGES_DOT_PRIMARY_DOT_LARGE,
    GetItemsResource.IMAGES_DOT_VARIANTS_DOT_LARGE,
    GetItemsResource.OFFERS_V2_DOT_LISTINGS_DOT_PRICE,
    GetItemsResource.OFFERS_V2_DOT_LISTINGS_DOT_AVAILABILITY,
    GetItemsResource.OFFERS_V2_DOT_LISTINGS_DOT_DEAL_DETAILS,
    GetItemsResource.OFFERS_V2_DOT_LISTINGS_DOT_IS_BUY_BOX_WINNER,
    GetItemsResource.OFFERS_V2_DOT_LISTINGS_DOT_MERCHANT_INFO,
    GetItemsResource.CUSTOMER_REVIEWS_DOT_STAR_RATING,
    GetItemsResource.CUSTOMER_REVIEWS_DOT_COUNT,
    GetItemsResource.BROWSE_NODE_INFO_DOT_BROWSE_NODES,
]


def _safe(obj: Any, *attrs: str, default: Any = None) -> Any:
    """Traverse nested SDK objects without leaking AttributeError."""
    for attr in attrs:
        if obj is None:
            return default
        obj = getattr(obj, attr, None)
    return obj if obj is not None else default


def extract_asin_from_url(url_or_asin: str) -> str | None:
    """Extract an Amazon ASIN from a URL or accept a direct ASIN."""
    value = url_or_asin.strip().upper()
    if DIRECT_ASIN_RE.match(value):
        return value

    match = ASIN_RE.search(url_or_asin)
    if match:
        return match.group(1)

    if not url_or_asin.lower().startswith("http"):
        return None

    try:
        request = urllib.request.Request(url_or_asin, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            final_url = response.geturl()
    except Exception:
        logger.info("No se pudo resolver redirección de URL Amazon.", exc_info=True)
        return None

    match = ASIN_RE.search(final_url)
    return match.group(1) if match else None


def _format_price(value: float | None, currency: str) -> str:
    if value is None:
        return "Precio no disponible"
    symbol = "EUR" if currency != "EUR" else "EUR"
    return f"{value:.2f} {symbol}"


def build_telegram_text(product: ProductPreview) -> str:
    """Build a first version of the Telegram deal text."""
    current_price = _format_price(product.current_price, product.currency)
    original_price = _format_price(product.original_price, product.currency)
    description = product.description or "Sin descripción técnica adicional."
    url = product.affiliate_url or product.product_url

    lines = [f"🍄 {product.title or 'Título no disponible'}", ""]
    if product.original_price:
        lines.append(f"💶 Precio: {current_price} (antes {original_price})")
    else:
        lines.append(f"💶 Precio: {current_price}")

    if product.discount_percentage:
        lines.append(f"💰 Descuento: -{product.discount_percentage} %")

    lines.extend(["", f"🛒 {url}", "", f"✏️{description}"])
    return "\n".join(lines)


class AmazonProductClient:
    """Fetch products from Amazon Creators API and map them to domain objects."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None:
        """Fetch a product preview from Amazon by URL or ASIN."""
        self._validate_configuration()
        asin = extract_asin_from_url(url_or_asin)
        if not asin:
            return None

        items = self._get_items(asin)
        if not items:
            return None

        return self._map_item_to_preview(items[0], asin)

    def _validate_configuration(self) -> None:
        if AmazonCreatorsApi is None or Country is None or GetItemsRequestContent is None:
            raise ProductProviderUnavailableError("La librería creators no está instalada.")
        if not self.settings.amazon_client_id or not self.settings.amazon_client_secret:
            raise ProductProviderUnavailableError("Faltan credenciales de Amazon en variables de entorno.")

    def _get_items(self, asin: str) -> list[Any]:
        configured_version = self.settings.amazon_effective_credential_version
        versions = (
            [configured_version]
            if configured_version
            else list(self.settings.amazon_supported_credential_versions)
        )
        last_error: Exception | None = None

        for credential_version in versions:
            try:
                return self._get_items_with_credential_version(asin, credential_version)
            except Exception as exc:
                last_error = exc
                if configured_version or "invalid_client" not in str(exc):
                    break

        logger.error("Error consultando Amazon Creators API: %s", last_error)
        error_text = str(last_error) if last_error else ""
        if "invalid_client" in error_text:
            raise ProductProviderUnavailableError(
                "Amazon rechazó las credenciales configuradas (invalid_client). "
                "Revisa AMAZON_CLIENT_ID y AMAZON_CLIENT_SECRET."
            )
        if "InternalServerException" in error_text or "Internal Server Error" in error_text:
            raise ProductProviderUnavailableError(
                "Amazon autenticó la petición, pero su API devolvió un error interno. "
                "Reintenta más tarde o prueba otro ASIN."
            )
        raise ProductProviderUnavailableError("Amazon no está disponible o rechazó la configuración actual.")

    def _get_items_with_credential_version(self, asin: str, credential_version: str) -> list[Any]:
        api = AmazonCreatorsApi(
            credential_id=self.settings.amazon_client_id,
            credential_secret=self.settings.amazon_client_secret,
            version=credential_version,
            tag=self.settings.amazon_affiliate_tag,
            country=Country.ES,
        )
        return api.get_items(asin, resources=RESOURCES)

    @staticmethod
    def _extract_items_from_response(response: Any) -> list[Any]:
        if isinstance(response, list):
            return response
        items_result = getattr(response, "items_result", None)
        return getattr(items_result, "items", None) or []

    def _map_item_to_preview(self, item: Any, asin: str) -> ProductPreview:
        product = ProductPreview(asin=getattr(item, "asin", None) or asin)
        product.product_url = f"https://www.amazon.es/dp/{product.asin}"
        product.affiliate_url = (
            getattr(item, "detail_page_url", None)
            or f"{product.product_url}?tag={self.settings.amazon_affiliate_tag}"
        )

        raw_title = _safe(item, "item_info", "title", "display_value", default="")
        product.title = self._clean_title(raw_title)
        product.brand = _safe(item, "item_info", "by_line_info", "brand", "display_value", default="")
        product.category = self._extract_category(item)
        product.features = self._extract_features(item)
        product.description = " ".join(product.features[:2]) if product.features else ""
        product.image_url = _safe(item, "images", "primary", "large", "url", default="")

        self._fill_price_data(product, item)
        product.telegram_text = build_telegram_text(product)
        return product

    @staticmethod
    def _clean_title(raw_title: str) -> str:
        if not raw_title:
            return ""
        return re.split(r"(?:,\s+|\s+-\s+|\s+–\s+|\s+—\s+|\s+_\s+|\s+\|\s+|\|)", raw_title)[0].strip()

    @staticmethod
    def _extract_category(item: Any) -> str:
        nodes = _safe(item, "browse_node_info", "browse_nodes", default=[])
        if not nodes:
            return ""
        names = [getattr(node, "display_name", "") for node in nodes]
        return " > ".join([name for name in names if name][:3])

    @staticmethod
    def _extract_features(item: Any) -> list[str]:
        features = _safe(item, "item_info", "features", "display_values", default=[])
        return [feature for feature in features if feature]

    @staticmethod
    def _fill_price_data(product: ProductPreview, item: Any) -> None:
        listings = _safe(item, "offers_v2", "listings", default=[])
        if not listings:
            return

        listing = next((entry for entry in listings if getattr(entry, "is_buy_box_winner", False)), listings[0])
        price_money = _safe(listing, "price", "money")
        if price_money:
            product.current_price = getattr(price_money, "amount", None)
            product.currency = getattr(price_money, "currency", "EUR")

        original_money = _safe(listing, "price", "saving_basis", "money")
        if original_money:
            product.original_price = getattr(original_money, "amount", None)

        savings_percentage = _safe(listing, "price", "savings", "percentage")
        if savings_percentage:
            product.discount_percentage = int(savings_percentage)
        elif (
            product.current_price is not None
            and product.original_price is not None
            and product.original_price > product.current_price
        ):
            product.discount_percentage = round(
                ((product.original_price - product.current_price) / product.original_price) * 100
            )
