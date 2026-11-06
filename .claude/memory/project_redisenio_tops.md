---
title: "Rediseño y tops comunitarios automáticos"
category: "product"
date: "2026-11-06"
status: "active"
---

# Rediseño y tops comunitarios (ADR-018)

- Pedro pidió una web más viva, con tarjetas horizontales, categorías visuales, navegación clara hacia blog/categorías y módulos laterales. Referencias de densidad y exploración: Chollómetro y Chollero, sin copiar el diseño.
- **Aclaración de Pedro:** todos los productos compiten automáticamente. Los públicos (con oferta `active` o `expired`) entran en el top de categoría/subcategoría; los vinculados solo a borradores no se muestran. Voto positivo reversible por usuario registrado y producto, independiente del voto de chollo. Orden por votos; empate: oferta activa, creación e ID.
- Podio de tres y puestos 4-10, sin rellenar posiciones inexistentes. Tabla `product_top_votes`, migración `20261107120000`; endpoints `/v1/catalog/tops/{slug}`, `/v1/catalog/my-votes` y `/v1/catalog/products/{id}/vote`.
- Portada y categorías renderizan datos en HTML inicial con TanStack Start. Banner de voto, sidebar de chollos populares y blog, tarjetas horizontales y directorio visual de categorías.
- Código en `develop`, commit `015d752`, PR borrador #67 con CI verde. Producción `main` sigue sin este cambio; la API del NAS se actualiza por separado tras merge.
- **Próximo desarrollo pedido por Pedro:** diseñar puntos por acciones y recompensas; no se ha implementado ni acordado su mecánica.
- Detalle: `docs/adr/ADR-018-tops-comunitarios-productos.md`, `docs/project/redisenio-web-y-tops-2026-11.md` y `PRODUCT.md`.
