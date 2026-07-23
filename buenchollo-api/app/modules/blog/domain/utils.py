import re

_MAX_TAGS = 10
_MAX_TAG_LENGTH = 40


def slugify(title: str) -> str:
    """Genera un slug URL-safe a partir del título. Sin sufijo temporal:
    a diferencia de `deals.domain.utils.auto_slug`, el slug de un artículo
    debe ser estable y legible; la unicidad la valida el repositorio."""
    slug = title.lower().strip()
    for src, dst in [("áàäâ", "a"), ("éèëê", "e"), ("íìïî", "i"), ("óòöô", "o"), ("úùüû", "u"), ("ñ", "n")]:
        for ch in src:
            slug = slug.replace(ch, dst)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug


def normalize_tags(tags: list[str] | None) -> list[str]:
    """Limpia, deduplica (case-insensitive) y limita una lista de tags."""
    if not tags:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in tags:
        tag = raw.strip()
        if not tag:
            continue
        tag = tag[:_MAX_TAG_LENGTH]
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(tag)
        if len(normalized) >= _MAX_TAGS:
            break
    return normalized
