# ADR-017 — Catálogo permanente: los chollos ya no se borran

## Estado

**Aceptado** · 2026-11-06 · Fase 1 implementada en `develop`
([spec](../superpowers/specs/2026-11-05-catalogo-permanente-design.md),
[plan](../superpowers/plans/2026-11-05-catalogo-permanente-fase1.md)). Sustituye la parte de
ADR-012 que borraba chollos y el punto de ADR-016 «aprobar borra los expirados».

## Contexto

Hasta ahora un chollo se borraba cuando caducaba (job de las 03:00 y al arrancar el
scheduler) o cuando la revisión de precios detectaba subida, falta de stock o fin de la
rebaja. Con él desaparecían la URL (y su posicionamiento), los votos, los comentarios y los
favoritos (borrado en cascada). La visión del proyecto (04/11/2026) es pasar a un catálogo
permanente y multitienda, con la sección de chollos y Telegram como capa rápida encima.

## Decisión

1. **Separar producto, tienda y oferta sin rehacer `deals`.** Nuevo módulo `catalog` con
   `products` (ficha permanente) y `product_listings` (el producto en una tienda: precio
   vigente, referencia, stock, disponibilidad, `unavailable_since`, `last_checked_at`).
   `deals` sigue siendo la oferta y la página pública (`/chollo/:slug`) y gana
   `product_id`, `listing_id`, `offer_end_reason`, `offer_price` (precio con el que se
   publicó o reactivó), `last_price_check_at` y el antispam del canal Admin. Un deal por
   listing: la reactivación reutiliza el mismo deal (misma URL, votos y comentarios).
   Migración `20261105120000`, reversible, con backfill que agrupa por tienda + ASIN.
2. **Ciclo de vida por estado, no por borrado.** `active` = en oferta; `expired` = sin
   oferta ahora, ficha visible y fuera de listados. La tarea `price_check` pasa a diaria y
   revisa listings: actualiza precio/stock, termina ofertas (`price_increase`,
   `no_longer_deal`, `out_of_stock`, `not_found`) y las reactiva. Reglas puras en
   `catalog/domain/offer_rules.py`.
3. **Reactivación con histéresis según el motivo de fin**: subida → solo si vuelve a su
   `offer_price`; agotado/retirado → si vuelve con stock dentro de la tolerancia; ya no
   rebajado → si la tienda vuelve a marcar descuento ≥ `min_discount_percent` dentro de la
   tolerancia. Nunca se reactiva algo que la misma revisión terminaría. El descuento que
   informa Amazon es frente a su propia referencia y, por sí solo, no prueba una bajada.
4. **Aviso al canal Admin** (nunca al oficial) tras el commit de cada ejecución, como mucho
   uno por deal cada 7 días salvo que el precio baje más; las alertas de usuario se
   disparan con el mismo antispam. La web reactiva sin aprobación.
5. **Única eliminación automática:** un listing con disponibilidad confirmada como
   `unavailable`/`not_found` durante `purge_after_days` (30). Si al producto le quedan otras
   tiendas solo se quita esa; si no, se eliminan producto y deals. Un fallo de Amazon nunca
   cuenta como «no disponible».
6. **Amazon:** solo se guarda el precio vigente, sobrescrito en cada revisión; ningún
   histórico. La ficha solo presenta un precio como actual si tiene ≤ 24 h. Peticiones
   espaciadas (~1/s, la Creators API responde 429 si se excede), un reintento por lote y
   solo identificadores con formato ASIN (uno inválido hace que Amazon rechace el lote).
7. **Alta de un producto conocido:** panel, propuesta aprobada o chollo programado
   reactivan el deal `expired` existente en vez de crear otro o borrarlo.

## Consecuencias

- Las URLs de chollos son permanentes; el sitemap incluye también los `expired`.
- El botón y el endpoint «Restaurar» desaparecen; `scheduled_task_run_items` registra
  transiciones (`offer_ended`, `reactivated`, `purged`). Las columnas `restored_*` quedan
  sin uso para no tocar el histórico.
- Coste de Amazon: una petición por cada 10 productos y día (≈ 1 s cada una). Con miles de
  productos hará falta priorizar la cadencia (Fase 3) y sacar la ejecución manual del
  ciclo petición/respuesta HTTP (TD-41).
- `downgrade` de la migración desactiva `price_check`: el código anterior borraba lo que
  revisaba.
- Exclusión mutua entre el worker y «Ejecutar ahora» con una marca atómica
  (`scheduled_tasks.running_since`, caduca a los 30 min) en lugar de un advisory lock: la
  transacción se cierra antes de consultar Amazon para no retener conexiones de PgBouncer.
- Solo es «no encontrado» lo que Amazon declara inexistente en `errors`; una respuesta vacía
  sin errores por producto es un fallo del lote. Reactivar limpia los datos de la oferta
  anterior (fecha de fin, cupón, precio «antes») y nunca se reactiva una oferta cuya fecha de
  fin ya pasó. Los productos sin ningún chollo se eliminan en la revisión diaria.

## Alternativas descartadas

- **Renombrar `deals` a `offers` y crear una ficha `/producto/:slug` ya.** Rompía API,
  frontend, FKs y tests sin beneficio inmediato; la ficha multitienda llega en Fase 2.
- **Un deal nuevo por cada periodo de oferta.** Perdía votos/comentarios y la URL posicionada
  en cada reactivación.
- **Reactivar por el descuento que informa la tienda.** Probado con datos reales: convertía
  subidas de precio en «vuelve a estar en oferta» (spec 5.2 corregido).
