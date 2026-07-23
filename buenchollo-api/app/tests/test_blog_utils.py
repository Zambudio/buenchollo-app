from app.modules.blog.domain.utils import normalize_tags, slugify


def test_slugify_normaliza_acentos_y_espacios():
    assert slugify("Los 10 Mejores Cascos Bluetooth de 2026") == "los-10-mejores-cascos-bluetooth-de-2026"
    assert slugify("Ñoño & Cía: análisis") == "nono-cia-analisis"


def test_slugify_es_estable_sin_sufijo_temporal():
    assert slugify("Guía de compra") == slugify("Guía de compra")


def test_normalize_tags_deduplica_case_insensitive_y_limpia_vacios():
    assert normalize_tags(["Ofertas", "ofertas", "  ", "Amazon"]) == ["Ofertas", "Amazon"]


def test_normalize_tags_limita_a_diez():
    tags = [f"tag{i}" for i in range(20)]
    assert len(normalize_tags(tags)) == 10


def test_normalize_tags_vacio():
    assert normalize_tags(None) == []
    assert normalize_tags([]) == []
