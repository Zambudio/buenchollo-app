# Redes de afiliación: Awin y Tradedoubler

> Guía viva. Decisión de diseño en [ADR-019](../adr/ADR-019-redes-afiliacion-awin-tradedoubler.md).
> Estado a 2026-11-08: **en producción** (PR #78, merge `c47269c`, Alembic `20261108120000`)
> con las credenciales de ambas redes configuradas en el NAS. **Ninguna tienda aprobada**
> todavía: todos los programas siguen deshabilitados. El parser solo se ha probado con
> fixtures sintéticas (`buenchollo-api/app/tests/fixtures/affiliates/`).
>
> **Para activar una tienda cuando la aprueben: [`AFFILIATE-ACTIVATION-RUNBOOK.md`](AFFILIATE-ACTIVATION-RUNBOOK.md).**

## 1. Qué hace

Desde **Admin → Chollos**, el panel «Autocompletar desde Amazon, Awin o Tradedoubler»:

1. Recibe una URL de producto. Amazon sigue su flujo de siempre (`/products/preview-from-url`).
2. Cualquier otra URL va a `POST /v1/affiliates/import`, que:
   - valida la URL (http/https, host público, sin IPs, credenciales ni puertos raros);
   - detecta la tienda por dominio en el **registro de programas** (`affiliate_programs`);
     si hay varios programas (Miravia 37166/37168) pide elegir;
   - comprueba que el programa está habilitado, que hay credenciales y que la adhesión es
     `joined` (si no, no genera enlaces ni importa);
   - busca el producto en una **fuente autorizada**: catálogo local de feeds Awin
     sincronizados o la Products API de Tradedoubler (nunca scraping de la tienda);
   - obtiene el **enlace afiliado oficial** (Link Builder de Awin; `productUrl` de Tradedoubler);
   - devuelve la oferta común con procedencia, antigüedad del dato, campos pendientes,
     candidatos (si no hay coincidencia exacta o hay varias variantes) y si ya existe un chollo.
3. El editor se rellena como **borrador** y muestra tres etapas: *Enlace generado →
   Producto importado → Lista para publicar*. «SOLO ENLACE» genera solo el enlace.
4. Publicar (estado activo, o Telegram) exige pasar las reglas del backend
   (`POST /v1/affiliates/readiness`, `PublicationGuard`). Un borrador siempre se guarda.

Nada se publica al pegar una URL.

## 2. Reglas de publicación (chollos de redes)

Bloquean publicar (no guardar como borrador):

| Regla | Detalle |
|---|---|
| Programa | habilitado y adhesión `joined` |
| Enlace | de seguimiento de la red (`awin1.com`, `tidd.ly`, `*.tradedoubler.com`) |
| Precio anterior | mayor que el actual **y** con significado que lo pruebe + evidencia escrita. Un PVP recomendado o un «precio original» del feed **no** lo prueban |
| Ahorro | calculable exacto (Decimal, redondeo half-up igual que el panel) |
| Envío, descripción corta, categoría, imagen | obligatorios; la categoría la elige una persona (sin «Varios» automático) |
| Imágenes | el programa debe autorizar `web` y `telegram` (`restrictions.image_channels`) |
| Frescura | fecha real del dato del proveedor o comprobación manual en tienda dentro de `max_data_age_hours` (24 h por defecto). Una consulta reciente no prueba un dato reciente |

Tipos de precio anterior: `provider_price_history_30d` (mínimo de los 30 días previos a la
bajada según el historial de Tradedoubler), `store_strikethrough_verified` y
`manual_verified` justifican; `rrp`, `feed_original_price` y `none`, no.

El post de Telegram añade la línea de envío y el aviso adicional del programa
(`disclosure_text`). Los chollos de Amazon no cambian.

## 3. Credenciales (solo en `buenchollo-api/.env` del NAS)

Nunca en `buenchollo-web`, Git, capturas ni chat. El navegador solo ve booleanos
(`GET /v1/affiliates/status`). Los errores y logs se redactan.

| Variable | Dónde se obtiene | Uso |
|---|---|---|
| `AWIN_PUBLISHER_ID` | ui.awin.com, arriba a la izquierda. Conocido: `3148595` | Link Builder, programmes, feeds |
| `AWIN_ACCESS_TOKEN` | ui.awin.com → menú de usuario → *API Credentials* (token OAuth2 de la Publisher API) | `POST /publishers/{id}/linkbuilder/generate`, `GET /publishers/{id}/programmes` |
| `AWIN_FEED_API_KEY` | *Toolbox → Create-a-Feed*: en el enlace de descarga, el texto tras `apikey/`. **Distinta** del token anterior | Lista y descarga de feeds |
| `TRADEDOUBLER_SITE_ID` | Tradedoubler → *Sites*: ID del espacio promocional (no el de cuenta ni el de programa) | Solo para el deeplink verificado |
| `TRADEDOUBLER_PRODUCTS_TOKEN` | Tradedoubler → *Account → Manage tokens*, sistema **PRODUCTS** (40 hex) | Products API y `productFeeds` |

Opcionales (con valores por defecto): `AWIN_RATE_LIMIT_PER_MINUTE=20`,
`AWIN_FEED_MAX_DOWNLOAD_MB=200`, `AWIN_FEED_MAX_UNCOMPRESSED_MB=1500`, `AWIN_FEED_MAX_ROWS=300000`.

Tras editar el `.env` del NAS hay que reiniciar `buenchollo-api` y `buenchollo-scheduler`
(`docs/guides/NAS-SSH.md`). Cambio directo en producción: verificar con
`GET /v1/affiliates/status` (todo `true`) y rollback borrando las variables.

## 4. Registro de programas (Admin → Afiliación)

La migración `20261108120000` siembra estas referencias **sin verificar**: adhesión
`unknown`, deshabilitadas y sin permiso de imágenes.

| Red | ID | Tienda | Notas |
|---|---|---|---|
| Awin | 20982 | PcComponentes | |
| Awin | 124624 | Coolmod | |
| Awin | 77630 | Fnac ES | sin tienda vinculada en `stores` (crear y asignar) |
| Awin | 21707 | Samsung ES | dominio `samsung.com/es` (solo la tienda española) |
| Awin | 37166 | Miravia (influencers/redes) | no se elige automáticamente |
| Awin | 37168 | Miravia (otros modelos) | la ficha de 37166 remite aquí |
| Tradedoubler | 270504 | MediaMarkt ES | imágenes restringidas a Tradedoubler: verificar condiciones |

Por programa se configura: habilitado, tienda, dominios (admite ruta), adhesión manual,
espacios promocionales, canales con permiso de imagen, aviso adicional, caducidad del dato,
feeds seleccionados, restricciones (Marketplace, vendedores, canales) y, en Tradedoubler,
«deeplink verificado».

- **COMPROBAR ADHESIÓN**: Awin consulta `programmes?relationship=joined|pending|suspended|rejected&countryCode=ES`
  (4 llamadas); lo que no aparece queda `notjoined`. Tradedoubler: un programa con feeds
  accesibles al token pasa a `joined` (y se descubren sus feeds); sin feeds no se deduce
  nada. La adhesión manual queda marcada `manual` con fecha.
- **SINCRONIZAR FEEDS AWIN**: en segundo plano. Descarga la lista de feeds (actualiza
  nombre, idioma, nº de productos, `Last Imported`) y solo descarga los **seleccionados**
  cuyo `Last Imported` cambió. También corre a diario a las 05:17 en el scheduler y con
  `python scripts/sync_awin_feeds.py [--force] [--program <id>]`.

### Sincronización de feeds: garantías

- Nunca dentro de una petición del editor; un advisory lock de transacción evita dos a la vez.
- Descarga en streaming con tope de tamaño; gzip/zip con tope de descompresión y de filas.
- Escritura por generación: la nueva solo se activa al terminar bien; si falla se borra la
  parcial y el catálogo anterior sigue sirviendo. El estado y el error (redactado) quedan
  en el feed.
- Solo se guardan los campos necesarios (texto plano sin HTML, una imagen, precio, PVP,
  envío, stock, identificadores, fecha del proveedor). La URL de descarga (lleva la clave)
  no se persiste.

## 5. Resolución de productos

- **Awin**: coincidencia exacta por URL normalizada (`merchant_deep_link`: host sin `www`,
  sin barra final ni seguimiento, parámetros de variante ordenados) o por EAN / SKU /
  `aw_product_id`. Varias filas para la misma URL (color, reacondicionado...) → «coincidencia
  ambigua» y el editor pide elegir. Sin coincidencia → candidatos por título (al menos la
  mitad de las palabras del slug), nunca seleccionados solos.
- **Tradedoubler**: no hay búsqueda por URL. Se busca en los feeds seleccionados (máx. 3) por
  EAN, por `spId` (SKU de la tienda) o por palabras del slug, y solo se acepta la coincidencia
  exacta de `sourceProductUrl`. Se prefiere `productUrl` (enlace con nuestro seguimiento).
- Identidad para deduplicar: `external_id = aw|tr:<advertiser>:<id de producto/variante>`.
  Reimportar no crea otro chollo (aviso «ya existe») y no pisa lo editado a mano: los campos
  editados que difieren se listan como conflictos con «USAR IMPORTADO».

## 6. Enlaces sin ficha

- Awin: siempre Link Builder (`advertiserId` + `destinationUrl` validada, conservando los
  parámetros de variante; `clickref=bct-editor`). Si Link Builder falla y hay fila del feed,
  se usa su `aw_deep_link` (también generado por Awin para nuestra cuenta). Sin respuesta
  válida **no** se construye un enlace.
- Tradedoubler: la documentación pública de Products API no describe el deeplink. Solo si el
  propietario confirma en el generador de enlaces de su cuenta que el formato del programa es
  `https://clk.tradedoubler.com/click?p=<programa>&a=<site ID>&url=<destino>` marca
  «Deeplink verificado» y se usa. Si no, la interfaz muestra la limitación.

## 7. Activar una tienda aprobada

El procedimiento paso a paso (comprobación de estado con
`scripts/check_affiliate_status.py`, condiciones del programa, configuración, sincronización,
validación del parser con datos reales, primera importación, publicación, cierre y marcha atrás)
está en [`AFFILIATE-ACTIVATION-RUNBOOK.md`](AFFILIATE-ACTIVATION-RUNBOOK.md).

## 8. Hallazgos de la validación inicial (2026-11-08)

Credenciales de ambas redes configuradas; Awin y Tradedoubler responden a la consulta de feeds, pero las tiendas objetivo siguen sin catálogo accesible (Awin `feedList` devolvía 944 feeds, ninguno de ellas; Tradedoubler, cero).

- **Que Link Builder devuelva un enlace no prueba aprobación ni atribución de comisiones**: por eso la aplicación conserva la comprobación de adhesión.
- **La Promotions API no sustituye a los feeds de producto**: devuelve textos del proveedor (campañas, páginas de categoría), no precios ni fichas verificables. No se importan como chollos.
- **Awin** solicita enlace corto (`shorten=true`) y prefiere `shortUrl`; si Awin no lo devuelve conserva el largo, así que el acortamiento no está garantizado.
- **Tradedoubler** pide `sourceproducturl=true` y `priceHistory=true`: la comparación exacta por URL y el historial de 30 días necesitan esos campos opcionales. Conserva el enlace oficial del producto, sin acortamiento propio.
- Se conserva `shippingCost=0` como envío gratuito (no es dato ausente) y `NaN` se trata como precio ausente.
- Los enlaces de seguimiento exigen HTTPS, host exacto permitido, sin credenciales y puerto estándar; se rechazan dominios que solo terminan en `tradedoubler.com`.
- Los feeds deseleccionados o marcados como no disponibles dejan de participar en las búsquedas, y `supports_import=false` impide consultar el catálogo (queda el flujo de solo enlace). Un CSV de Awin con esquema desconocido falla explícitamente y conserva el catálogo anterior.

**Limitaciones abiertas**: formato real de cada feed (Google frente a CSV de Awin) sin validar; programar publicaciones de redes no Amazon (TD-48); acortamiento de Tradedoubler no implementado; cuota de Awin limitada por proceso y no global entre workers; las condiciones e imágenes deben verificarse por programa, y la aceptación de un programa no basta para publicar automáticamente.
