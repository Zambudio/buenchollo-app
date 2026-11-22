"""Términos técnicos partidos en el feed de Awin (Coolmod).

El feed real trae «PC Ie», «NV Me», «AS Rock», «5600M Hz»… (comprobado en el
CSV descargado, no lo provoca nuestro parser). Solo se corrigen casos
inequívocos; el resto del texto queda tal cual.
"""

import pytest

from app.modules.affiliates.domain.offers import fix_split_terms
from app.modules.affiliates.infrastructure.awin_client import map_feed_row


@pytest.mark.parametrize(
    ("raw", "fixed"),
    [
        ("Seagate Game Drive PS5 1TB PC Ie Gen4 x4 NV Me SSD", "Seagate Game Drive PS5 1TB PCIe Gen4 x4 NVMe SSD"),
        ("Kingston 32GB 5600M Hz CL46", "Kingston 32GB 5600MHz CL46"),
        ("Intel Core 3.2G Hz", "Intel Core 3.2GHz"),
        ("AS Rock B850 Steel Legend", "ASRock B850 Steel Legend"),
        ("G.S Kill Trident Z5", "G.Skill Trident Z5"),
        ("ALLM, VRR y H GiG para jugar", "ALLM, VRR y HGiG para jugar"),
        ("Tarjeta Wi Fi 7", "Tarjeta WiFi 7"),
        ("Powerbank 20000M Ah", "Powerbank 20000mAh"),
    ],
)
def test_fixes_known_split_terms(raw: str, fixed: str) -> None:
    assert fix_split_terms(raw) == fixed


@pytest.mark.parametrize(
    "text",
    [
        "AMD Ryzen 7 9800X3D",
        "ROG Strix ARGB Negro",
        "Monitor LG Gram 144 Hz",  # «144 Hz» con espacio es correcto
        "PC Intel Core i5",  # «PC» seguido de otra palabra no se toca
        "Disco NVMe PCIe 4.0",
    ],
)
def test_leaves_correct_text_untouched(text: str) -> None:
    assert fix_split_terms(text) == text


def test_none_and_empty() -> None:
    assert fix_split_terms(None) is None
    assert fix_split_terms("") == ""


def test_feed_row_title_and_description_are_fixed() -> None:
    row = {
        "aw_product_id": "1",
        "product_name": "approx APPPCIE1000 PC Ie",
        "description": "Tarjeta de red Gigabit PC Ie con NV Me",
        "merchant_deep_link": "https://www.coolmod.com/approx-apppcie1000-pcie-tarjeta-red/",
    }
    mapped = map_feed_row(row)
    assert mapped["title"] == "approx APPPCIE1000 PCIe"
    assert mapped["description"] == "Tarjeta de red Gigabit PCIe con NVMe"
