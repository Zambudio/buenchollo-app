"""Tests unitarios de la función pura `matches_alert`.

Función pura, sin BD ni I/O. Se prueban las distintas reglas (keyword, categoría,
tienda, marca, precio máximo, descuento mínimo) con SimpleNamespace para no
arrastrar el mapper SQLAlchemy.
"""
from types import SimpleNamespace
import pytest

from app.modules.alerts.application.matching import matches_alert


def _deal(**overrides):
    base = dict(
        title="Portátil HP",
        description="Buen procesador y SSD",
        brand="HP",
        category_id="cat-1",
        subcategory_id=None,
        store_id="store-1",
        current_price=500.0,
        discount_percentage=20,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _alert(**overrides):
    base = dict(
        keyword=None,
        category_id=None,
        store_id=None,
        brand=None,
        max_price=None,
        min_discount=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_sin_criterios_la_alerta_coincide_siempre():
    assert matches_alert(_alert(), _deal()) is True


def test_keyword_busca_en_titulo_descripcion_y_marca():
    assert matches_alert(_alert(keyword="portátil"), _deal()) is True
    assert matches_alert(_alert(keyword="SSD"), _deal()) is True
    assert matches_alert(_alert(keyword="HP"), _deal()) is True
    assert matches_alert(_alert(keyword="raspberry"), _deal()) is False


def test_categoria_acepta_la_subcategoria_del_deal():
    deal = _deal(category_id="cat-A", subcategory_id="cat-B")
    assert matches_alert(_alert(category_id="cat-A"), deal) is True
    assert matches_alert(_alert(category_id="cat-B"), deal) is True
    assert matches_alert(_alert(category_id="cat-C"), deal) is False


def test_tienda_filtra_por_store_id_exacto():
    assert matches_alert(_alert(store_id="store-1"), _deal()) is True
    assert matches_alert(_alert(store_id="store-2"), _deal()) is False


def test_marca_se_compara_case_insensitive_y_substring():
    assert matches_alert(_alert(brand="hp"), _deal(brand="HP Pavilion")) is True
    assert matches_alert(_alert(brand="dell"), _deal(brand="HP Pavilion")) is False


def test_max_price_descarta_los_mas_caros():
    assert matches_alert(_alert(max_price=600), _deal(current_price=500)) is True
    assert matches_alert(_alert(max_price=400), _deal(current_price=500)) is False


def test_min_discount_descarta_los_menos_rebajados():
    assert matches_alert(_alert(min_discount=10), _deal(discount_percentage=20)) is True
    assert matches_alert(_alert(min_discount=25), _deal(discount_percentage=20)) is False
    assert matches_alert(_alert(min_discount=10), _deal(discount_percentage=None)) is False


def test_combinacion_de_criterios_exige_todos():
    alert = _alert(keyword="portátil", store_id="store-1", max_price=600)
    assert matches_alert(alert, _deal()) is True
    assert matches_alert(alert, _deal(current_price=700)) is False
    assert matches_alert(alert, _deal(store_id="store-2")) is False
