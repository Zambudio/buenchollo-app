"""Normalización de títulos con ejemplos reales del catálogo."""

import pytest

from app.modules.deals.domain.titles import is_shouting, needs_manual_review, normalize_title


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "AURICULARES INFANTILES INALÁMBRICOS SUPER MARIO BLUETOOTH PLEGABLES",
            "Auriculares Infantiles Inalámbricos Super Mario Bluetooth Plegables",
        ),
        (
            "AURICULARES INFANTILES INALÁMBRICOS SUPER MARIO LOGO BLUETOOTH PLEGABLES",
            "Auriculares Infantiles Inalámbricos Super Mario Logo Bluetooth Plegables",
        ),
        (
            "Edifier R20BT Altavoces PC USB con Bluetooth 6.0，Blanco",
            "Edifier R20BT Altavoces PC USB con Bluetooth 6.0, Blanco",
        ),
        (
            "Edifier M60 Altavoces Multimedia Bluetooth con 66W RMS & Audio Hi-Res，Negro",
            "Edifier M60 Altavoces Multimedia Bluetooth con 66W RMS & Audio Hi-Res, Negro",
        ),
        (
            "Corsair XENEON Edge 14.5\" Pantalla táctil LCD 2K HDMI USB‑C",
            "Corsair XENEON Edge 14.5\" Pantalla táctil LCD 2K HDMI USB-C",
        ),
        ("BenQ MA320U 32” Monitor 4K 3840x2160", "BenQ MA320U 32\" Monitor 4K 3840x2160"),
        (
            "Lekespring 17.3“ Mochila Ordenador Portatil,30 L Mochila Ejecutivo Hombre",
            "Lekespring 17.3\" Mochila Ordenador Portatil, 30 L Mochila Ejecutivo Hombre",
        ),
        (
            "Estación de Carga PowerA para PlayStation Portal™ Remote Player con Lumectra™",
            "Estación de Carga PowerA para PlayStation Portal Remote Player con Lumectra",
        ),
        ("Playstation Mando inalámbrico DualSense®: Colección Hyperpop", "Playstation Mando inalámbrico DualSense: Colección Hyperpop"),
        ("  Monitor   gaming  27\"  ", "Monitor gaming 27\""),
        ("CABLE DE CARGA PARA EL MÓVIL Y LA TABLETA", "Cable de Carga para el Móvil y la Tableta"),
        (
            "AURICULARES BLUETOOTH USB-C CON IA PARA NIÑOS",
            "Auriculares Bluetooth USB-C con IA para Niños",
        ),
        ("FUNDA PARA IPHONE 15 PRO MAX COLOR NEGRO", "Funda para iPhone 15 Pro Max Color Negro"),
        ("REPETIDOR WIFI PARA CASA CON ENCHUFE", "Repetidor WiFi para Casa con Enchufe"),
    ],
)
def test_normaliza_titulos_reales(raw, expected):
    assert normalize_title(raw) == expected


@pytest.mark.parametrize(
    "title",
    [
        "LG S95AR",
        "MSI MPG A850GS PCIE5",
        "ASUS V16 V3607VH-TK214",
        "ASUS TUF GAMING B850M-PLUS II AMD B850 Socket AM5 micro ATX (ASUS AM5 TUF GAMING B850M-PLUS II M-ATX)",
        "AOOSTAR MACO Mini PC AMD R7 Pro 6850H (8C/16T hasta 4,7GHz) 24GB LPDDR5 RAM + 1TB PCIe4.0 SSD",
        "GIGABYTE B550M X AORUS ELITE WIFI7 Placa Base",
        "MAG CORELIQUID E240",
        "ICE-WATCH",
        "LG 65QNED82B6B",
        "ASUS USB-BT540",
    ],
)
def test_no_toca_modelos_ni_marcas(title):
    assert normalize_title(title) == title
    assert not is_shouting(title)


def test_respeta_los_decimales_con_coma():
    assert normalize_title("Mini PC hasta 4,7GHz") == "Mini PC hasta 4,7GHz"


def test_titulo_vacio():
    assert normalize_title("") == ""


@pytest.mark.parametrize(("title", "manual"), [("Cellularline", True), ("Hama", True), ("Beats Pill", False)])
def test_titulos_de_una_palabra_van_a_revision_manual(title, manual):
    assert needs_manual_review(title) is manual
