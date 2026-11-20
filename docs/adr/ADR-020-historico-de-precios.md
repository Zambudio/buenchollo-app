# ADR-020 — Histórico de precios propio

## Estado

Aceptado · 2026-11-20 · en `develop`. Sustituye el punto 6 de [ADR-017](ADR-017-catalogo-permanente.md) («Amazon: ningún histórico»).

## Contexto

La hoja de ruta de retención (noviembre de 2026) pone los datos de precio propios en el centro de la propuesta de valor: mínimo histórico, media de 90 días y un veredicto («Comprar / Buen precio / Esperar»). Hasta ahora la ficha solo enlazaba el gráfico de Keepa y `product_listings` guardaba el último precio, que se sobrescribía en cada revisión.

Pronto se publicarán chollos de más tiendas (Awin y Tradedoubler, [ADR-019](ADR-019-redes-afiliacion-awin-tradedoubler.md)), así que el histórico tiene que valer para cualquier tienda, no solo para Amazon.

**Riesgo asumido.** Los precios de Amazon llegan por la Creators API con la cuenta de Afiliados. Las páginas de licencia de Afiliados (Amazon.com, Amazon.co.uk) limitan el almacenamiento de contenido no gráfico a 24 h, con refresco obligatorio, y la documentación de la Creators API recomienda una caché de 1 h para las ofertas. Guardar un histórico de esos precios va contra esa licencia. El riesgo no es legal sino contractual: que Amazon cierre la cuenta de Afiliados. Pedro lo decidió el 2026-11-20 conociendo el riesgo. Antes de mostrar estos datos en público conviene revisar la versión española del acuerdo y valorar alternativas para Amazon, como la API de pago de Keepa.

## Decisión

1. **Tabla `price_history`** (migración `20261120120000`): un punto por listing y día natural de Madrid (`uq_price_history_listing_day`). Guarda `product_id` y `store_id` para consultar por producto en todas sus tiendas. `price` es la última observación del día y `low_price` la más baja entre las automáticas (upsert con `LEAST`). Una edición manual (`source = deal`) sustituye el mínimo del día en lugar de combinarse con él: así un precio mal tecleado y corregido no queda como mínimo histórico. También guarda `reference_price`, `in_stock`, `source` y `observed_at`. Tiene RLS activado, como el resto de tablas, porque solo la API accede.
2. **Fuentes de datos:**
   - `price_check`: la revisión diaria apunta el precio de cada listing que Amazon devuelve con precio **y con stock**, en un único upsert al final de la ejecución. No apunta nada si el lote falla, si el producto no aparece, si llega sin precio, si está agotado (sería un falso mínimo, porque no se podía comprar) o si el listing se purga.
   - `deal`: el alta (`link_new_deal`), la reactivación y la edición manual de `current_price` de un chollo, de cualquier tienda. Si el chollo ya no coincide con su listing (cambió de tienda o de identificador), no se apunta, porque sería el precio de otra tienda.
   - `backfill`: la migración siembra el precio actual de cada listing.
   - Las tiendas no Amazon solo reciben puntos con las altas y ediciones hasta que sus feeds se revisen de forma periódica.
3. **Reglas puras** en `catalog/domain/price_history.py`: `observed_day`, `window_start` y `compute_stats`, que calcula el mínimo, el máximo y la media de una ventana (90 días por defecto). Con varias tiendas, cada día cuenta con su precio más bajo. El resumen de todo el histórico (días con datos, primer día, mínimo histórico y su fecha) se calcula en SQL (`CatalogRepository.all_time_summary`) para no cargar puntos antiguos.
4. **API:** `GET /v1/catalog/products/{id}/price-history?days=90` (de 7 a 365, límite de 60 peticiones por minuto) devuelve los puntos de la ventana y las estadísticas. La lógica vive en el caso de uso `catalog/application/price_history_service.py`; el router solo la expone.
5. **Sin interfaz todavía:** las etiquetas («Mínimo histórico», «Precio normal») y el veredicto se construirán cuando haya datos suficientes.

## Consecuencias

- **Positivas:** a partir de ahora acumulamos datos propios de precio para cualquier tienda, y el veredicto y las etiquetas tienen base.
- **Negativas:** riesgo contractual con Amazon Afiliados mientras se guarden precios de su API.
- **Tamaño:** como mucho una fila por listing y día, unas 350 diarias con el catálogo actual. Es poco.
- **Pendiente:** registrar el precio al publicar un chollo programado (`publication_worker`). Hoy lo recoge la revisión del día siguiente.
