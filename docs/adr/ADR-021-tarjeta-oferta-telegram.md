# ADR-021 — Tarjeta de oferta como imagen de cada chollo en Telegram

## Estado

Aceptado · 2026-11-23 · en producción.

## Contexto

Cada publicación de chollo en Telegram llevaba la foto del producto tal cual: cada tienda la sirve con un tamaño y una proporción distintos, el canal se veía desigual y el precio solo estaba en el texto. Pedro diseñó una plantilla, «Simple claro» (1200 × 800), con la foto, la insignia de descuento, la tienda, el precio actual, el anterior tachado, «Ahorras X €» y el logo del canal. La especificación y la referencia visual están en `_handoff/plantilla-telegram-oferta/` (raíz de WEB-Buenchollo): `ESPECIFICACION.md`, `referencia.html` y los PNG de referencia.

Opciones para generarla:

1. **Motor HTML con navegador headless** (Playwright/Chromium, como `Baner_Publicaciones`): reproduce el HTML tal cual, pero exige un Chromium en el contenedor del NAS, más memoria y más tiempo por imagen.
2. **Satori u otro renderizador HTML→SVG**: otro runtime (Node) en la API.
3. **Pillow** en la API, como el collage del resumen semanal (`weekly_collage.py`): sin dependencias nuevas, en memoria y en milisegundos. A cambio, el diseño se programa en Python.

## Decisión

1. **Pillow** (opción 3). `telegram/application/deal_card.py` compone la tarjeta con una función pura (datos + bytes de la foto → JPEG). Reproduce el HTML de referencia emulando el modelo de cajas del navegador (alto de línea «normal» de Space Grotesk, línea base, `letter-spacing`, centrado tipo flex); difiere de los PNG de referencia en ~1 % de píxeles.
2. **Punto único de publicación**: `telegram/application/deal_photo.py` decide la imagen de **todos** los envíos de un chollo: panel (`/telegram/notify`), publicaciones programadas, republicación al canal Admin tras una bajada de precio y copia de WhatsApp. Nadie más llama a `deal_card` directamente.
3. **Nunca bloquea**: sin precio anterior, con anterior ≤ actual, si la foto no se descarga o no se lee, si falla la composición o si Telegram rechaza la tarjeta, se publica la foto original como antes. Si Telegram no responde tras recibir la petición (tiempo de lectura agotado), la tarjeta se da por enviada para no duplicar el post; si ni siquiera conectó, no se da por enviada.
4. **Coherencia con el texto**: la tarjeta usa los mismos datos que el post. En el panel mandan los precios que envía la web (un «antes» vacío no se completa con el del chollo guardado) y la insignia muestra el mismo porcentaje que el texto.
5. **Tiendas**: logo por tienda en `app/assets/images/stores/<clave>.png` (PNG transparente); sin logo, punto de color (`STORE_COLORS`) y nombre. El `logo_url` de la tabla `stores` no se usa: varios son SVG o enlaces de terceros, y la tarjeta no debe depender de internet al publicar.
6. **Interruptor** `DEAL_CARD_ENABLED` (por defecto `true`): con `false` todo se publica con la foto original.
7. El descargador de imágenes conserva las cookies entre redirecciones del mismo host (Coolmod redirige en bucle sin ellas), sin dejar de validar cada salto contra SSRF.

## Consecuencias

- **Positivas:** el canal tiene un formato fijo (siempre 3:2) y el precio, el descuento y el ahorro se leen en la imagen. Sin dependencias ni servicios nuevos.
- **Negativas:** cambiar el diseño exige tocar Python (y sus tests), no un HTML. Cada tienda nueva necesita su logo para verse completa.
- **A vigilar:** la descarga y la composición ocurren dentro de la transacción del worker de programadas, con la fila bloqueada; alargan ese bloqueo unos segundos. El logo del canal (`app/assets/images/logo-bctech.png`) es provisional.

Guía operativa: [`docs/guides/TELEGRAM-TARJETA-OFERTA.md`](../guides/TELEGRAM-TARJETA-OFERTA.md).
