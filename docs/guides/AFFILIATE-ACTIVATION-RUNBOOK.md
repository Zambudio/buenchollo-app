# Runbook: activar una tienda de Awin o Tradedoubler

> **Para el agente que ayude a Pedro cuando una tienda apruebe la solicitud.**
> Léelo entero antes de empezar. Contexto técnico en
> [`AFFILIATE-NETWORKS.md`](AFFILIATE-NETWORKS.md) y [ADR-019](../adr/ADR-019-redes-afiliacion-awin-tradedoubler.md);
> historial de pruebas en [`AFFILIATE-VALIDATION-2026-11-08.md`](AFFILIATE-VALIDATION-2026-11-08.md).
> Acceso al NAS: [`NAS-SSH.md`](NAS-SSH.md).

## 0. Punto de partida (2026-11-08)

- Código **en producción**: PR #78 (merge `c47269c`), API y scheduler recreados,
  Alembic en `20261108120000`. El job diario `run_awin_feed_sync` (05:17) está registrado.
- **Credenciales configuradas** en `buenchollo-api/.env` del NAS (las cinco variables;
  ver `AFFILIATE-NETWORKS.md` §3). No hace falta pedirlas otra vez.
- Ningún programa aprobado todavía. Estado real consultado ese día:

| Red | ID | Tienda | Adhesión en la red | En la BD |
|---|---|---|---|---|
| Awin | 20982 | PcComponentes | `pending` | `unknown`, deshabilitado |
| Awin | 124624 | Coolmod | `pending` | `unknown`, deshabilitado |
| Awin | 77630 | Fnac ES | `pending` | `unknown`, deshabilitado, **sin tienda vinculada** |
| Awin | 21707 | Samsung ES | `pending` | `unknown`, deshabilitado |
| Awin | 37166 | Miravia (influencers/redes) | `pending` | `unknown`, deshabilitado |
| Awin | 37168 | Miravia (otros modelos) | `notjoined` | `unknown`, deshabilitado |
| Tradedoubler | 270504 | MediaMarkt ES | sin feeds accesibles | `unknown`, deshabilitado |

- Awin `feedList` devolvía 944 feeds, **ninguno** de estas tiendas; Tradedoubler, 0 feeds.
  Un feed de producto solo aparece cuando la tienda acepta.
- El código de lectura de catálogos (columnas del feed Awin, respuesta de la Products API
  de Tradedoubler) **solo se ha probado con datos sintéticos**. La primera tienda real
  es también la primera validación del parser (paso 5).

## 1. Reglas para el agente

- **Pedro hace los clics del panel** (`/admin/afiliacion`, `/admin` → Chollos) y lee las
  condiciones en Awin/Tradedoubler. El agente guía, comprueba con el script del §2 y
  revisa resultados. No teclear credenciales de Pedro en ninguna web.
- **Nunca** mostrar ni copiar tokens, claves o URLs de descarga de feeds (llevan la clave)
  en chat, Git, docs ni logs. El script del §2 ya los omite.
- **No publicar** nada (web ni Telegram) sin que Pedro lo revise. Primera prueba siempre
  como **borrador**; Telegram primero en el canal Admin.
- Los permisos (espacios promocionales, imágenes) se marcan **solo** si las condiciones
  del programa los autorizan por escrito. Ante la duda, no se marcan: el editor bloqueará
  publicar con imagen, que es lo correcto.
- Cambios de código: rama `develop`, test que falle primero, PR a `main`, CI verde, y
  luego despliegue (`NAS-SSH.md` §1.1). La copia del NAS **es** lo que ejecuta producción.
- Responder a Pedro en español.

## 2. Comprobar el estado (solo lectura)

Desde la raíz del repo, en la máquina de trabajo:

```bash
ssh -o BatchMode=yes nas-zambu \
  'sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker exec -i buenchollo-api python -' \
  < buenchollo-api/scripts/check_affiliate_status.py
```

No escribe en la BD ni necesita reconstruir la imagen (el script va por stdin). Devuelve
JSON con `credentials`, `errors` y, por programa, `live_membership` (lo que dice la red
ahora), `db` (lo guardado) y `feeds_offered` (feeds de producto que la red ofrece).

Cómo leerlo:

