# Catálogo permanente — Fase 1: los chollos ya no se borran

Fecha: 2026-11-05 · Rama: `develop` · Estado: borrador para aprobación

Documento de origen: «Evolución BuenChollo Tech — Catálogo permanente, multitienda y
fidelización» (visión del 04/11/2026). Este diseño cubre **solo la Fase 1** de esa visión.

## 1. Intención

Hoy un chollo se borra cuando caduca, sube de precio o se agota. Con él se pierden la URL
(y su posicionamiento), los votos, los comentarios y los favoritos (borrado en cascada).

Pedro quiere pasar a un **catálogo permanente**:

- Los anuncios se mantienen. Cada día se actualiza el precio.
- Si sube de precio o deja de estar rebajado, **deja de mostrarse como oferta** y nada más.
- Si vuelve a estar rebajado, **se reactiva solo en la web** (sin aprobación) y se avisa en
  el **canal Admin de Telegram** (no en el oficial); Pedro decide desde ahí si lo reenvía.
- Solo se elimina algo cuando lleva **mucho tiempo sin estar disponible** o ya no existe en
  la tienda. Si el producto está vinculado a otras tiendas que sí lo venden, se elimina
  **solo esa tienda** del producto.
- Sentar las bases (producto ↔ tiendas ↔ ofertas) para un catálogo grande y multitienda.

## 2. Situación actual (auditoría)

| Pieza | Fichero | Qué hace hoy |
|---|---|---|
| Borrado por caducidad | `deals/application/cleaner_service.py::clean_expired_deals` | Cron 03:00 **y al arrancar el scheduler**: `DELETE` de deals con `expires_at` < ahora − 2 días |
| Marcado por caducidad | `cleaner_service.py::mark_expired_deals` | Cada 5 min: `active` → `expired` si `expires_at` pasó. **Se mantiene** |
| Revisión de precios | `scheduled_tasks/application/price_check_handler.py` | Consulta Amazon en lotes de 10; motivos `out_of_stock`, `price_increase` (> tolerancia, 10 % por defecto), `no_longer_deal`; **`execute()` borra el deal** |
| Restaurar | `scheduled_task_service.restore_item` + `POST /runs/items/{id}/restore` | Recrea el deal borrado desde la foto en `scheduled_task_run_items` |
| Candidatos | `DealRepository.get_active_without_expiry_with_asin` | Solo deals `active`, sin `expires_at`, con ASIN |
| Modelo | `deals` | Una fila mezcla producto, tienda (`store_id`, `external_id`, `affiliate_url`) y oferta (precios, estado) |
| FK a `deals` | votos, favoritos, comentarios, notificaciones, `scheduled_deals` (CASCADE); `deal_submissions` (SET NULL) | |
| Ficha | `web/src/routes/chollo.$slug.tsx` | `expired` ya es visible al público (schema.org `OutOfStock`); `draft`/`scheduled` ocultos |
| Sitemap | `web/src/routes/sitemap[.]xml.ts` | Solo `status = active` |
| Canal Admin | `config.telegram_admin_channel_id` | Ya existe y el panel lo ofrece como «Canal Admin» |
| Alertas de usuario | `alerts/application/alert_matcher.py` | Por palabra clave/categoría/precio; se disparan al crear/activar un deal |

## 3. Objetivos, no objetivos y antiobjetivos

**Objetivos de la Fase 1**

1. Ningún proceso automático borra un chollo por subir de precio, agotarse o caducar.
2. Revisión **diaria** del precio y la disponibilidad de todos los chollos con tienda
   consultable (hoy Amazon), estén en oferta o no.
3. Transiciones automáticas: oferta activa ⇄ sin oferta, con aviso al canal Admin al reactivar.
4. Purga controlada: tienda no disponible ≥ 30 días → se quita esa tienda; producto sin
   tiendas → se elimina.
5. Modelo `products` + `product_listings` con los deals existentes migrados sin pérdida.
6. La ficha `/chollo/:slug` sigue siendo la URL pública permanente y muestra claramente si
   hay oferta o no.

**No objetivos (fases posteriores de la visión)**

