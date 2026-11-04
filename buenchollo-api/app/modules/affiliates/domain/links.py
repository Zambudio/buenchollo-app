import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.exceptions import ValidationError

MAX_URL_LENGTH = 2048

AMAZON_SHORT_HOSTS = frozenset({"amzn.to", "amzn.eu", "a.co", "link.amazon"})

# Acortadores genéricos: ocultan el destino real y saltarían la reescritura de
# afiliación (y la detección de duplicados). Los de Amazon se resuelven aparte.
GENERIC_SHORTENER_HOSTS = frozenset(
    {
        "bit.ly",
        "bitly.com",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "ow.ly",
        "buff.ly",
        "rebrand.ly",
        "shorturl.at",
        "cutt.ly",
        "is.gd",
        "v.gd",
        "t.ly",
        "rb.gy",
        "tiny.cc",
        "bl.ink",
        "lnkd.in",
        "amzlink.to",
        "s.click.aliexpress.com",
        "a.aliexpress.com",
        "ebay.us",
    }
)
SHORTENER_NOT_ALLOWED = "Pega el enlace directo del producto, sin acortadores"

_AMAZON_HOST_RE = re.compile(r"^(?:www\.)?amazon\.(?P<tld>[a-z]{2,3}(?:\.[a-z]{2})?)$")
_AMAZON_ASIN_PATH_RE = re.compile(r"/(?:dp|gp/product|gp/aw/d|product)/([A-Z0-9]{10})(?:[/?#]|$)")
_AMAZON_ASIN_PATH_CI_RE = re.compile(r"/(?:dp|gp/product|gp/aw/d|product)/([a-z0-9]{10})(?:[/?#]|$)", re.IGNORECASE)
_ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")

_TRACKING_EXACT = frozenset(
    {
        "fbclid",
        "gclid",
        "msclkid",
        "ref",
        "ref_",
        "tag",
        "ascsubtag",
        "linkcode",
        "linkid",
        "psc",
        "th",
        "smid",
        "spm",
        "clickref",
        "irclickid",
        "srsltid",
    }
)
_TRACKING_PREFIXES = ("utm_", "aff_", "affiliate")
_TRAILING_PUNCTUATION = "!.,;:)]}'\"»”’?"
_LEADING_PUNCTUATION = "(['\"«“‘<"
_KNOWN_HOST_START_RE = re.compile(
    r"^(?:www\.|(?:[a-z0-9-]+\.)?amazon\.[a-z]{2,3}(?:\.[a-z]{2})?/|amzn\.to/|amzn\.eu/|a\.co/|link\.amazon/)",
    re.IGNORECASE,
)


class InvalidLinkError(ValidationError):
    """El texto no contiene un enlace http(s) válido."""


@dataclass(frozen=True)
class CanonicalLink:
    url: str
    canonical_url: str
    host: str
    asin: str | None


def _normalize_host(netloc: str) -> str:
    host = netloc.rsplit("@", 1)[-1].split(":", 1)[0].lower()
    return host.removeprefix("www.")


def is_amazon_host(host: str) -> bool:
    return _AMAZON_HOST_RE.match(host.lower()) is not None


def is_amazon_short_host(host: str) -> bool:
    return host.lower().removeprefix("www.") in AMAZON_SHORT_HOSTS


def is_generic_shortener_host(host: str) -> bool:
    return host.lower().removeprefix("www.") in GENERIC_SHORTENER_HOSTS


def is_tracking_param(name: str) -> bool:
    lowered = name.lower()
    return lowered in _TRACKING_EXACT or lowered.startswith(_TRACKING_PREFIXES)


def extract_url(raw: str) -> str:
    candidate = None
    for token in (raw or "").split():
        token = token.lstrip(_LEADING_PUNCTUATION)
        lowered = token.lower()
        if lowered.startswith(("http://", "https://")):
            candidate = token
            break
        if _KNOWN_HOST_START_RE.match(token):
            candidate = f"https://{token}"
            break
    if candidate is None:
        raise InvalidLinkError("No se ha encontrado ningún enlace válido.")
    candidate = candidate.rstrip(_TRAILING_PUNCTUATION)
    if len(candidate) > MAX_URL_LENGTH:
        raise InvalidLinkError("El enlace es demasiado largo.")
    parts = urlsplit(candidate)
    host = _normalize_host(parts.netloc)
    if parts.scheme not in ("http", "https") or "." not in host:
        raise InvalidLinkError("No se ha encontrado ningún enlace válido.")
    if not _is_public_store_netloc(parts.netloc):
        raise InvalidLinkError(PUBLIC_STORE_REQUIRED)
    return candidate


PUBLIC_STORE_REQUIRED = "El enlace debe ser la página pública de una tienda"
_INTERNAL_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home", ".corp", ".test", ".invalid", ".example")
_TLD_RE = re.compile(r"^(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})$")


def _is_public_store_netloc(netloc: str) -> bool:
    """Un chollo enlaza a la web pública de una tienda: ni IPs, ni hosts internos,
    ni credenciales en la URL (`https://www.amazon.es@otra-web.com`), ni puertos raros."""
    if "@" in netloc:
        return False
    try:
        port = urlsplit(f"//{netloc}").port
    except ValueError:
        return False
    if port not in (None, 80, 443):
        return False
    host = netloc.split(":", 1)[0].lower().rstrip(".")
    if not host or host.startswith("[") or host == "localhost" or host.endswith(_INTERNAL_SUFFIXES):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return _TLD_RE.match(host.rsplit(".", 1)[-1]) is not None


def clean_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not is_tracking_param(k)
    )
    host = parts.netloc.rsplit("@", 1)[-1].lower()
    path = parts.path.rstrip("/")
    return urlunsplit(("https", host, path, urlencode(query), ""))


def extract_asin(path: str) -> str | None:
    # Amazon acepta el ASIN en minúsculas (`/dp/b09b8x9rgm`); sin normalizarlo
    # el enlace se quedaba sin tag de afiliado y saltaba la detección de
    # duplicados. Se exige un dígito para no confundir palabras de la ruta.
    match = _AMAZON_ASIN_PATH_RE.search(path) or _AMAZON_ASIN_PATH_CI_RE.search(path)
    if not match:
        return None
    asin = match.group(1).upper()
    return asin if any(c.isdigit() for c in asin) else None


def ensure_not_shortened(link: CanonicalLink) -> None:
    if is_generic_shortener_host(link.host):
        raise InvalidLinkError(SHORTENER_NOT_ALLOWED)


def canonicalize(url: str, *, asin: str | None = None) -> CanonicalLink:
    parts = urlsplit(url.strip())
    host = _normalize_host(parts.netloc)
    cleaned = clean_url(url)
    cleaned_parts = urlsplit(cleaned)
    canonical = urlunsplit(
        ("https", host, cleaned_parts.path, cleaned_parts.query, "")
    )
    resolved_asin: str | None = None
    if is_amazon_host(host):
        explicit = asin.upper() if asin else None
        if explicit and _ASIN_RE.match(explicit):
            resolved_asin = explicit
        else:
            resolved_asin = extract_asin(parts.path)
        if resolved_asin:
            tld = _AMAZON_HOST_RE.match(host).group("tld")  # type: ignore[union-attr]
            canonical = f"https://www.amazon.{tld}/dp/{resolved_asin}"
    return CanonicalLink(url=url.strip(), canonical_url=canonical, host=host, asin=resolved_asin)