| Resultado | Significado | Siguiente paso |
|---|---|---|
| `credentials` con algún `false` | falta una variable en el `.env` del NAS | ver `AFFILIATE-NETWORKS.md` §3; reiniciar API y scheduler |
| `errors.awin_programmes` / `awin_feeds` / `tradedoubler_feeds` | token caducado o red caída | Pedro regenera el token; no seguir hasta que desaparezca |
| Awin `live_membership: joined` | **aprobado** | §3 |
| Awin `pending` / `notjoined` / `rejected` / `suspended` | no aprobado | esperar; no habilitar |
| TD `joined (feeds accesibles)` | MediaMarkt aprobado y con feed | §3 y §7 |
| TD `sin feeds accesibles` | no aprobado, o aprobado sin feed de producto | preguntar a Pedro si le llegó la aprobación (ver §7) |
| `feeds_offered` vacío con `joined` | aprobado pero sin feed de producto | solo funcionará «SOLO ENLACE» (Awin); avisar a Pedro |

## 3. Leer las condiciones del programa (Pedro, con el agente)

En Awin (*Advertisers → My Programmes → <tienda> → Terms*) o Tradedoubler (*Programs →
<programa> → Program info / Terms*), anotar:

1. **Espacios promocionales** permitidos: web propia, Telegram (canal de mensajería),
   redes sociales. Si Telegram no está permitido, no marcarlo.
2. **Uso de imágenes** de producto: ¿se pueden usar las del feed en web y en Telegram?
   (MediaMarkt/Tradedoubler las restringe: leerlo con calma).
3. **Aviso de afiliación** obligatorio o texto concreto → «Aviso adicional del programa».
4. Exclusiones: Marketplace / vendedores externos, categorías, cupones, precios que no
   se pueden anunciar. Anotarlas en «Notas»/restricciones.
5. Antigüedad máxima del precio si la exigen (por defecto 24 h).

## 4. Configurar el programa en `/admin/afiliacion`

1. Comprobar que los cuatro indicadores de arriba (Awin Publisher API, Awin feeds,
   Tradedoubler Products, Tradedoubler site ID) están en verde.
2. Pulsar **COMPROBAR ADHESIÓN**. El programa aprobado debe pasar a `joined`
   (fuente `api`, o `api_feeds` en Tradedoubler).
3. En la ficha del programa:
   - **Tienda**: vincular la tienda de `stores`. Para **Fnac** hay que crearla antes en
     Admin → Tiendas y luego vincularla.
   - **Dominios**: revisar (`samsung.com/es` lleva ruta a propósito).
   - **Espacios promocionales autorizados** y **Imágenes permitidas en** (`web`,
     `telegram`): solo lo autorizado en el §3. Publicar con imagen exige **ambos** canales.
   - **Aviso adicional del programa (post)**, **Caducidad del dato (h)**.
   - **Habilitado** ✔ y **GUARDAR**.
4. **Miravia**: hay dos programas (37166 «influencers / redes sociales», 37168 «otros
   modelos de publisher»; la ficha de 37166 remite a 37168). Habilitar solo el que esté
   `joined` y cuyas condiciones encajen con una web de chollos. Si los dos estuvieran
   habilitados, el editor pide elegir.

## 5. Catálogo: sincronizar y validar el parser (primera vez por red)

### Awin

1. **SINCRONIZAR FEEDS AWIN** (descubre los feeds del programa).
2. En la ficha, marcar el feed **en español** (idioma `es`, el de más productos si hay
   varios) y **SINCRONIZAR ESTE PROGRAMA**. Va en segundo plano.
3. Pasados unos minutos, repetir el script del §2: en `db.feed_sync` debe salir
   `last_status: ok` y `rows` > 0. Alternativa por CLI dentro del contenedor:
   `docker exec buenchollo-api python scripts/sync_awin_feeds.py --program <uuid>`
   (con `sudo -n` y ruta completa, `NAS-SSH.md` §4).
4. Si `last_status: error`, leer `last_error` (ya redactado) y logs
   (`docker logs --tail 200 buenchollo-api`):

| Error | Causa | Arreglo |
|---|---|---|
| esquema de CSV desconocido | el feed no trae `product_name` y alguno de `aw_product_id` / `product_id` / `merchant_product_id` (p. ej. feed en formato Google) | elegir un feed CSV de Awin; si no lo hay, ampliar `iter_feed_rows` / `map_feed_row` en `buenchollo-api/app/modules/affiliates/infrastructure/awin_client.py` |
| tamaño / filas máximas | feed mayor que los topes | subir `AWIN_FEED_MAX_DOWNLOAD_MB`, `AWIN_FEED_MAX_UNCOMPRESSED_MB` o `AWIN_FEED_MAX_ROWS` en el `.env` del NAS y reiniciar |
| `already_running` | otra sincronización en curso | esperar |

