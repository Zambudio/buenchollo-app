import re
import time


def auto_slug(title: str) -> str:
    """Genera un slug URL-safe desde el título. Sin dependencias externas."""
    slug = title.lower().strip()
    for src, dst in [("áàäâ", "a"), ("éèëê", "e"), ("íìïî", "i"), ("óòöô", "o"), ("úùüû", "u"), ("ñ", "n")]:
        for ch in src:
            slug = slug.replace(ch, dst)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return f"{slug}-{int(time.time() * 1000):x}"
