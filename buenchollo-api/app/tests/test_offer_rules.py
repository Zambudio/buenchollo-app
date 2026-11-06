from decimal import Decimal

import pytest

from app.modules.catalog.domain.offer_rules import (
    Observation,
    OfferState,
    RulesConfig,
    availability_of,
    decide,
    rules_config_from,
)

CFG = RulesConfig()


def _obs(price="100", *, found=True, in_stock=True, reference=None, discount=None):
    return Observation(
        found=found,
        in_stock=in_stock,
        price=Decimal(price) if price is not None else None,
        reference_price=Decimal(reference) if reference is not None else None,
        discount_percentage=discount,
    )


def _state(status="active", *, offer="100", previous=None, reason=None):
    return OfferState(
        status=status,
        offer_end_reason=reason,
        offer_price=Decimal(offer) if offer is not None else None,
        previous_price=Decimal(previous) if previous is not None else None,
    )


@pytest.mark.parametrize(
    "price, expected",
    [("110.01", ("end", "price_increase")), ("110", ("keep", None)), ("96", ("keep", None)), ("90", ("drop", "price_drop"))],
)
def test_active_sube_mas_de_tolerancia_termina(price, expected):
    assert decide(_state(offer="100"), _obs(price), CFG) == expected


def test_active_sin_stock_termina_out_of_stock():
    assert decide(_state(), _obs(in_stock=False), CFG) == ("end", "out_of_stock")


def test_active_no_encontrado_termina_not_found():
    assert decide(_state(), _obs(None, found=False, in_stock=False), CFG) == ("end", "not_found")


def test_active_descuento_cero_termina_no_longer_deal():
    assert decide(_state(), _obs("100", discount=0), CFG) == ("end", "no_longer_deal")


def test_active_alcanza_previous_price_termina():
    # Dentro de la tolerancia (95 × 1,10 = 104,5) pero ya al precio "antes".
    state = _state(offer="95", previous="100")
    assert decide(state, _obs("100"), CFG) == ("end", "no_longer_deal")
    assert decide(state, _obs("97"), CFG) == ("keep", None)
    # Por encima de la tolerancia gana price_increase (misma prioridad que antes).
    assert decide(_state(offer="80", previous="100"), _obs("100"), CFG) == ("end", "price_increase")


def test_active_con_cupon_sin_descuento_informado_se_mantiene():
    assert decide(_state(offer="100"), _obs("100", discount=None), CFG) == ("keep", None)


def test_active_sin_precio_pero_en_stock_se_mantiene():
    assert decide(_state(), _obs(None), CFG) == ("keep", None)


def test_active_sin_offer_price_solo_termina_por_stock_o_descuento():
    state = _state(offer=None)
    assert decide(state, _obs("999"), CFG) == ("keep", None)
    assert decide(state, _obs("999", discount=0), CFG) == ("end", "no_longer_deal")


@pytest.mark.parametrize("reason", ["price_increase", "no_longer_deal", "out_of_stock", "not_found"])
def test_expired_vuelve_a_su_precio_se_reactiva(reason):
    state = _state("expired", offer="80", reason=reason)
    assert decide(state, _obs("80"), CFG) == ("reactivate", None)
    assert decide(state, _obs("79.99"), CFG) == ("reactivate", None)


def test_expired_por_subida_solo_se_reactiva_al_volver_a_su_precio():
    """Regresión (datos reales): subió de 114,15 a 123,29 y Amazon le seguía
    marcando un 10 % frente a su referencia; reactivarlo por ese descuento
    convertía una subida en un «vuelve a estar en oferta»."""
    state = _state("expired", offer="114.15", reason="price_increase")
    assert decide(state, _obs("123.29", discount=10), CFG) == ("none", None)
    assert decide(state, _obs("114.16", discount=40), CFG) == ("none", None)
    assert decide(state, _obs("114.15"), CFG) == ("reactivate", None)


def test_expired_por_no_rebajado_se_reactiva_si_vuelve_el_descuento():
    state = _state("expired", offer="80", reason="no_longer_deal")
    assert decide(state, _obs("85", discount=5), CFG) == ("reactivate", None)
    assert decide(state, _obs("85", discount=4), CFG) == ("none", None)
    assert decide(state, _obs("85"), CFG) == ("none", None)
    # Fuera de la tolerancia (80 × 1,10 = 88) no vale ni con descuento alto
    assert decide(state, _obs("88.01", discount=30), CFG) == ("none", None)


@pytest.mark.parametrize("reason", ["out_of_stock", "not_found"])
def test_expired_sin_stock_vuelve_dentro_de_la_tolerancia(reason):
    state = _state("expired", offer="80", reason=reason)
    assert decide(state, _obs("88"), CFG) == ("reactivate", None)
    assert decide(state, _obs("88.01"), CFG) == ("none", None)
    assert decide(state, _obs("85", discount=0), CFG) == ("none", None)


