"""Lista centralizada de dominios permitidos para enlaces de afiliado manuales
del blog. Un único punto de configuración (§6 del encargo: "no disperses
dominios hardcodeados en componentes").

Ampliable vía la variable de entorno `BLOG_AFFILIATE_DOMAINS` (CSV) sin tocar
código; los dominios por defecto cubren las tiendas ya soportadas por el
módulo `deals`/`stores`.
"""
from __future__ import annotations

from urllib.parse import urlparse

from app.core.config import get_settings

_DEFAULT_ALLOWED_DOMAINS = frozenset({
    "amazon.es", "amzn.to", "amazon.com",
    "pccomponentes.com",
    "elcorteingles.es",
    "mediamarkt.es",
    "aliexpress.com", "s.click.aliexpress.com",
})


def extract_domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def get_allowed_affiliate_domains() -> frozenset[str]:
    settings = get_settings()
    extra = getattr(settings, "blog_affiliate_domains", None)
    if not extra:
        return _DEFAULT_ALLOWED_DOMAINS
    extra_domains = {d.strip().lower() for d in extra.split(",") if d.strip()}
    return _DEFAULT_ALLOWED_DOMAINS | frozenset(extra_domains)