- Ficha `/producto/:slug` con tabla de precios multitienda (Fase 2).
- Integrar tiendas distintas de Amazon (Fase 2).
- Histórico de precios, gráficas, alertas de precio por producto (Fase 3).
- Rankings/Top 10, newsletter, comunidad, monetización (Fases 4–5).
- Planificador por prioridad/cuotas para catálogos de decenas de miles (Fase 3); en Fase 1
  basta con la revisión diaria por lotes.

**Antiobjetivos (sería un fracaso aunque funcione)**

- Mostrar como «oferta» algo que ya no lo es, o un precio de Amazon de más de 24 h como actual.
- **Guardar histórico de precios de Amazon** (la política de Amazon Associates/Creators API
  restringe almacenar y rastrear precios). En Fase 1 de Amazon solo se guarda el precio
  vigente, sobrescrito en cada revisión.
- Spamear el canal Admin con el mismo producto cada día.
- Perder votos/comentarios/favoritos en la migración.
- Borrar algo por un fallo puntual de la API (error de red ≠ «no existe»).

## 4. Modelo de datos

Se mantiene la tabla `deals` (renombrarla rompería API, frontend, FKs y tests sin beneficio).
Se añaden dos tablas y columnas nuevas. Migración Alembic reversible.

### `products` (la ficha permanente)

`id`, `slug` (único), `title`, `brand`, `description`, `short_description`, `image_url`,
`images`, `category_id`, `subcategory_id`, `gtin` (nullable, para Fase 2),
`status` (`active` | `discontinued`), `created_at`, `updated_at`.

### `product_listings` (el producto en una tienda)

`id`, `product_id` (FK CASCADE), `store_id` (FK), `external_id` (ASIN en Amazon),
`canonical_url`, `affiliate_url`, `current_price`, `reference_price` (precio de referencia
que da la propia tienda, p. ej. el «antes» de Amazon), `discount_percentage` (el que da la
tienda), `in_stock`, `availability` (`available` | `unavailable` | `not_found` | `unknown`),
`unavailable_since`, `last_checked_at`, `created_at`, `updated_at`.
Único: `(store_id, external_id)`.

### `deals` (la oferta y la página pública) — columnas nuevas

- `product_id` (FK SET NULL), `listing_id` (FK SET NULL).
- `offer_end_reason` (`price_increase` | `no_longer_deal` | `out_of_stock` | `not_found` |
  `expired_date` | `manual`, nullable).
- `last_price_check_at`.
- `offer_price`: precio con el que se publicó o reactivó por última vez (referencia de las
  reglas 5.2; `current_price` se sobrescribe a diario y no sirve para eso). Se inicializa con
  el `current_price` actual en la migración.
- `admin_notified_at`, `admin_notified_price` (antispam del canal Admin).
- `status` mantiene sus valores: `active` = en oferta y visible en listados;
  `expired` = **sin oferta ahora**, ficha visible pero fuera de listados.

Se mantiene **un deal por listing** en Fase 1: la reactivación reutiliza el mismo deal
(misma URL, votos y comentarios). Decisión: es lo que Pedro describe («los anuncios se
mantienen») y conserva el SEO. Llevar un registro de ofertas por periodo queda para Fase 3.

### Migración de datos

1. Por cada deal con `store_id` + `external_id`: agrupar por `(store_id, upper(external_id))`.
   Cada grupo → 1 `product` + 1 `listing`; todos los deals del grupo apuntan a ellos.
   Si hay varios deals para el mismo listing, se conservan todos (no se fusionan votos);
   el más reciente es el que revisa la tarea diaria y los demás quedan `expired`.
2. Deals sin `external_id` (manuales, otras tiendas): 1 producto + 1 listing cada uno,
   con `availability = unknown`; no entran en la revisión diaria.
3. `slug` del producto = slug del deal (deduplicado con sufijo si choca).
4. `downgrade`: elimina columnas y tablas nuevas; los deals quedan como estaban.
5. Copia de seguridad (`pg_dump`) de producción antes del despliegue.

## 5. Comportamiento

### 5.1 Revisión diaria (tarea `price_check` reconvertida)

- Recorre **listings** consultables (Amazon con ASIN), no solo deals activos, en lotes de 10.
- Actualiza en el listing: precio, referencia, descuento, stock, `availability`,
  `last_checked_at`; y en el deal vinculado: `current_price`, `previous_price`,
  `discount_percentage`, `savings_amount`, `last_price_check_at`.
