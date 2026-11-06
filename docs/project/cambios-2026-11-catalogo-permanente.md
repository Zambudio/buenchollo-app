# Cierre operativo: catálogo permanente y publicaciones de Telegram (2026-11-06)

## Qué cambia para Pedro

- Los chollos caducados o cuya oferta termina siguen teniendo ficha y URL. Salen de los listados de ofertas activas; la ficha indica que la oferta terminó. Si el producto vuelve a cumplir las reglas de precio y stock, se reactiva el mismo chollo con sus votos, comentarios y favoritos.
- `price_check` revisa diariamente los listings de Amazon. Puede terminar o reactivar ofertas y avisar de bajadas de precio en ofertas activas. El panel muestra las transiciones, permite ejecutar la revisión manualmente y ya no ofrece «Restaurar». La purga automática solo afecta a listings con falta de disponibilidad confirmada durante 30 días por defecto; si el producto pierde todos sus listings, también se eliminan su ficha y chollos.
- Las publicaciones enviadas a Telegram quedan registradas. Al detectar una reactivación o bajada relevante, el canal Admin recibe un aviso y después el texto de la última publicación del chollo con el precio corregido. El panel permite «Usar la última publicación». Estos avisos pueden ser reales desde la primera revisión en producción.

## Cambios del sistema

- Migración `20261105120000`: crea `products` y `product_listings`, vincula y amplía `deals`, añade `scheduled_task_run_items.transition` y `scheduled_tasks.running_since`, hace backfill de chollos existentes y activa `price_check` con frecuencia `daily`. La marca `running_since` evita ejecuciones simultáneas del worker y del panel.
- Migración `20261106120000`: crea `telegram_publications` (canal, origen, texto, imagen, precio y mensaje) y añade el umbral `price_drop_percent` a la configuración de `price_check`.
- `GET /v1/deals/sitemap`: entradas de chollos activos y caducados para el sitemap web. `GET /v1/telegram/publications?deal_id=<UUID>`: historial del chollo para el administrador, con texto corregido al precio actual cuando es posible. `POST /v1/telegram/notify` acepta `deal_id` UUID para asociar el envío. `POST /v1/admin/scheduled-tasks/{id}/confirm` ejecuta sin body de candidatos; devuelve 409 si hay una ejecución en curso. El endpoint de restauración se eliminó.
- `TELEGRAM_ENABLED` tiene valor por defecto `true`; está en `false` en el entorno local y las pruebas. `PUBLIC_SITE_URL` tiene por defecto `https://buenchollotech.com`. `price_check` usa `min_discount_percent` (5), `purge_after_days` (30) y `price_drop_percent` (5) como valores iniciales de migración, conservando la configuración previa donde corresponda.
- Las consultas a Creators API se espacian y solo envían ASIN válidos. Un fallo de lote no altera precio, disponibilidad ni estado de la oferta.

## Despliegue de la API en el NAS (pendiente de autorización de Pedro)

La web se despliega automáticamente tras el merge a `main`; la API y el scheduler del NAS requieren un paso independiente. Hasta entonces, la web nueva puede solicitar `/v1/deals/sitemap` y `/v1/telegram/publications` que la API antigua no ofrece. Procedimiento: [NAS-SSH §1.1](../guides/NAS-SSH.md).

1. Hacer `pg_dump` de la base de producción **antes de cualquier cambio** y comprobar que el backup existe.
2. Parar `local-env` si está arrancado sobre el share.
3. En la copia del share, que debe estar en `main`, hacer `git pull`. No cambiar de rama allí.
4. En la ruta real del proyecto del NAS, ejecutar `docker-compose build && docker-compose up -d` mediante el procedimiento SSH de la guía. No hay dependencias nuevas en este lote. El arranque de la API ejecuta `alembic upgrade head` y aplica ambas migraciones.
5. Comprobar `/health`, `/health/ready` y `/v1/deals/sitemap`; verificar en `scheduled_tasks` que `price_check` está `enabled` y `daily`.
6. Comprobar que `TELEGRAM_ENABLED` no está a `false` en el `.env` del NAS, sin mostrar su contenido ni otros secretos.

La primera ejecución diaria puede consultar Amazon para todo el catálogo y enviar avisos reales al canal Admin.

## Riesgos y rollback

- El backfill agrupa chollos por tienda y ASIN. Guardar el `pg_dump` antes del despliegue permite recuperar datos si hay un problema de migración o de comportamiento.
- Para volver a la revisión anterior de esquema, ejecutar primero el `downgrade` de `20261106120000` (elimina `telegram_publications` y su configuración; **pierde el registro acumulado**) y después el de `20261105120000` (elimina catálogo, vínculos y estado nuevo; **pierde los datos nuevos**). El segundo downgrade desactiva `price_check` y lo deja semanal: el código antiguo borraba los chollos revisados.
- No basta con volver al código anterior mientras la base siga en la revisión nueva: el arranque ejecuta Alembic y requiere los ficheros de migración que correspondan a la revisión aplicada. Restaurar código y esquema de forma coordinada, o conservar las revisiones hasta completar el rollback.
- Un rollback de la web puede hacerse revirtiendo el merge en `main` o seleccionando la versión anterior del Worker. El despliegue de la API y sus migraciones es independiente.

## Referencias

- [ADR-017](../adr/ADR-017-catalogo-permanente.md)
- [Especificación](../superpowers/specs/2026-11-05-catalogo-permanente-design.md)
- [Plan de fase 1](../superpowers/plans/2026-11-05-catalogo-permanente-fase1.md)
- [Estado del proyecto](../../PROJECT_STATUS.md)
- [Deuda técnica, TD-39 a TD-45](10-technical-debt.md)
