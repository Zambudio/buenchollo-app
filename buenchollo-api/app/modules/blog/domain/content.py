"""Validación y extracción sobre el documento Tiptap (JSON) de un BlogPost.

Lógica pura, sin dependencias de FastAPI/SQLAlchemy, para poder testarse
de forma aislada y reutilizarse tanto en el schema de creación/edición
como en el paso previo a publicar.

El documento es la fuente de verdad canónica del contenido (§4 del
encargo): nunca se acepta ni se persiste HTML arbitrario del cliente.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from app.modules.blog.domain.exceptions import InvalidContentError

# Nodos soportados. Los cuatro tipos de "bloque informativo" del encargo
# (info/consejo/advertencia/veredicto) se modelan como un único nodo
# `callout` con un atributo `variant`, en vez de 4 tipos de nodo distintos
# — mismo comportamiento, sin duplicar el validador (DRY).
ALLOWED_NODE_TYPES = {
    "doc", "paragraph", "text", "heading",
    "bulletList", "orderedList", "listItem", "taskList", "taskItem",
    "blockquote", "codeBlock", "horizontalRule",
    "table", "tableRow", "tableCell", "tableHeader",
    "image", "hardBreak",
    "callout", "productRecommendation",
}

ALLOWED_MARKS = {"bold", "italic", "underline", "strike", "code", "link", "highlight", "textStyle"}

ALLOWED_HEADING_LEVELS = {2, 3, 4}
ALLOWED_CALLOUT_VARIANTS = {"info", "tip", "warning", "verdict"}
ALLOWED_IMAGE_ALIGN = {"left", "center", "right"}
ALLOWED_IMAGE_WIDTH = {"normal", "full"}
ALLOWED_LINK_PROTOCOLS = {"http:", "https:"}
# Paleta controlada de color de texto (coherente con el tema de la web).
# Ampliar aquí, nunca aceptar un color arbitrario del cliente.
ALLOWED_TEXT_COLORS = {"#22d3ee", "#f87171", "#4ade80", "#facc15", "#a78bfa", "#f8fafc", "#94a3b8"}

MAX_DOCUMENT_CHARS = 300_000
MAX_DEPTH = 30
_READING_WPM = 200


def _protocol_of(url: str) -> str | None:
    if ":" not in url:
        return None
    return url.split(":", 1)[0].lower() + ":"


def _validate_link_href(href: str) -> None:
    if not isinstance(href, str) or not href:
        raise InvalidContentError("Enlace sin URL")
    if href.startswith("/"):
        return  # enlace interno relativo
    protocol = _protocol_of(href)
    if protocol not in ALLOWED_LINK_PROTOCOLS:
        raise InvalidContentError(f"Protocolo de enlace no permitido: {href!r}")


def _validate_image_attrs(attrs: dict) -> None:
    src = attrs.get("src")
    if not isinstance(src, str) or not src:
        raise InvalidContentError("Imagen sin src")
    protocol = _protocol_of(src)
    if not src.startswith("/") and protocol not in ALLOWED_LINK_PROTOCOLS:
        raise InvalidContentError(f"Protocolo de imagen no permitido: {src!r}")
    alt = attrs.get("alt")
    if not isinstance(alt, str) or not alt.strip():
        raise InvalidContentError("Toda imagen debe tener texto alternativo (alt)")
    align = attrs.get("align")
    if align is not None and align not in ALLOWED_IMAGE_ALIGN:
        raise InvalidContentError(f"Alineación de imagen no permitida: {align!r}")
    width = attrs.get("width")
    if width is not None and width not in ALLOWED_IMAGE_WIDTH:
        raise InvalidContentError(f"Ancho de imagen no permitido: {width!r}")


def _validate_heading_attrs(attrs: dict) -> None:
    level = attrs.get("level")
    if level not in ALLOWED_HEADING_LEVELS:
        raise InvalidContentError("Solo se permiten encabezados H2, H3 y H4 dentro del contenido")


def _validate_callout_attrs(attrs: dict) -> None:
    variant = attrs.get("variant")
    if variant not in ALLOWED_CALLOUT_VARIANTS:
        raise InvalidContentError(f"Variante de bloque informativo no permitida: {variant!r}")


def _validate_product_recommendation_attrs(attrs: dict, *, allowed_affiliate_domains: frozenset[str]) -> None:
    mode = attrs.get("mode")
    if mode not in {"deal", "manual"}:
        raise InvalidContentError("Bloque de producto: 'mode' debe ser 'deal' o 'manual'")

    if mode == "deal":
        deal_id = attrs.get("deal_id")
        if not isinstance(deal_id, str) or not deal_id:
            raise InvalidContentError("Bloque de producto (chollo existente) sin deal_id")
    else:
        name = attrs.get("name")
        affiliate_url = attrs.get("affiliate_url")
        if not isinstance(name, str) or not name.strip():
            raise InvalidContentError("Bloque de producto manual sin nombre")
        if not isinstance(affiliate_url, str) or not affiliate_url:
            raise InvalidContentError("Bloque de producto manual sin URL de afiliado")
        _validate_link_href(affiliate_url)
        from app.modules.blog.domain.affiliate_domains import extract_domain
        domain = extract_domain(affiliate_url)
        if domain not in allowed_affiliate_domains:
            raise InvalidContentError(f"Dominio de afiliado no permitido: {domain!r}")
        for forbidden in ("previous_price", "discount_percentage", "savings_amount", "current_price"):
            if attrs.get(forbidden) is not None:
                raise InvalidContentError("Los bloques de producto manuales no admiten campos de precio")

    note = attrs.get("note")
    if note is not None and (not isinstance(note, str) or len(note) > 600):
        raise InvalidContentError("Recomendación editorial de producto inválida")
    button_text = attrs.get("button_text")
    if button_text is not None and (not isinstance(button_text, str) or len(button_text) > 60):
        raise InvalidContentError("Texto de botón de producto inválido")


def _validate_marks(marks: list) -> None:
    if not isinstance(marks, list):
        raise InvalidContentError("'marks' debe ser una lista")
    for mark in marks:
        if not isinstance(mark, dict):
            raise InvalidContentError("Marca inválida")
        mark_type = mark.get("type")
        if mark_type not in ALLOWED_MARKS:
            raise InvalidContentError(f"Marca no permitida: {mark_type!r}")
        attrs = mark.get("attrs") or {}
        if mark_type == "link":
            href = attrs.get("href")
            _validate_link_href(href)
            rel = attrs.get("rel")
            if rel is not None and not isinstance(rel, str):
                raise InvalidContentError("Atributo 'rel' de enlace inválido")
        if mark_type == "textStyle":
            color = attrs.get("color")
            if color is not None and color not in ALLOWED_TEXT_COLORS:
                raise InvalidContentError(f"Color de texto no permitido: {color!r}")


def _validate_node(node: dict, *, depth: int, allowed_affiliate_domains: frozenset[str]) -> None:
    if depth > MAX_DEPTH:
        raise InvalidContentError("El documento supera la profundidad máxima permitida")
    if not isinstance(node, dict):
        raise InvalidContentError("Nodo inválido")

    node_type = node.get("type")
    if node_type not in ALLOWED_NODE_TYPES:
        raise InvalidContentError(f"Tipo de nodo no permitido: {node_type!r}")

    attrs = node.get("attrs") or {}
    if not isinstance(attrs, dict):
        raise InvalidContentError("'attrs' debe ser un objeto")

    if node_type == "heading":
        _validate_heading_attrs(attrs)
    elif node_type == "image":
        _validate_image_attrs(attrs)
    elif node_type == "callout":
        _validate_callout_attrs(attrs)
    elif node_type == "productRecommendation":
        _validate_product_recommendation_attrs(attrs, allowed_affiliate_domains=allowed_affiliate_domains)

    marks = node.get("marks")
    if marks is not None:
        _validate_marks(marks)

    if node_type == "text" and not isinstance(node.get("text"), str):
        raise InvalidContentError("Nodo de texto sin contenido")

    for child in node.get("content") or []:
        _validate_node(child, depth=depth + 1, allowed_affiliate_domains=allowed_affiliate_domains)


def validate_document(doc: dict, *, allowed_affiliate_domains: frozenset[str]) -> None:
    """Valida recursivamente un documento Tiptap. Lanza InvalidContentError si no es válido."""
    if not isinstance(doc, dict):
        raise InvalidContentError("El contenido debe ser un objeto JSON")
    if doc.get("type") != "doc":
        raise InvalidContentError("El nodo raíz debe ser 'doc'")

    serialized_size = len(json.dumps(doc))
    if serialized_size > MAX_DOCUMENT_CHARS:
        raise InvalidContentError("El contenido del artículo supera el tamaño máximo permitido")

    for child in doc.get("content") or []:
        _validate_node(child, depth=1, allowed_affiliate_domains=allowed_affiliate_domains)


# ── Extracción (lógica pura, usada tanto en publish como en listados) ───────

def _walk(node: dict):
    yield node
    for child in node.get("content") or []:
        yield from _walk(child)


def extract_plain_text(doc: dict) -> str:
    parts: list[str] = []
    for node in _walk(doc):
        if node.get("type") == "text" and isinstance(node.get("text"), str):
            parts.append(node["text"])
    return " ".join(parts)


def count_words(text: str) -> int:
    return len([w for w in text.split() if w])


def reading_time_minutes(word_count: int) -> int:
    return max(1, round(word_count / _READING_WPM)) if word_count else 0


@dataclass(frozen=True)
class HeadingEntry:
    level: int
    text: str
    id: str


def _heading_text(node: dict) -> str:
    return "".join(
        child.get("text", "") for child in node.get("content") or [] if child.get("type") == "text"
    )


def extract_toc(doc: dict) -> list[HeadingEntry]:
    """Tabla de contenidos a partir de los encabezados H2/H3 del documento."""
    entries: list[HeadingEntry] = []
    used_ids: set[str] = set()
    for node in _walk(doc):
        if node.get("type") != "heading":
            continue
        level = (node.get("attrs") or {}).get("level")
        if level not in (2, 3):
            continue
        text = _heading_text(node).strip()
        if not text:
            continue
        from app.modules.blog.domain.utils import slugify
        base_id = slugify(text) or "seccion"
        heading_id = base_id
        counter = 2
        while heading_id in used_ids:
            heading_id = f"{base_id}-{counter}"
            counter += 1
        used_ids.add(heading_id)
        entries.append(HeadingEntry(level=level, text=text, id=heading_id))
    return entries


def has_affiliate_blocks(doc: dict) -> bool:
    return any(node.get("type") == "productRecommendation" for node in _walk(doc))


def extract_referenced_deal_ids(doc: dict) -> list[str]:
    """IDs únicos (orden de aparición) de los bloques de producto en modo 'deal'."""
    seen: set[str] = set()
    ordered: list[str] = []
    for node in _walk(doc):
        if node.get("type") != "productRecommendation":
            continue
        attrs = node.get("attrs") or {}
        if attrs.get("mode") != "deal":
            continue
        deal_id = attrs.get("deal_id")
        if deal_id and deal_id not in seen:
            seen.add(deal_id)
            ordered.append(deal_id)
    return ordered


def is_content_empty(doc: dict) -> bool:
    return len(extract_plain_text(doc).strip()) == 0
