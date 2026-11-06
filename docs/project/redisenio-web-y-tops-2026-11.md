# Rediseño web y tops comunitarios · 2026-11-06

## Qué cambia para Pedro y los visitantes

- La portada sustituye el texto SEO desplegable por un banner que invita a explorar y votar. El feed usa tarjetas horizontales, precio y tienda visibles, y módulos laterales alimentados por chollos populares y artículos publicados del blog.
- La navegación muestra Inicio, Chollos, Tops y categorías, y Blog. La página de categorías ofrece una franja visual con imágenes de productos presentes en los últimos chollos (icono de reserva) y un directorio compacto de subcategorías.
- Cada categoría y subcategoría muestra su top: podio para los tres primeros y lista hasta el décimo. Todos los productos públicos de esa categoría compiten automáticamente; no hay selección manual. Solo votan usuarios registrados. Repetir el voto lo retira.
- La página de categoría mantiene después los chollos activos. El catálogo conserva productos aunque un chollo esté caducado; en ese caso el top no presenta su precio como oferta vigente.

## Sistema y SEO

- `product_top_votes` (migración Alembic `20261107120000`) guarda un voto por usuario y producto. La unicidad evita duplicados; el ranking cuenta votos reales y, en empate, prioriza oferta activa y después fecha e ID.
- API: `GET /v1/catalog/tops/{slug}`, `GET /v1/catalog/my-votes?product_ids=...` (autenticado) y `POST /v1/catalog/products/{id}/vote` (autenticado, limitado a 30 peticiones/minuto). Solo aparecen productos activos con al menos una oferta pública `active` o `expired`; los borradores quedan fuera.
- Las categorías, sus tops y el feed de portada cargan en los loaders de TanStack Start, de modo que el HTML inicial contiene enlaces y contenido legible. Las URLs de categoría ya están en el sitemap; no se generan páginas de top vacías o duplicadas. No se añaden valoraciones estructuradas ficticias.
- El blog tiene una entrada lateral visible hacia artículos publicados. Para mejorar la captación orgánica, Pedro debe publicar guías y comparativas útiles y mantener títulos, enlaces internos y datos de producto correctos. Ningún cambio técnico garantiza el primer puesto en búsquedas.

### Trabajo editorial para atraer búsquedas al blog

1. Elegir preguntas concretas de cada subcategoría (por ejemplo, cómo elegir un monitor según uso y presupuesto) y responderlas con criterios propios, datos comprobados y fecha de revisión. No crear artículos que solo repitan fichas de tiendas.
2. Enlazar cada guía con su categoría y, cuando aporte valor, con productos del top y chollos vigentes; enlazar desde las categorías a las guías pertinentes. Mantener estos enlaces cuando una oferta caduque.
3. Revisar en Search Console consultas, impresiones y clics por página, y en la analítica propia la navegación blog → categoría/chollo. Priorizar la mejora de artículos existentes antes de multiplicar páginas similares.
4. Usar datos estructurados de reseñas o valoraciones solo si el contenido y las valoraciones reales cumplen los requisitos de Google; los votos de este top no son reseñas editoriales.

Referencias: [guía SEO de Google](https://developers.google.com/search/docs/fundamentals/seo-starter-guide), [contenido útil](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) y [datos de producto](https://developers.google.com/search/docs/appearance/structured-data/product-snippet).

## Validación y despliegue

En `develop`: backend `pytest -q -m "not integration"` 686 correctas y 58 de integración sobre PostgreSQL 17 local; frontend typecheck y lint sin errores, 457 Vitest, 33 Playwright y build SSR; comprobación visual a 390 y 1440 px sin desbordamiento horizontal. La migración se aplicó **solo a la base local** de `local-env`.

Para publicar, verificar primero la CI de la PR `develop` → `main`. El merge desplegará el Worker web automáticamente. La API del NAS requiere después `pg_dump` previo, actualización de la copia `main` del share, rebuild/reinicio de API y scheduler según [NAS-SSH](../guides/NAS-SSH.md) §1.1, y comprobación de `/health`, `/health/ready`, `/v1/catalog/tops/monitores` y Alembic `20261107120000`. Durante el intervalo entre web y API, las páginas de categoría podrán mostrar el top vacío hasta que la API se actualice. No hay dependencias nuevas.

## Pendiente siguiente desarrollo

Diseñar **puntos por acciones y recompensas para usuarios**: fuentes de puntos, límites contra abuso, historial auditable, niveles y recompensas. No forma parte de este cambio; requiere decisión de producto y modelo propios.

## Referencias

- [ADR-018](../adr/ADR-018-tops-comunitarios-productos.md) y [ADR-017](../adr/ADR-017-catalogo-permanente.md)
- [Estado del proyecto](../../PROJECT_STATUS.md) y [deuda técnica](10-technical-debt.md)
