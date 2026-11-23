# Tarjeta de oferta de Telegram («Simple claro»)

Imagen de 1200 × 800 que sustituye a la foto del producto en cada publicación de chollo:
foto, insignia de descuento, logo de la tienda, precio actual, precio anterior tachado,
«Ahorras X €» y el logo del canal. El título y la descripción siguen en el texto del post.
Decisión y alternativas: [ADR-021](../adr/ADR-021-tarjeta-oferta-telegram.md).

## Dónde está

| Pieza | Fichero |
|---|---|
| Composición (Pillow, función pura) | `buenchollo-api/app/modules/telegram/application/deal_card.py` |
| Decisión de la imagen de cada envío (tarjeta o foto original) | `buenchollo-api/app/modules/telegram/application/deal_photo.py` |
| Logo del canal (provisional) | `buenchollo-api/app/assets/images/logo-bctech.png` |
| Logos de tiendas | `buenchollo-api/app/assets/images/stores/<clave>.png` |
| Tipografía | `buenchollo-api/app/assets/fonts/SpaceGrotesk-latin.woff2` |
| Especificación y referencia visual | `_handoff/plantilla-telegram-oferta/` (raíz de WEB-Buenchollo) |
| Tests | `app/tests/test_deal_card.py`, `test_deal_photo.py` |

## Qué envíos la llevan

Todos los de un chollo con foto: panel (`/telegram/notify`), publicaciones programadas,
republicación al canal Admin tras una bajada de precio y la copia de WhatsApp. El resumen
semanal tiene su propio collage (`weekly_collage.py`).

## Cuándo sale la foto original

Sin precio anterior, con anterior ≤ actual, si la foto no se descarga o no se lee, si falla
la composición, si Telegram rechaza la tarjeta o con `DEAL_CARD_ENABLED=false`. Nunca
bloquea una publicación. Los fallos se registran como `warning` en los logs de la API.

## Datos

- **Panel**: la web envía `current_price`, `previous_price`, `discount_percentage` y
  `store_name` (lo que muestra el post). Si el panel no los manda (versión antigua), se
  toman del chollo guardado (`deal_id`). Un «antes» vacío en el panel nunca se completa con
  el del chollo: la imagen enseñaría una rebaja que el post no tiene.
- **Programadas**: precio verificado de la programación (`offer_price`, `regular_price`,
  `discount_percentage`) y tienda del chollo.
- **Republicación**: precios y tienda del chollo tras la revisión diaria.
- Formato español (`99`, `264,99`, `1.299`); el porcentaje y el ahorro se calculan si no
  vienen. La parte entera del precio cambia de tamaño según sus cifras (1 → 210 px,
  2 → 180, 3 → 140, 4 o más → 104) y nunca se sale de la columna.

## Ajustes sobre la especificación (pedidos por Pedro, 2026-11-23)

- Logo del canal a 340 px de ancho (260 en la especificación).
- «Ahorras X €» a 40 px con relleno 18/28 (34 y 16/24); se reduce si un importe largo no cabe.
- Logo de la tienda en la pastilla en lugar del punto y el nombre (si hay logo).
- Logo de la tienda hasta 260 × 56 px (la pastilla crece si hace falta).
- Precio anterior: números `#334155` y raya roja fina semitransparente (`#dc2626` al 75 %, 3 px) en lugar de la raya gris de 4 px, que tapaba los números.

## ⚠️ Al añadir una tienda nueva

Cuando se active una tienda (Awin, Tradedoubler o cualquier otra), revisa sus publicaciones:

1. **Logo**: guarda `app/assets/images/stores/<clave>.png`, PNG con fondo transparente y al
   menos 400 px de ancho. La clave es el nombre de la tienda en `stores.name`, en
   minúsculas, sin espacios, signos ni acentos (`deal_card.store_key`): «El Corte Inglés» →
   `elcorteingles.png`. Sin logo sale el punto de color y el nombre: funciona, pero se ve peor.
2. **Color**: si no tiene logo, añade su color a `STORE_COLORS` en `deal_card.py` (si no, gris).
3. **Icono del enlace (🛒)**: su emoji premium en `STORE_LINK_ICONS` (ver
   [`TELEGRAM-EMOJIS.md`](TELEGRAM-EMOJIS.md)); si no, sale el genérico.
4. **Fotos**: comprueba que su CDN deja descargar las fotos desde la API (Coolmod necesitaba
   cookies). Si no, sus posts saldrán con la foto original enviada por URL.
5. **Prueba**: publica un chollo de esa tienda en el canal Admin y mira la tarjeta en el móvil.

## Cambiar el logo del canal

Sustituye `app/assets/images/logo-bctech.png` por el original (PNG transparente, mismo
nombre) y reinicia la API y el scheduler. Se escala a 340 px de ancho.
