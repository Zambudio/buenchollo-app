"""Tests del resumen nocturno de alertas (TD-26).

Usan modelos ORM reales (`Deal`, `Alert`, `Store`) a propósito: el worker leía
atributos inexistentes (`deal.price`, `Deal.is_active`, `branding.base_url`) y un
stub con SimpleNamespace los habría aceptado sin fallar.
"""
from datetime import date
from decimal import Decimal

from app.modules.alerts.domain.models import Alert
from app.modules.deals.domain.models import Deal
from app.modules.emails.application.digest_worker import build_user_digests
from app.modules.emails.application.rendering import EmailBranding, render_alert_digest
from app.modules.stores.domain.models import Store


def _deal(**overrides) -> Deal:
    base = dict(
        id="deal-1",
        title="Portátil HP Victus",
        slug="portatil-hp-victus",
        description="Portátil gaming con RTX",
        brand="HP",
        current_price=Decimal("699.00"),
        previous_price=Decimal("899.00"),
        discount_percentage=22,
        affiliate_url="https://www.amazon.es/dp/B0TEST1234",
        external_id="B0TEST1234",
        show_keepa_chart=True,
        status="active",
        category_id="cat-1",
        store_id="store-1",
    )
    base.update(overrides)
    deal = Deal(**base)
    deal.store = Store(id="store-1", name="Amazon", slug="amazon")
    return deal


def _alert(**overrides) -> Alert:
    base = dict(id="alert-1", user_id="user-1", name="Portátiles", keyword="portátil", notify_email=True)
    base.update(overrides)
    return Alert(**base)


def test_agrupa_por_usuario_con_los_campos_reales_del_chollo():
    digests = build_user_digests(EmailBranding(), [_alert()], [_deal()])

    [item] = digests["user-1"]
    assert item.price == format_price("699,00")
    assert item.previous_price == format_price("899,00")
    assert item.discount == 22
    assert item.store == "Amazon"
    assert item.alert_names == ("Portátiles",)
    assert "/chollo/portatil-hp-victus" in item.url
    assert item.price_history_url and "B0TEST1234" in item.price_history_url


def test_un_chollo_aparece_una_vez_con_todas_las_alertas_que_lo_disparan():
    alerts = [_alert(), _alert(id="alert-2", name="Marca HP", keyword=None, brand="hp")]

    digests = build_user_digests(EmailBranding(), alerts, [_deal()])

    [item] = digests["user-1"]
    assert item.alert_names == ("Portátiles", "Marca HP")


def test_usuarios_sin_coincidencias_no_reciben_resumen():
    alerts = [_alert(), _alert(id="alert-2", user_id="user-2", keyword="televisor")]

    digests = build_user_digests(EmailBranding(), alerts, [_deal()])

    assert list(digests) == ["user-1"]


def test_respeta_precio_maximo_y_sin_historico_si_el_chollo_no_lo_muestra():
    deal_barato = _deal(id="deal-2", slug="barato", current_price=Decimal("300"), show_keepa_chart=False)
    alerts = [_alert(max_price=Decimal("500"))]

    [item] = build_user_digests(EmailBranding(), alerts, [_deal(), deal_barato])["user-1"]

    assert "/chollo/barato" in item.url
    assert item.price_history_url is None


def test_el_resumen_se_renderiza_con_el_enlace_de_baja():
    branding = EmailBranding()
    deals = build_user_digests(branding, [_alert()], [_deal()])["user-1"]

    rendered = render_alert_digest(
        branding,
        name="Ana",
        digest_date=date(2026, 11, 7),
        deals=deals,
        unsubscribe_url=f"{branding.site_url}/perfil?tab=alertas",
    )

    assert "Portátil HP Victus" in rendered.html
    assert "/perfil?tab=alertas" in rendered.html


def format_price(value: str) -> str:
    """Formato EUR de `format_eur` (coma decimal y símbolo al final)."""
    return f"{value} €"
