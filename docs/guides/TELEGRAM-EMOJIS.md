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
   ejemplo `"xiaomi": "<id>"`.
4. Test en `app/tests/test_telegram_link_icon.py`, PR y reiniciar la API y el scheduler.

## Registro de iconos

Todos los `custom_emoji_id` conocidos (2026-11-22). «En uso» = ya sale en los posts.

| Icono | `custom_emoji_id` | Dónde | Estado |
|---|---|---|---|
| Amazon | `5346056560537779652` | `AMAZON_LINK_ICON` | en uso (🛒 de Amazon) |
| Genérico (eslabones) | `5271604874419647061` | `GENERIC_LINK_ICON` | en uso (🛒 de Coolmod y tiendas sin icono) |
| Xiaomi | `5262875916031244720` | `STORE_LINK_ICONS["xiaomi"]` | en uso (por tienda; el dominio `mi.com` no lo detecta) |
| AliExpress | `5373265917092316632` | `STORE_LINK_ICONS["aliexpress"]` | en uso (por tienda o dominio) |
| Steam | `5373144051690258848` | `STORE_LINK_ICONS["steam"]` | en uso (dominio `store.steampowered.com`; no hay tienda «Steam» en `stores` todavía) |
| Samsung, mitad izquierda | `5307876255486453093` | `SAMSUNG_LINK_ICON_PARTS[0]` | guardado |
| Samsung, mitad derecha | `5309981060044433947` | `SAMSUNG_LINK_ICON_PARTS[1]` | guardado |
| WhatsApp | `5334998226636390258` | `WHATSAPP_ICON` | guardado |

Pendientes:

- **Samsung** ocupa dos emojis seguidos (el logo es ancho). El 🛒 del post es un solo
  carácter y cada entidad `custom_emoji` cubre un emoji del texto, así que hace falta que
  el post escriba dos emojis base (p. ej. `🛒🛒`) cuando la tienda es Samsung y que
  `build_entities` asigne las dos mitades en orden. Mientras tanto, Samsung usa el genérico.
- **WhatsApp**: icono para enlazar el Canal de WhatsApp desde los posts de chollos (formato
  por decidir).
- Los iconos de los demás emojis del post (🍄, 💶, 💰, ✏️, ⚠️, 🔗) están en `CUSTOM_EMOJI_MAP`.
