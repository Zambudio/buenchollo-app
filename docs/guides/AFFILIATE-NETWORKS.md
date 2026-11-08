# Redes de afiliación: Awin y Tradedoubler

> Guía viva. Decisión de diseño en [ADR-019](../adr/ADR-019-redes-afiliacion-awin-tradedoubler.md).
> Estado a 2026-11-08: **código en `develop`, sin credenciales ni programas
> verificados**. Nada se ha validado todavía contra las APIs reales de Awin o
> Tradedoubler: solo con fixtures sintéticas (`buenchollo-api/app/tests/fixtures/affiliates/`).

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

## 7. Activar la primera tienda aprobada (pasos)

1. Desplegar `develop` a producción cuando Pedro lo decida (migración `20261108120000`, sin deps nuevas).
2. Añadir `AWIN_PUBLISHER_ID=3148595`, `AWIN_ACCESS_TOKEN` y `AWIN_FEED_API_KEY` al `.env` del
   NAS y reiniciar API y scheduler. Comprobar `Admin → Afiliación`: los indicadores en verde.
3. Pulsar **COMPROBAR ADHESIÓN**. Solo los programas que Awin devuelva como `joined` sirven.
4. En el programa aprobado: vincular la tienda, revisar dominios, leer las condiciones del
   programa y marcar espacios promocionales y permiso de imágenes solo si lo autorizan,
   ajustar el aviso adicional, **Habilitado**, GUARDAR.
5. **SINCRONIZAR FEEDS AWIN** (descubre los feeds), seleccionar el feed en español y
   sincronizar ese programa. Ver «última sync: ok (N filas)».
6. Probar en Admin → Chollos con una URL real de la tienda: debe salir «Producto importado»
   y un enlace `awin1.com`. Comprobar el enlace a mano y guardar como **borrador**.
7. Completar categoría, precio anterior con evidencia y comprobación en tienda; cuando el
   bloque diga «Lista para publicar», publicar en la web y, si se quiere, en Telegram
   (primero en el canal Admin para revisar).

Para Tradedoubler (MediaMarkt): `TRADEDOUBLER_PRODUCTS_TOKEN` (+ `TRADEDOUBLER_SITE_ID`),
COMPROBAR ADHESIÓN, seleccionar el feed descubierto y verificar antes las condiciones de
imágenes. Validar en vivo la forma real de la respuesta (los mapeos se escribieron con la
documentación y fixtures).


## Revisi?n de integraci?n (2026-11-08)

Credenciales de ambas redes configuradas; Awin y Tradedoubler responden a la consulta de feeds. Las tiendas objetivo siguen sin cat?logo accesible. Ver [informe de validaci?n](AFFILIATE-VALIDATION-2026-11-08.md) para resultados, correcciones y limitaciones. Awin solicita enlaces cortos; Tradedoubler conserva el enlace oficial del producto, sin acortamiento propio.
