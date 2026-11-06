---
title: "Rediseño y tops comunitarios automáticos"
category: "product"
date: "2026-11-06"
status: "active"
---

# Rediseño y tops comunitarios (ADR-018)

- Pedro pidió una web más viva, con tarjetas horizontales, categorías visuales, navegación clara hacia blog/categorías y módulos laterales. Referencias de densidad y exploración: Chollómetro y Chollero, sin copiar el diseño.
- **Aclaración de Pedro:** todos los productos compiten automáticamente. Los públicos (con oferta `active` o `expired`) entran en el top de categoría/subcategoría; los vinculados solo a borradores no se muestran. Voto positivo reversible por usuario registrado y producto, independiente del voto de chollo. Orden por votos; empate: oferta activa, creación e ID.
- Pedro pidió poder votar el producto también desde la tarjeta y la ficha del chollo (chip «Votar producto», distinto del pulgar). Estado único en `features/catalog/productVotes.ts`; `product_id` expuesto en respuestas de chollos. `product_top_votes.user_id` → `profiles.user_id` CASCADE.
- Los tests `-m integration` usan `DATABASE_URL` del `.env`, que apunta a **producción** (con rollback). Ejecutarlos contra local-env: `DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:54329/buenchollo_local` y el Python de `%LOCALAPPDATA%/BuenCholloLocal/api-venv`.
- Podio de tres y puestos 4-10, sin rellenar posiciones inexistentes. Tabla `product_top_votes`, migración `20261107120000`; endpoints `/v1/catalog/tops/{slug}`, `/v1/catalog/my-votes` y `/v1/catalog/products/{id}/vote`.
- Portada y categorías renderizan datos en HTML inicial con TanStack Start. Banner de voto, sidebar de chollos populares y blog, tarjetas horizontales y directorio visual de categorías.
- **Desplegado 2026-11-06**: PR #67 mergeada (`477166f`), API y scheduler reconstruidos en el NAS, Alembic `20261107120000`. Backup previo `bct-prod-pre-tops-20261106T173021Z.dump`.
- Backup en NAS: el `.env` tiene `DATABASE_URL` entre comillas (quitarlas en el contenedor) y los scripts remotos deben ir por Bash heredoc, no por PowerShell (BOM/CRLF).
- **Próximo desarrollo pedido por Pedro:** diseñar puntos por acciones y recompensas; no se ha implementado ni acordado su mecánica.
- Detalle: `docs/adr/ADR-018-tops-comunitarios-productos.md`, `docs/project/redisenio-web-y-tops-2026-11.md` y `PRODUCT.md`.
