# ADR-018 — Tops comunitarios de productos permanentes

## Estado

Aceptado para `develop` · 2026-11-06. Complementa [ADR-017](ADR-017-catalogo-permanente.md).

## Contexto

El voto de un chollo mide la acogida de una oferta concreta. Un producto puede permanecer mientras su oferta caduca o se reactiva. Pedro quiere un top por categoría y subcategoría donde todos los productos compitan automáticamente, sin selección manual de candidatos.

## Decisión

- Cada producto **activo con al menos un chollo publicado** (`active` o `expired`) entra en la clasificación de su categoría y subcategoría. Los productos vinculados solo a borradores no se exponen.
- Un usuario autenticado puede dar un voto positivo a un producto y retirarlo repitiendo la acción. `product_top_votes` impone unicidad por `(product_id, user_id)`; el voto permanece al cambiar el estado de la oferta.
- El orden es número de votos descendente; en empate, primero los productos con oferta activa y después creación del producto e ID. Solo se muestran los diez primeros y nunca se inventan posiciones si hay menos productos.
- El top enlaza a la oferta publicada representativa cuando existe. Un precio solo se muestra cuando esa oferta está `active`; para las caducadas se indica que no hay oferta activa.
- La API expone `GET /v1/catalog/tops/{slug}`, `GET /v1/catalog/my-votes?product_ids=...` y `POST /v1/catalog/products/{id}/vote`. La web consume estos contratos a través de `apiClient`.

## Consecuencias

- El ranking nace con empates a cero; la posición inicial es estable, no una recomendación editorial.
- La unicidad y el índice por producto permiten contar votos sin guardar contadores derivados. La tabla activa RLS y el backend usa el JWT para identificar al votante.
- El voto del producto es distinto de la temperatura del chollo. Puntos y recompensas se tratarán en otra fase.
- El despliegue de web y API sigue siendo independiente. La migración `20261107120000` es aditiva; el downgrade elimina los votos de producto y, por tanto, el ranking acumulado.