def test_expired_sin_stock_o_no_encontrado_no_se_reactiva():
    state = _state("expired", offer="80", reason="out_of_stock")
    assert decide(state, _obs("70", in_stock=False), CFG) == ("none", None)
    assert decide(state, _obs(None, found=False, in_stock=False), CFG) == ("none", None)
    assert decide(state, _obs(None), CFG) == ("none", None)


@pytest.mark.parametrize("reason", ["expired_date", "manual", None])
def test_expired_por_fecha_o_manual_no_se_reactiva(reason):
    state = _state("expired", offer="80", reason=reason)
    assert decide(state, _obs("50", discount=40), CFG) == ("none", None)


@pytest.mark.parametrize("status", ["draft", "scheduled"])
def test_draft_y_scheduled_nunca_cambian(status):
    state = _state(status, offer="80")
    assert decide(state, _obs("200"), CFG) == ("none", None)
    assert decide(state, _obs(None, found=False, in_stock=False), CFG) == ("none", None)


def test_rules_config_from_valores_por_defecto():
    assert rules_config_from({}) == RulesConfig(Decimal("10"), 5)


@pytest.mark.parametrize(
    "config, expected",
    [
        ({"price_tolerance_percent": 150}, RulesConfig(Decimal("10"), 5)),
        ({"price_tolerance_percent": "abc"}, RulesConfig(Decimal("10"), 5)),
        ({"price_tolerance_percent": 5}, RulesConfig(Decimal("5"), 5)),
        ({"min_discount_percent": -1}, RulesConfig(Decimal("10"), 5)),
        ({"min_discount_percent": "x"}, RulesConfig(Decimal("10"), 5)),
        ({"min_discount_percent": 15}, RulesConfig(Decimal("10"), 15)),
    ],
)
def test_rules_config_from_valores_invalidos(config, expected):
    assert rules_config_from(config) == expected


def test_availability_of():
    assert availability_of(_obs(None, found=False, in_stock=False)) == "not_found"
    assert availability_of(_obs(in_stock=False)) == "unavailable"
    assert availability_of(_obs()) == "available"


@pytest.mark.parametrize("reason", ["price_increase", "no_longer_deal", "out_of_stock", "not_found"])
def test_nunca_reactiva_lo_que_terminaria_en_la_misma_revision(reason):
    """Sin esta guarda alternaría terminar/reactivar cada día (y avisaría al canal)."""
    state = _state("expired", offer="80", previous="100", reason=reason)
    assert decide(state, _obs("80", discount=0), CFG) == ("none", None)
    assert decide(state, _obs("80"), CFG) == ("reactivate", None)
    reactivated_state = _state("active", offer="80", previous="100")
    assert decide(reactivated_state, _obs("80"), CFG) == ("keep", None)


def test_no_reactiva_una_oferta_cuya_fecha_de_fin_ya_paso():
    """Revisión del 2026-11-06: se reactivaba (aviso incluido) y a los 5 min
    mark_expired_deals la volvía a caducar por fecha."""
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 11, 6, 4, 0, tzinfo=timezone.utc)
    past = OfferState("expired", "out_of_stock", Decimal("80"), None, expires_at=now - timedelta(hours=1))
    future = OfferState("expired", "out_of_stock", Decimal("80"), None, expires_at=now + timedelta(days=1))
    assert decide(past, _obs("80"), CFG, now=now) == ("none", None)
    assert decide(future, _obs("80"), CFG, now=now) == ("reactivate", None)


def test_activo_que_baja_de_precio_se_avisa():
    """Petición 2026-11-06: avisar también si una oferta activa baja de precio."""
    state = _state(offer="100")
    assert decide(state, _obs("95"), CFG) == ("drop", "price_drop")
    assert decide(state, _obs("95.01"), CFG) == ("keep", None)
    assert decide(state, _obs("80"), RulesConfig(price_drop_percent=25)) == ("keep", None)


def test_bajada_no_aplica_si_la_oferta_debe_terminar():
    assert decide(_state(offer="100"), _obs("90", in_stock=False), CFG) == ("end", "out_of_stock")


def test_rules_config_from_price_drop():
    assert rules_config_from({"price_drop_percent": 10}).price_drop_percent == 10
    assert rules_config_from({"price_drop_percent": 0}).price_drop_percent == 5
    assert rules_config_from({"price_drop_percent": "x"}).price_drop_percent == 5


def test_bajada_se_mide_contra_el_ultimo_aviso_sin_mover_el_precio_de_oferta():
    """Revisión 2026-11-06: si la bajada movía offer_price, 100 → 90 → 100
    terminaba la oferta por 'subida' y ya no se reactivaba a 100."""
    notified_at_90 = OfferState("active", None, Decimal("100"), None, notified_price=Decimal("90"))
    assert decide(notified_at_90, _obs("100"), CFG) == ("keep", None)
    assert decide(notified_at_90, _obs("88"), CFG) == ("keep", None)  # < 5 % bajo el último aviso
    assert decide(notified_at_90, _obs("85.50"), CFG) == ("drop", "price_drop")
