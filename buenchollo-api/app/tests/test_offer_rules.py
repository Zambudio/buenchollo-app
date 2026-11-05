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
    [("110.01", ("end", "price_increase")), ("110", ("keep", None)), ("90", ("keep", None))],
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


def test_expired_descuento_tienda_5_se_reactiva():
    state = _state("expired", offer="80", reason="price_increase")
    assert decide(state, _obs("90", discount=5), CFG) == ("reactivate", None)
    assert decide(state, _obs("90", discount=4), CFG) == ("none", None)
    assert decide(state, _obs("90"), CFG) == ("none", None)


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
