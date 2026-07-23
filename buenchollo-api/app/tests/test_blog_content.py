import pytest

from app.modules.blog.domain.content import (
    count_words,
    extract_plain_text,
    extract_referenced_deal_ids,
    extract_toc,
    has_affiliate_blocks,
    is_content_empty,
    reading_time_minutes,
    validate_document,
)
from app.modules.blog.domain.exceptions import InvalidContentError

ALLOWED_DOMAINS = frozenset({"amazon.es"})


def _doc(*content):
    return {"type": "doc", "content": list(content)}


def _paragraph(text: str):
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def _heading(level: int, text: str):
    return {"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": text}]}


def test_documento_valido_no_lanza():
    doc = _doc(_heading(2, "Introducción"), _paragraph("Hola mundo"))
    validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_nodo_raiz_debe_ser_doc():
    with pytest.raises(InvalidContentError):
        validate_document({"type": "paragraph"}, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_rechaza_h1_dentro_del_contenido():
    with pytest.raises(InvalidContentError):
        validate_document(_doc(_heading(1, "Título")), allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_rechaza_tipo_de_nodo_no_soportado():
    with pytest.raises(InvalidContentError):
        validate_document(_doc({"type": "iframe"}), allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_rechaza_marca_no_soportada():
    doc = _doc({"type": "paragraph", "content": [{"type": "text", "text": "x", "marks": [{"type": "superscript"}]}]})
    with pytest.raises(InvalidContentError):
        validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


@pytest.mark.parametrize("href", ["javascript:alert(1)", "data:text/html;base64,x", "ftp://x.com"])
def test_rechaza_protocolos_inseguros_en_enlaces(href):
    doc = _doc({
        "type": "paragraph",
        "content": [{"type": "text", "text": "click", "marks": [{"type": "link", "attrs": {"href": href}}]}],
    })
    with pytest.raises(InvalidContentError):
        validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_acepta_enlace_interno_relativo():
    doc = _doc({
        "type": "paragraph",
        "content": [{"type": "text", "text": "click", "marks": [{"type": "link", "attrs": {"href": "/chollos/x"}}]}],
    })
    validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_imagen_sin_alt_es_invalida():
    doc = _doc({"type": "image", "attrs": {"src": "https://cdn.example.com/a.png"}})
    with pytest.raises(InvalidContentError):
        validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_color_de_texto_fuera_de_paleta_es_invalido():
    doc = _doc({
        "type": "paragraph",
        "content": [{"type": "text", "text": "x", "marks": [{"type": "textStyle", "attrs": {"color": "#123456"}}]}],
    })
    with pytest.raises(InvalidContentError):
        validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_producto_modo_deal_requiere_deal_id():
    doc = _doc({"type": "productRecommendation", "attrs": {"mode": "deal"}})
    with pytest.raises(InvalidContentError):
        validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_producto_manual_valido():
    doc = _doc({
        "type": "productRecommendation",
        "attrs": {
            "mode": "manual", "name": "Cargador USB-C", "affiliate_url": "https://amazon.es/dp/X",
            "button_text": "Ver oferta",
        },
    })
    validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_producto_manual_dominio_no_permitido():
    doc = _doc({
        "type": "productRecommendation",
        "attrs": {"mode": "manual", "name": "X", "affiliate_url": "https://sospechoso.example/x"},
    })
    with pytest.raises(InvalidContentError):
        validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_producto_manual_rechaza_campos_de_precio():
    doc = _doc({
        "type": "productRecommendation",
        "attrs": {
            "mode": "manual", "name": "X", "affiliate_url": "https://amazon.es/dp/X",
            "previous_price": 10,
        },
    })
    with pytest.raises(InvalidContentError):
        validate_document(doc, allowed_affiliate_domains=ALLOWED_DOMAINS)


def test_extract_plain_text_y_conteo_de_palabras():
    doc = _doc(_paragraph("Hola mundo cruel"))
    text = extract_plain_text(doc)
    assert text.strip() == "Hola mundo cruel"
    assert count_words(text) == 3


def test_reading_time_minimo_un_minuto_si_hay_texto():
    assert reading_time_minutes(10) == 1
    assert reading_time_minutes(0) == 0
    assert reading_time_minutes(400) == 2


def test_extract_toc_solo_h2_h3():
    doc = _doc(_heading(2, "Sección A"), _heading(3, "Sub A"), _heading(4, "Detalle ignorado"))
    toc = extract_toc(doc)
    assert [(h.level, h.text) for h in toc] == [(2, "Sección A"), (3, "Sub A")]
    assert toc[0].id == "seccion-a"


def test_extract_toc_desambigua_ids_repetidos():
    doc = _doc(_heading(2, "Repetido"), _heading(2, "Repetido"))
    toc = extract_toc(doc)
    assert toc[0].id == "repetido"
    assert toc[1].id == "repetido-2"


def test_has_affiliate_blocks():
    assert has_affiliate_blocks(_doc(_paragraph("sin bloques"))) is False
    doc = _doc({"type": "productRecommendation", "attrs": {"mode": "deal", "deal_id": "x"}})
    assert has_affiliate_blocks(doc) is True


def test_extract_referenced_deal_ids_unico_y_en_orden():
    doc = _doc(
        {"type": "productRecommendation", "attrs": {"mode": "deal", "deal_id": "a"}},
        {"type": "productRecommendation", "attrs": {"mode": "manual", "name": "x"}},
        {"type": "productRecommendation", "attrs": {"mode": "deal", "deal_id": "b"}},
        {"type": "productRecommendation", "attrs": {"mode": "deal", "deal_id": "a"}},
    )
    assert extract_referenced_deal_ids(doc) == ["a", "b"]


def test_is_content_empty():
    assert is_content_empty(_doc()) is True
    assert is_content_empty(_doc(_paragraph("   "))) is True
    assert is_content_empty(_doc(_paragraph("hola"))) is False
