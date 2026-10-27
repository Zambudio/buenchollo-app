"""Renderizado de los correos (HTML + texto plano) con Jinja2.

Funciones puras respecto a la BD: reciben datos ya cargados y devuelven
`RenderedEmail`. Así las plantillas se prueban sin SMTP ni base de datos y el
mismo código genera las vistas previas.
"""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.modules.emails.application.theme import THEME
from app.modules.emails.domain.messages import DigestDeal, RenderedEmail

MADRID = ZoneInfo("Europe/Madrid")
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
TELEGRAM_URL = "https://t.me/buenchollotech"
# Tope de tarjetas por correo: Gmail recorta los mensajes de más de ~102 KB.
MAX_DIGEST_DEALS = 8

_MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(enabled_extensions=("html.j2",), default_for_string=False),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def format_eur(value: float | Decimal | str | None) -> str | None:
    """1299.5 -> '1.299,50 €' (formato español)."""
    if value is None:
        return None
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    whole, cents = f"{amount:,.2f}".split(".")
    return f"{whole.replace(',', '.')},{cents} €"


def format_short_datetime(dt: datetime) -> str:
    """'31 oct, 23:59' en hora de Madrid."""
    local = dt.astimezone(MADRID)
    return f"{local.day} {_MONTHS[local.month - 1]}, {local:%H:%M}"


def format_short_date(d: date) -> str:
    return f"{d.day} {_MONTHS[d.month - 1]}"