5. **Validación del parser con datos reales** (obligatoria la primera vez): importar un
   producto (§6) y comparar con la ficha de la tienda: título, precio, PVP (`rrp_price`),
   envío (`delivery_cost`), stock, imagen, EAN, variante (color/capacidad) y fecha del dato
   del proveedor (zona horaria de `last_updated`). Mapeo en `map_feed_row` y `_parse_dt`
   del mismo fichero. Si algo no cuadra: crear fixture con una fila real **anonimizada**
   en `buenchollo-api/app/tests/fixtures/affiliates/`, test que falle, corregir, PR.

### Tradedoubler (MediaMarkt)

No hay sincronización: se consulta la Products API en cada importación. Tras COMPROBAR
ADHESIÓN, marcar el feed descubierto en la ficha y GUARDAR. Validar con un producto real
igual que arriba; mapeo en `map_td_product`
(`buenchollo-api/app/modules/affiliates/infrastructure/tradedoubler_client.py`): campos
`offers`, `priceHistory` (justifica el precio anterior con el mínimo de 30 días),
`productImage`, `productUrl` (enlace con seguimiento) y `sourceProductUrl` (se usa para
casar la URL exacta).

## 6. Primera importación real (borrador)

En `/admin` → Chollos, panel «Autocompletar desde Amazon, Awin o Tradedoubler»:

1. Pegar la URL de un producto de la tienda **que esté en el feed**.
2. Esperado: etapas «Enlace generado» y «Producto importado»; enlace de la red
   (`awin1.com` / `tidd.ly` en Awin; `*.tradedoubler.com` en Tradedoubler); procedencia
   y antigüedad del dato visibles.
3. Abrir el enlace en una ventana privada: debe pasar por la red y acabar en **esa**
   ficha y variante de la tienda.
4. Probar también **SOLO ENLACE** con una URL de la tienda que no esté en el feed.
5. **Guardar como borrador**. Reimportar la misma URL debe avisar «ya existe» y no
   duplicar.

Si sale «coincidencia ambigua», es normal en productos con variantes: elegir la correcta.
Si no encuentra el producto y sí está en la tienda, puede que el feed sea de otro día:
comprobar `rows` y la fecha de sync.

## 7. Particularidades de Tradedoubler

- Si Pedro dice que MediaMarkt aprobó pero el script da `sin feeds accesibles`: el
  programa no ha asignado feed de producto al token. Opciones: pedírselo a la tienda o
  marcar la adhesión manual (`joined`) y usar solo enlaces — pero **solo** si el deeplink
  está verificado (abajo); si no, no hay enlace válido.
- **Deeplink verificado en mi cuenta TD**: marcarlo solo si Pedro, en el generador de
  enlaces de su cuenta Tradedoubler, ve que el formato del programa es
  `https://clk.tradedoubler.com/click?p=270504&a=<site ID>&url=<destino>`. Ver TD-47.
- Imágenes: Tradedoubler las restringe; marcar `web`/`telegram` solo con permiso escrito.

## 8. Publicar el primer chollo

Sobre el borrador del §6:

1. Elegir categoría (nunca automática), descripción corta y envío.
2. **Precio anterior**: tipo y evidencia. Válidos: historial 30 días del proveedor
   (Tradedoubler), tachado verificado en tienda, comprobación manual. **No** valen PVP
   recomendado ni «precio original» del feed. Pasar el caso al agente `price-validator`
   si hay dudas.
3. Cuando el bloque marque «Lista para publicar», publicar en la web. Telegram: primero el
   canal Admin, revisar el post (línea de envío y aviso del programa) y luego el público.
4. Recordatorio: los chollos de redes **no se pueden programar** todavía (TD-48);
   se publican a mano.

## 9. Cerrar la activación (documentar y commitear)

Por cada tienda activada:

- Actualizar la tabla del §0 de este runbook (adhesión, fecha, feed elegido, permisos).
- `AFFILIATE-NETWORKS.md`: cabecera de estado y tabla del §4.
- `docs/project/10-technical-debt.md`: TD-46 — anotar qué red queda validada en vivo;
  cerrarla cuando lo estén Awin **y** Tradedoubler.
- `PROJECT_STATUS.md`: entrada con fecha.
- Commit en `develop` (no dejar ficheros pendientes) y PR a `main` si hubo cambios de código.

## 10. Marcha atrás

- Desactivar una tienda: desmarcar **Habilitado** y GUARDAR. No se borra nada; los
  chollos ya publicados siguen con su enlace. Bloquea importar y publicar nuevos.
- Desactivar una red entera: quitar sus variables del `.env` del NAS y reiniciar
  `buenchollo-api` y `buenchollo-scheduler` (`NAS-SSH.md` §5.2). Los indicadores pasan a rojo.
- Un fallo de sincronización nunca borra el catálogo anterior (escritura por generaciones).
