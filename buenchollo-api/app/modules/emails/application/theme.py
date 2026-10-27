"""Paleta y tipografías de los correos.

Equivalentes en hex del tema oscuro de la web (`buenchollo-web/src/styles.css`,
definido en oklch): los clientes de correo no entienden oklch ni variables CSS,
y Outlook tampoco rgba, así que los tonos translúcidos van ya mezclados sobre
el fondo de tarjeta.
"""

THEME: dict[str, str] = {
    "bg": "#010717",  # --surface-900
    "card": "#051127",  # --surface-800
    "terminal": "#030c1f",
    "border": "#122239",  # --surface-700
    "border_strong": "#2d3b4f",  # --surface-600
    "cyan": "#00ebff",  # --cyan-glow
    "cyan_border": "#035d73",  # cian al 35% sobre la tarjeta
    "cyan_soft": "#05273d",  # cian al 10% sobre la tarjeta
    "cta": "#16c784",  # .btn-cta
    "cta_text": "#06231a",
    "green": "#40cc6d",  # --success
    "red": "#ff2b5e",  # --alert-red
    "amber": "#f5a623",  # --color-countdown
    "amber_soft": "#1d2027",
    "text": "#eceff1",  # --foreground
    "text_soft": "#c3cad3",
    "muted": "#86909b",  # --muted-foreground
    "faint": "#5b6676",
    "sans": "'Space Grotesk','Segoe UI',Roboto,Helvetica,Arial,sans-serif",
    "mono": "'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace",
}
