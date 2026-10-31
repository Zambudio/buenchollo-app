"""Tipos de datos de los correos: lo que se renderiza y lo que se envía.

Sin I/O ni dependencias de infraestructura: los servicios de aplicación los
construyen y el remitente SMTP los consume.
"""
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    html: str
    text: str
    # Cabeceras extra (p. ej. List-Unsubscribe para la baja con un clic).
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DigestDeal:
    """Chollo ya formateado para la plantilla del resumen de alertas."""

    title: str
    url: str
    image_url: str | None
    price: str
    previous_price: str | None
    discount: int | None
    store: str | None
    short_description: str | None
    expires_label: str | None
    price_history_url: str | None
    savings: str | None
    alert_names: tuple[str, ...] = ()
    savings_amount: Decimal | None = None
