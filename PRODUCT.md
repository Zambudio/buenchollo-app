# BuenCholloTech

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Personas en España que buscan ofertas de tecnología, comparan productos y siguen categorías de interés. Usuarios registrados que guardan, comentan y votan. Pedro selecciona y administra el catálogo, los chollos y el blog.

## Product Purpose

Descubrir chollos tecnológicos verificados y seguir productos de interés aunque una oferta concreta termine. La web combina ofertas, catálogo permanente, comunidad y contenido editorial.

## Positioning

BuenCholloTech une el chollo puntual con una ficha persistente del producto y una selección tecnológica curada. Las URLs, votos y conversaciones del chollo permanecen cuando cambia el estado de la oferta.

## Operating Context

Web pública en Cloudflare Workers, API FastAPI en NAS y catálogo en PostgreSQL. El panel permite publicar chollos y administrar categorías; el blog aporta contenido editorial. Hay temas claro y oscuro y uso móvil y de escritorio.

## Capabilities and Constraints

- La web habla con la API; no consulta Supabase DB directamente. Auth con Supabase y Google OAuth.
- Las fichas de chollo y sus URLs ya son permanentes. Los listados de ofertas activas no incluyen las caducadas.
- El rediseño incluirá tarjetas horizontales, navegación visible, categorías explorables y una zona de tops por subcategoría con podio y puestos 4 a 10.
- Todos los productos con una oferta pública de cada categoría y subcategoría compiten automáticamente; los vinculados solo a borradores permanecen privados. Los usuarios registrados podrán votar productos en el top, con un voto positivo por usuario y producto que se puede retirar. Los empates priorizan oferta activa y después fecha de creación e ID.
- El sistema de puntos y recompensas queda pendiente para el siguiente desarrollo; no forma parte de este rediseño.
- La publicación requiere CI en verde y despliegue separado de la API del NAS cuando haya cambios de backend.

## Brand Commitments

Nombre BuenCholloTech y logo existente. El usuario señaló Chollómetro y Chollero como referencias de densidad útil, navegación y tarjetas horizontales, sin copiar su diseño literalmente.

## Evidence on Hand

Código y datos del catálogo permanente, chollos, categorías, votos y blog; capturas de ocho zonas de referencia aportadas por Pedro. El volumen actual de productos es todavía pequeño; los tops deben funcionar con menos de diez candidatos sin rellenar puestos ficticios.

## Product Principles

1. Mostrar primero información que ayude a decidir: producto, precio, tienda, estado de la oferta y participación.
2. Facilitar exploración entre ofertas, categorías, tops y blog mediante enlaces claros.
3. Conservar URLs estables y contenido útil que los buscadores puedan leer.
4. Dar a la comunidad acciones comprensibles y verificables, sin métricas inventadas.
