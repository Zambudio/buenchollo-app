"""Normalización de títulos de chollos (reglas puras, sin BD).

Se aplica al publicar o editar un chollo y, una vez, a los ya publicados
(`scripts/normalize_titles.py`). Es deliberadamente conservadora: los nombres
de modelo («LG S95AR», «MSI MPG A850GS PCIE5», «ASUS TUF B850M-PLUS») no se
tocan; solo se corrigen caracteres raros, espacios y los títulos que «gritan»
enteros en mayúsculas («AURICULARES INFANTILES INALÁMBRICOS…»).
"""

import re
import unicodedata

# Caracteres que llegan de Amazon y se ven mal o raros en la web y en Telegram.
_REPLACEMENTS = {
    "，": ",",  # coma de ancho completo «，»
    "、": ",",
    "（": "(",
    "）": ")",
    "：": ":",
    "‐": "-",  # guiones tipográficos
    "‑": "-",
    "‒": "-",
    "–": "-",
    "—": "-",
    "“": '"',  # comillas tipográficas
    "”": '"',
    "„": '"',
    "″": '"',
    "‘": "'",
    "’": "'",
    "´": "'",
    "™": "",  # ™
    "®": "",  # ®
    "©": "",  # ©
}

# Siglas y marcas que se escriben en mayúsculas y no hay que «bajar».
_KEEP_UPPER = frozenset(
    """
    AI AKG AMD ANC AOC ASUS ATX BT CPU DDR DJI DLSS DP DVD EU FHD GB GPS GPU HD HDD HDMI HDR HP HQ IA II III
    IPS IV JBL KB LCD LED LG MB MSI NAS NFC NVME NZXT OLED PC PCIE PD PS QHD QLED QNED RAM RGB ROG
    SATA SD SSD TB TCL TKL TUF TV TWS UHD UK USA USB VA VR WQHD XL XXL
    """.split()
)

# Marcas y términos con grafía propia (se escriben así aunque llegaran en mayúsculas).
_BRAND_CASE = {
    "AIRPODS": "AirPods",
    "IMAC": "iMac",
    "IPAD": "iPad",
    "IPHONE": "iPhone",
    "MACBOOK": "MacBook",
    "PLAYSTATION": "PlayStation",
    "TIKTOK": "TikTok",
    "WIFI": "WiFi",
    "XBOX": "Xbox",
    "YOUTUBE": "YouTube",
}

# Palabras cortas que van en minúscula en un título (salvo al principio).
_SMALL_WORDS = frozenset("a al con de del e el en la las los o para por sin u y".split())

# Palabras «gritadas»: solo letras (y guiones), todas en mayúscula, 4+ letras.
_SHOUTED = re.compile(r"^[^\W\d_]{4,}(?:-[^\W\d_]+)*$")
_WORD = re.compile(r"^[^\W\d_]{3,}$")

MIN_SHOUTED_WORDS = 3
SHOUTED_SHARE = 0.6


def _clean_characters(title: str) -> str:
    text = unicodedata.normalize("NFC", title)
    text = "".join(_REPLACEMENTS.get(c, c) for c in text)
    # Controles y caracteres invisibles (p. ej. U+200B) fuera.
    text = "".join(c for c in text if unicodedata.category(c) not in ("Cc", "Cf"))
    text = re.sub(r"\s+", " ", text).strip()
    # Espacio tras una coma pegada («Hi-Res,Negro», «6.0,Blanco», «Portátil,30 L»),
    # sin tocar los decimales («4,7GHz»: dígito, coma, dígito).
    text = re.sub(r",(?=[^\s\d])", ", ", text)
    text = re.sub(r"(?<=[^\W\d_)]),(?=\d)", ", ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text


def _is_shouted(word: str) -> bool:
    letters = word.replace("-", "")
    return (
        bool(_SHOUTED.match(word))
        and letters.isupper()
        and not any(part in _KEEP_UPPER for part in word.split("-"))
    )


def _soften_part(part: str) -> str:
    if part in _KEEP_UPPER or len(part) < 2:
        return part
    return _BRAND_CASE.get(part, part[:1].upper() + part[1:].lower())


def is_shouting(title: str) -> bool:
    """True si el título está «gritado»: al menos 3 palabras largas en
    mayúsculas que no son siglas ni marcas, y más del 60 % de sus palabras."""
    words = [w.strip("()[]\"'.,:;") for w in title.split()]
    candidates = [w for w in words if _WORD.match(w.replace("-", "")) or _SHOUTED.match(w)]
    shouted = [w for w in candidates if _is_shouted(w)]
    return len(shouted) >= MIN_SHOUTED_WORDS and len(shouted) / max(1, len(candidates)) > SHOUTED_SHARE


def _soften(word: str, first: bool) -> str:
    """Solo se llama con el título entero «gritado»: baja las palabras en
    mayúsculas (también las cortas: «DE», «Y», «SET») salvo siglas, marcas,
    letras sueltas y todo lo que lleve dígitos."""
    core = word.strip("()[]\"'.,:;")
    letters = core.replace("-", "")
    if not letters.isalpha() or not letters.isupper():
        return word
    lower = core.lower()
    if not first and lower in _SMALL_WORDS:  # «DE», «Y», «LA» (también de una letra)
        return word.replace(core, lower, 1)
    fixed = "-".join(_soften_part(part) for part in core.split("-"))
    return word.replace(core, fixed, 1)


def normalize_title(title: str) -> str:
    """Título limpio: caracteres raros fuera, espacios normalizados y, si el
    título entero está en mayúsculas, palabras en formato normal (respetando
    siglas, marcas y modelos con dígitos)."""
    if not title:
        return title
    text = _clean_characters(title)
    if is_shouting(text):
        words = text.split(" ")
        text = " ".join(_soften(w, i == 0) for i, w in enumerate(words))
    return text


def needs_manual_review(title: str) -> bool:
    """Títulos que no se pueden arreglar solos (p. ej. solo la marca:
    «Cellularline», «Hama»): se listan para revisarlos a mano."""
    return len(title.split()) <= 1
