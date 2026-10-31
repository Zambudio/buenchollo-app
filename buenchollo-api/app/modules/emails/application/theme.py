"""Paleta y tipografías de los correos BuenChollo Tech.

Diseño limpio, elegante y armónico: fondo claro, tarjeta blanca,
cabecera limpia sin bloques negros estridentes, tipografía refinada
y acentos equilibrados.
"""

THEME: dict[str, str] = {
    # Lienzo exterior limpio (gris perla suave)
    "canvas": "#f8fafc",
    "bg": "#f8fafc",

    # Tarjetas y contenedores
    "card": "#ffffff",
    "card_subtle": "#f8fafc",
    "card_pastel": "#f0f7ff",  # Acento pastel sutil

    # Bordes limpios y discretos
    "border": "#e2e8f0",
    "border_subtle": "#f1f5f9",
    "border_strong": "#cbd5e1",

    # Cabecera y barra inferior limpias (sin fondo negro)
    "header_bg": "#ffffff",
    "header_line": "#2563eb",  # Línea de acento azul elegante
    "footer_banner": "#f8fafc",
    "footer_border": "#e2e8f0",

    # Colores de acción armónicos (adiós verdes estridentes)
    "cta": "#2563eb",  # Azul royal elegante y profesional
    "cta_hover": "#1d4ed8",
    "cta_text": "#ffffff",
    "cta_secondary_bg": "#ffffff",
    "cta_secondary_border": "#cbd5e1",
    "cta_secondary_text": "#334155",

    # Acentos
    "cyan": "#0284c7",  # Azul cyan sofisticado
    "cyan_dark": "#0369a1",
    "cyan_border": "#bae6fd",
    "cyan_soft": "#f0f9ff",
    "telegram": "#229ed9",  # Azul oficial de Telegram

    # Tipografía cuidada
    "text": "#0f172a",  # Pizarra oscuro de alta legibilidad
    "text_soft": "#334155",  # Gris grafito para párrafos
    "muted": "#64748b",  # Gris medio para subtítulos y notas
    "faint": "#94a3b8",  # Gris claro para avisos legales
    "sans": "'Space Grotesk','Segoe UI',Roboto,Helvetica,Arial,sans-serif",
    "mono": "'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace",
}