- **Error de lote o de red** → no se toca nada de ese lote (ni precio ni disponibilidad).
- **ASIN que Amazon devuelve como inexistente** (error por ítem en una respuesta correcta)
  → `availability = not_found`.
- La frecuencia pasa a **diaria** (`frequency_preset = daily`) y la tarea queda habilitada
  por defecto tras la migración. La hora sigue siendo configurable desde el panel.

### 5.2 Reglas de oferta

**Fin de oferta (deal `active`)**: se mantienen las reglas actuales del `PriceCheckHandler`,
que ya funcionan en producción, para no expirar de golpe chollos publicados por cupón,
mínimo tipo Keepa o `previous_price` manual:

- sin stock → `out_of_stock`; no encontrado → `not_found`;
- precio > `offer_price` × (1 + tolerancia 10 %) → `price_increase`;
- la tienda informa descuento ≤ 0, o el precio iguala/supera el `previous_price` del deal
  → `no_longer_deal`.

En esos casos → `expired` con `offer_end_reason`. **No se borra.** Si no se cumple ninguno,
solo se actualiza el precio.

**Reactivación (deal `expired` por precio/stock/no encontrado)**: listing disponible **y**
(precio ≤ `offer_price` **o** descuento informado por la tienda ≥ `min_discount_percent`,
configurable, **por defecto 5 %**). Es decir: vuelve al precio al que ya fue chollo, o la
tienda vuelve a marcarlo rebajado.

- Reactivación →
  `status = active`, `published_at = ahora` (sube en «Últimos»), `offer_end_reason = null`,
  `offer_price = precio actual`, aviso al canal Admin y alertas de usuario (5.3).
- Los deals `expired` por fecha (`expired_date`) también actualizan precio y disponibilidad
  (la ficha muestra datos frescos), pero no se reactivan solos.
- No se reactivan automáticamente deals `expired` por fecha (`expired_date`) ni los
  caducados a mano (`manual`), ni `draft`/`scheduled`.

### 5.3 Aviso al canal Admin

- Mensaje: título, precio nuevo, precio de referencia y % de descuento, tienda, enlace de
  afiliado y enlace a la ficha web. Se reutiliza el formato de `telegram/post_generator`
  cuando sea posible.
- Antispam: no se vuelve a avisar del mismo deal en **7 días** salvo que el precio sea
  **menor** que `admin_notified_price`.
- Si Telegram falla, la reactivación en la web se mantiene y se registra el error.
- Las alertas de usuario existentes (`AlertMatcher`) se disparan en la reactivación con el
  mismo antispam.

### 5.4 Purga por no disponibilidad

- Un listing con `availability ∈ {unavailable, not_found}` durante **≥ 30 días**
  (`unavailable_since`) se elimina.
- Si al producto le quedan otros listings, el producto sigue; su deal pasa a apuntar al
  listing disponible más barato si lo hay.
- Si el producto se queda sin listings → se elimina el producto **y sus deals** (con votos,
  comentarios y favoritos). Es la única eliminación automática que queda.
- Días configurables (`purge_after_days`, por defecto 30) en la configuración de la tarea.

### 5.5 Alta de un producto que ya está en el catálogo

Hoy, al aprobar una propuesta de la comunidad se **borran** los deals `expired` del mismo
ASIN (`submissions/application/review_submission.py`), y el alta desde el panel lanza
`DuplicateDealError` con opción de «sobrescribir». Con el catálogo permanente:

- Si el listing ya existe, el alta (panel, propuesta aprobada o chollo programado) **actualiza
  y reactiva el deal existente**: misma URL, votos y comentarios. Se actualizan precio,
  textos e imagen con los nuevos; `published_at = ahora`; `offer_price = precio nuevo`.
- En una propuesta de la comunidad, `created_by` pasa a ser quien la propuso (se le atribuye
  la oferta nueva).
- Si el deal existente está **activo**, se mantiene el aviso de duplicado actual.
- Se elimina el borrado «replaced_by_submission».

### 5.6 Ejecución manual desde el panel

