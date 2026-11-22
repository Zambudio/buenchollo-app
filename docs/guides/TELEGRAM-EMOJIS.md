# Emojis premium de Telegram

Los posts del canal llevan **emojis premium** (custom emoji): el texto usa un emoji normal
(🍄, 💶, 🛒…) y la API de Telegram lo sustituye por el premium mediante una entidad
`custom_emoji` con su `custom_emoji_id`. Quien no tiene Telegram Premium ve el emoji normal.
Código: `buenchollo-api/app/modules/telegram/application/post_generator.py`.

## Iconos fijos

| Emoji | Uso | Constante |
|---|---|---|
| 🍄 💶 💰 ✏️ ⚠️ 🔗 | título, precio, ahorro, descripción, fin de oferta, enlace web | `CUSTOM_EMOJI_MAP` |

## Icono del enlace de compra (🛒), por tienda

Desde el 2026-11-22 el 🛒 ya no es siempre el logo de Amazon:

| Tienda | Icono | Constante |
|---|---|---|
| Amazon (`amazon.*`, `amzn.to`, `amzn.eu`, `link.amazon`) | logo de Amazon | `AMAZON_LINK_ICON` |
| Tiendas con icono propio | su logo | `STORE_LINK_ICONS` |
| El resto (Coolmod…) y enlaces a nuestra web | genérico (eslabones) | `GENERIC_LINK_ICON` |

Cómo se elige (`link_icon_for`):

1. Si se conoce el chollo (publicación desde el panel con `deal_id`), manda el **nombre de
   su tienda**: el enlace de Awin (`tidd.ly`, `awin1.com`) no dice de qué tienda es.
2. Si no, el **dominio** del enlace de esa línea (cada 🛒 del resumen semanal se decide
   por separado).
3. Si nada coincide, el genérico.

## Añadir el icono de una tienda

1. En Telegram, envía el emoji premium (solo el emoji) a **@JsonDumpBot**. Vale cualquier
   bot que devuelva el JSON del mensaje (@RawDataBot, @ShowJsonBot).
2. En la respuesta, copia `message.entities[].custom_emoji_id` (número de ~19 cifras).
   Si envías varios emojis en un mensaje, salen en el mismo orden.
3. Añade la entrada a `STORE_LINK_ICONS` con una clave en minúsculas y sin espacios que
   aparezca en el nombre de la tienda (`stores.name`) o en el dominio de su web, por
   ejemplo `"samsung": "<id>"`, `"xiaomi": "<id>"`, `"aliexpress": "<id>"`.
4. Test en `app/tests/test_telegram_link_icon.py`, PR y reiniciar la API y el scheduler.

IDs actuales: Amazon `5346056560537779652`; genérico `5271604874419647061`.
