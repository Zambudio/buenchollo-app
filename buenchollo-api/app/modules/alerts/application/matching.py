"""Reglas puras de matching entre Alert y Deal.

Vive en la capa de aplicación porque expresa lógica de negocio: la decisión
de qué alerta dispara qué deal. El repositorio se limita a recuperar las
alertas activas; este módulo decide cuáles coinciden.

Funciones puras, sin BD ni I/O — fácilmente testeables.
"""
from app.modules.alerts.domain.models import Alert
from app.modules.deals.domain.models import Deal


def matches_alert(alert: Alert, deal: Deal) -> bool:
    """¿Coincide `alert` con `deal`? Aplica los criterios en orden de coste
    creciente y devuelve `False` en el primer fallo."""
    title = (deal.title or "").lower()
    description = (deal.description or "").lower()
    deal_brand = (deal.brand or "").lower()

    if alert.keyword:
        kw = alert.keyword.lower()
        if kw not in title and kw not in description and kw not in deal_brand:
            return False

    if alert.category_id and alert.category_id not in (
        deal.category_id, getattr(deal, "subcategory_id", None),
    ):
        return False

    if alert.store_id and alert.store_id != deal.store_id:
        return False

    if alert.brand and alert.brand.lower() not in deal_brand:
        return False

    if alert.max_price is not None and float(deal.current_price) > float(alert.max_price):
        return False

    if alert.min_discount is not None and (deal.discount_percentage or 0) < alert.min_discount:
        return False

    return True