Se mantiene la vista previa: muestra qué ofertas terminarían, cuáles se reactivarían y qué se
purgaría. «Confirmar» aplica **todas** las transiciones de la vista previa (sin selección
individual, igual que la ejecución automática). El registro de ejecuciones muestra el tipo de
transición de cada elemento.

### 5.7 Lo que se retira

- Job `clean_expired_deals` (cron 03:00 y llamada al arrancar el scheduler).
- `PriceCheckHandler.execute` como borrado; el registro de ejecuciones
  (`scheduled_task_runs/items`) pasa a guardar **transiciones** (oferta terminada,
  reactivada, purgada) en vez de borrados.
- Botón/endpoint «Restaurar»: ya no hay nada que restaurar. Se retira de la UI; el endpoint
  se elimina.

## 6. Web

- **Ficha `/chollo/:slug` con `status = expired`:** aviso visible «Ahora mismo no está en
  oferta» con el precio actual y «comprobado hace X h». Si la última comprobación de un precio
  de Amazon tiene más de 24 h, no se muestra el precio: solo «Ver precio en Amazon».
  Votos/comentarios siguen visibles.
- **Ficha `active`:** se muestra «Precio comprobado hace X h». Si pasan más de 24 h (por
  ejemplo, porque Amazon falla varios días), aparece la nota «Precio de hace X: puede haber
  cambiado».
- **Listados, portada, búsqueda, categorías:** solo `active` (ya es así). En Fase 1 no se
  oculta el precio en las tarjetas. Hoy un precio puede tener hasta una semana; con la
  revisión diaria pasa a ≤ 24 h en condiciones normales. El caso de fallo prolongado queda
  registrado como deuda técnica para Fase 3 (frescura por prioridad).
- **Sitemap:** incluye también `expired` (URLs permanentes).
- **Panel admin de chollos:** filtro por estado con el motivo de fin de oferta y la fecha de
  la última comprobación.
- **Panel de tareas programadas:** muestra transiciones en vez de borrados; nuevos campos
  `min_discount_percent` y `purge_after_days`.
- Mobile-first, sin desbordamiento a 375 px.

## 7. Restricciones

- Arquitectura: monolito modular, Clean pragmática (ADR-001/002). Nuevo módulo `catalog`
  (`products`, `product_listings`) siguiendo `api → application → domain ← infrastructure`.
- Amazon: precio vigente sobrescrito, sin histórico; precio mostrado ≤ 24 h o se oculta.
- Producción ejecuta la copia del NAS en `main`: el trabajo va en `develop` (copia en
  `C:\Users\fadwe\dev\bct-develop`); el merge a `main` y el despliegue solo cuando Pedro lo pida.
- La migración corre sola al arrancar el contenedor (`alembic upgrade head`): tiene que ser
  idempotente y rápida con el volumen actual.
- Tests: unitarios de reglas (5.2 a 5.5) con fakes de Amazon/Telegram; integración de
  la migración y del repositorio; prueba en el entorno local (`local-env`) antes del merge.
- Se documenta con un ADR (catálogo permanente) y se actualiza `PROJECT_STATUS.md`.

## 8. Decisiones del diseñador (revisables)

- Mantener `deals` como tabla de ofertas y página pública; un deal por listing.
- Mínimo de descuento para considerar oferta: 5 %. Tolerancia de subida: 10 % (la actual).
- Antispam del canal Admin: 7 días o precio más bajo.
- Purga a los 30 días sin disponibilidad.
- La reactivación cambia `published_at` para que el chollo aparezca como nuevo.
- Deals sin ASIN quedan fuera de la revisión automática.
- Fin de oferta con las reglas actuales; reactivación por precio ≤ `offer_price` o descuento
  de tienda ≥ 5 % (5.2).
- Volver a dar de alta un ASIN existente reactiva el mismo deal en vez de borrar o duplicar (5.5).
- Ejecución manual: vista previa + confirmar todo (5.6).
- Precio con más de 24 h: nota en la ficha, sin ocultarlo en tarjetas; queda como deuda (6).

## 9. Queda a criterio del constructor

Nombres internos, orden de commits, estructura exacta del mensaje de Telegram, cómo
distinguir «no encontrado» en la respuesta de la Creators API, índices concretos y el
diseño visual del aviso en la ficha (siguiendo el estilo actual).