def with_utm(url: str, campaign: str) -> str:
    """Añade utm_source/medium=email para atribuir la visita al correo en la
    analítica de la web (`features/analytics/lib/tracking.ts`)."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.startswith("utm_")]
    query += [("utm_source", "email"), ("utm_medium", "email"), ("utm_campaign", campaign)]
    return urlunsplit(parts._replace(query=urlencode(query)))


def keepa_chart_url(asin: str) -> str:
    return (
        "https://graph.keepa.com/pricehistory.png?"
        + urlencode({"asin": asin, "domain": "es", "width": 514, "height": 200, "range": 90})
    )


@dataclass(frozen=True)
class EmailBranding:
    """URLs públicas usadas por todas las plantillas."""

    site_url: str = "https://buenchollotech.com"
    contact_email: str = "contacto@buenchollotech.com"

    @property
    def assets(self) -> dict[str, str]:
        return {
            "logo": f"{self.site_url}/email/logo-144.png",
            "logo_small": f"{self.site_url}/email/logo-64.png",
        }

    def links(self, campaign: str) -> dict[str, str]:
        site = self.site_url
        return {
            "home": with_utm(f"{site}/", campaign),
            "explore": with_utm(f"{site}/explorar", campaign),
            "alerts": with_utm(f"{site}/alertas", campaign),
            "new_alert": with_utm(f"{site}/alertas/nueva", campaign),
            "notifications": with_utm(f"{site}/notificaciones", campaign),
            "preferences": with_utm(f"{site}/perfil#correos", campaign),
            "telegram": TELEGRAM_URL,
        }


def build_digest_deal(
    *,
    branding: EmailBranding,
    title: str,
    slug: str,
    image_url: str | None,
    current_price: float | Decimal,
    previous_price: float | Decimal | None,
    discount_percentage: int | None,
    store_name: str | None,
    short_description: str | None,
    expires_at: datetime | None,
    asin: str | None,
    show_price_history: bool,
    alert_names: tuple[str, ...],
) -> DigestDeal:
    has_previous = previous_price is not None and Decimal(str(previous_price)) > Decimal(str(current_price))
    savings_amount = (
        Decimal(str(previous_price)) - Decimal(str(current_price)) if has_previous else None
    )
    return DigestDeal(
        title=title,
        url=with_utm(f"{branding.site_url}/chollo/{slug}", "alertas"),
        image_url=image_url,
        price=format_eur(current_price) or "",
        previous_price=format_eur(previous_price) if has_previous else None,
        discount=discount_percentage or None,
        store=store_name,
        short_description=short_description,
        expires_label=format_short_datetime(expires_at) if expires_at else None,
        price_history_url=keepa_chart_url(asin) if (show_price_history and asin) else None,
        savings=format_eur(savings_amount),
        alert_names=alert_names,
        savings_amount=savings_amount,
    )


def _base_context(branding: EmailBranding, campaign: str) -> dict:
    return {
        "t": THEME,
        "assets": branding.assets,
        "links": branding.links(campaign),
        "contact_email": branding.contact_email,
        "header_tag": None,
        "footer_reason": None,
        "footer_links": [],
        "show_affiliate_note": False,
    }


def _render(name: str, context: dict) -> RenderedEmail:
    html = _env.get_template(f"{name}.html.j2").render(context)
    text = _env.get_template(f"{name}.txt.j2").render(context)
    return RenderedEmail(subject=context["subject"], html=html, text=text.strip() + "\n")


def render_welcome(branding: EmailBranding, *, name: str | None) -> RenderedEmail:
    ctx = _base_context(branding, "bienvenida")
    ctx.update(
        subject="Te damos la bienvenida a BuenChollo Tech 🎉",
        preheader="Ya formas parte de la comunidad que caza los mejores chollos de tecnología.",
        header_tag="BIENVENIDA",
        name=(name or "").strip() or None,
        footer_reason="Recibes este correo porque acabas de crear tu cuenta en BuenChollo Tech.",
        footer_links=[
            ("Mi perfil", ctx["links"]["preferences"]),
            ("Canal de Telegram", ctx["links"]["telegram"]),
        ],
    )
    return _render("welcome", ctx)


def render_alert_digest(
    branding: EmailBranding,
    *,
    name: str | None,
    digest_date: date,
    deals: list[DigestDeal],
    unsubscribe_url: str,
) -> RenderedEmail:
    """Resumen diario: un único correo con todos los chollos del día que
    encajan con las alertas del usuario."""
    if not deals:
        raise ValueError("Un resumen de alertas necesita al menos un chollo")
    shown = deals[:MAX_DIGEST_DEALS]
    count = len(deals)
    alert_names = list(dict.fromkeys(n for d in deals for n in d.alert_names))
    name = (name or "").strip() or None

    savings_total = sum((d.savings_amount for d in deals if d.savings_amount), Decimal("0"))
    max_discount = max((d.discount or 0) for d in deals)

    if count == 1:
        subject = f"🔔 Tu alerta tiene un chollo: {_truncate(deals[0].title, 48)} a {deals[0].price}"
        headline = "1 chollo de tus alertas"
        intro = "Hoy ha salido una oferta que encaja con lo que buscas. Aquí la tienes, con todos los detalles."
    else:
        subject = f"🔔 {count} chollos de tus alertas de hoy"
        headline = f"{count} chollos de tus alertas"
        intro = (
            "Hoy han salido ofertas que encajan con lo que buscas. "
            "Te las dejamos todas juntas, como cada noche."
        )
    greeting = f"Hola, {name}: {headline[0].lower()}{headline[1:]}" if name else headline
    preheader = (
        f"Hasta -{max_discount}% · {deals[0].title}" if max_discount else deals[0].title
    )

    ctx = _base_context(branding, "alertas")
    ctx["links"]["unsubscribe"] = unsubscribe_url
    ctx.update(
        subject=subject,
        preheader=preheader,
        header_tag="ALERTAS",
        greeting=greeting,
        intro=intro,
        date_label=format_short_date(digest_date),
        deals=shown,
        hidden_count=count - len(shown),
        alert_names=alert_names,
        stats={
            "count": count,
            "max_discount": max_discount,
            "total_savings": format_eur(savings_total) if savings_total else None,
        },
        show_affiliate_note=True,
        footer_reason=(
            "Recibes este resumen porque activaste el aviso por correo en tus alertas "
            "de BuenChollo Tech. Solo te escribimos los días en que hay chollos para ti."
        ),
        footer_links=[
            ("Gestionar alertas", ctx["links"]["alerts"]),
            ("Preferencias", ctx["links"]["preferences"]),
            ("Darme de baja", unsubscribe_url),
        ],
    )
    return _render("alert_digest", ctx)


def render_auth_template(branding: EmailBranding, **content: str | None) -> str:
    """HTML de un correo de Supabase Auth. Los valores de `content` pueden
    contener variables de plantilla de Supabase (`{{ .ConfirmationURL }}`),
    que se copian tal cual."""
    ctx = _base_context(branding, "cuenta")
    ctx.update(
        preheader=content.get("preheader") or content["intro"],
        header_tag="CUENTA",
        footer_reason=(
            "Has recibido este correo porque se solicitó esta acción en buenchollotech.com. "
            "Si no has sido tú, puedes ignorarlo con tranquilidad."
        ),
        icon="✉️",
        detail=None,
        code=None,
        action_url=None,
        button_label=None,
        expiry_note=None,
        safety_note=(
            "Nunca te pediremos tu contraseña por correo. Si no has solicitado esta acción, "
            "ignora este mensaje: tu cuenta sigue segura."
        ),
    )
    ctx.update({k: v for k, v in content.items() if v is not None})
    return _env.get_template("auth_action.html.j2").render(ctx)


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
