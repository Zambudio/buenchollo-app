# 🔎 13 · SEO y visibilidad en buscadores con IA

> **TL;DR** · Cómo está preparada la web para posicionar búsquedas de «chollos de
> tecnología» en Google y Bing y para que los asistentes de IA (ChatGPT, Claude,
> Perplexity, Gemini) la entiendan y la citen. Auditoría y cambios del
> 2026-11-18, qué mantener y qué queda pendiente.

---

## 1. Punto de partida (auditoría del 2026-11-18)

| Problema | Impacto |
|---|---|
| Fichas, artículos y categorías inexistentes respondían **HTTP 200** con «no encontrado» (*soft 404*); una caída de la API se servía igual | Google indexa páginas vacías y puede sustituir una URL buena por una vacía |
| El sitemap publicaba las **91 categorías**, muchas sin ningún chollo (p. ej. *Portátiles*, *Energía*) | Contenido escaso: rebaja la valoración del sitio entero |
| Ninguna categoría tenía texto propio; títulos genéricos («Chollos de X · BuenChollo Tech») | Las páginas que deben posicionar «chollos de auriculares» no aportaban nada que posicionar |
| Paginación de la portada con botones sin `href`; las páginas 2+ apuntaban su canonical a la portada | Los buscadores no descubrían los chollos antiguos |
| Chollos caducados con precio en el `<title>` y en el JSON-LD aunque la página no lo mostraba | Riesgo de penalización por discrepancia de precio |
| Sin `twitter:*` en fichas y categorías; página de contacto sin `<head>` propio | Tarjetas pobres al compartir; página sin título ni descripción |
| Pie (enlaces legales y de navegación) fuera del HTML del servidor; listado del blog solo en el navegador | Enlaces internos invisibles para el rastreador |
| `llms.txt` estático y sin datos; `robots.txt` sin mención a los bots de IA; sin feed de chollos | Los asistentes de IA no tenían una fuente fiable y actual |
| Logo y favicon de **588 KB**; Google Fonts externo y bloqueante | Peor LCP en móvil (Core Web Vitals) y envío de la IP del visitante a Google |
| Fechas renderizadas en UTC en el servidor y en hora local en el navegador | Desajuste de hidratación y hora de fin errónea en el HTML |

---

## 2. Qué se implementó

### 2.1 SEO técnico

- **Códigos de estado correctos.** Los loaders lanzan `notFound()` ante un 404 de la
  API (respuesta **404** con `noindex`) y propagan cualquier otro fallo como error
  temporal (**5xx** con `noindex`), para que el buscador reintente en vez de indexar
  una página vacía. La pantalla de error está en español.
- **Cabecera común** (`src/lib/seo/head.ts` → `pageHead`): cada página indexable
  publica título, descripción (≤ 158 caracteres, cortada en palabra), `canonical`,
  `robots` (`max-image-preview:large, max-snippet:-1`), Open Graph y Twitter. Las
  páginas privadas usan `noindex`.
- **Canonical y paginación.** `/?page=N` y `/blog?page=N` tienen canonical propio y
  enlaces `href` reales (con `rel="prev"`/`"next"`) que siguen navegando sin
  recargar; los cambios de orden (`?sort=`) apuntan al canonical sin orden; las
  búsquedas y filtros del blog son `noindex`.
- **Sitemap** (`/sitemap.xml`, `src/lib/sitemap.ts`): solo categorías con chollos y
  con la fecha de su chollo más reciente, chollos con su imagen (sitemap de
  imágenes), páginas fijas sin el buscador `/explorar` (es `noindex`), y fechas
  vacías que ya no rompen el bloque del blog. Requiere que `/v1/deals/sitemap`
  devuelva `title`, `image_url`, `category_id` y `subcategory_id`.
- **`robots.txt`**: bloquea solo las zonas privadas y nombra explícitamente a los
  buscadores y bots de IA (ver § 2.4).

### 2.2 Contenido y palabras clave

| Página | Título (patrón) | Objetivo |
|---|---|---|
| Portada | «Chollos de tecnología hoy: las mejores ofertas y descuentos» | *chollos tecnología*, *ofertas tecnología hoy* |
| Categoría | «Chollos de {categoría} hoy: ofertas y descuentos» | *chollos {categoría}*, *ofertas {categoría}* |
| Ficha activa | «Chollo {producto} por {precio} (-{d} %)» | *chollo {producto}*, *{producto} oferta* |
| Ficha terminada | «{producto}: oferta terminada» | Conservar la URL sin anunciar un precio que no se muestra |
| Blog | «Blog de tecnología y guías de compra» | Búsquedas informativas que alimentan las transaccionales |

- **Categorías**: H1 «Chollos de {categoría}» y una introducción propia y útil en las
  principales (`CATEGORY_INTROS` en `src/lib/seo/category.ts`); las subcategorías
  usan una plantilla. Una categoría sin chollos ni productos destacados queda en
  `noindex`.
- **Portada**: H1 con la palabra clave. Desde el 2026-11-21 sin bloque de preguntas
  frecuentes: quedaba mal al final del feed.
- **Preguntas frecuentes** (`/preguntas-frecuentes`, enlazada en el pie, en INFO): las
  preguntas de `SITE_FAQ` (`SiteFaq`), las mismas que se publican ahí como `FAQPage`.
  «Sobre nosotros» enlaza a ella en lugar de repetirlas.
- **Landings de campaña** (`/black-friday`, 2026-11-20): URL fija sin año, reutilizable cada edición para acumular autoridad; el año va en el título. Lista los chollos activos con al menos un 20 % de descuento y tiene FAQ visible con su `FAQPage`, `CollectionPage`, `BreadcrumbList` e `ItemList`. Está en el sitemap. Las fechas de cada edición se añaden en `src/lib/campaigns.ts`.
- **«Sobre nosotros»** (`/sobre-nosotros`): quién publica, cómo se seleccionan y
  verifican los chollos (revisión antes de publicar y comprobación diaria de precio y
  stock), transparencia sobre afiliación y contacto. Es la señal de confianza
  (E-E-A-T) que usan Google y los asistentes de IA para decidir a quién citar.
- **Pie siempre en el HTML** del servidor (plegado visualmente), con enlaces a blog,
  Telegram, «Sobre nosotros» y textos legales. El listado del blog se carga en el
  servidor.

### 2.3 Datos estructurados (schema.org, JSON-LD)

| Página | Nodos |
|---|---|
| Portada | `Organization`, `WebSite` (+ `SearchAction`), `ItemList` de chollos |
| Preguntas frecuentes | `CollectionPage`, `BreadcrumbList`, `FAQPage` |
| Ficha activa | `Product` + `Offer` (precio, moneda, disponibilidad, `priceValidUntil` solo si es futura, vendedor), `BreadcrumbList` |
| Ficha terminada | Solo `BreadcrumbList` (sin `Product` para no anunciar un precio que no se muestra) |
| Categoría | `CollectionPage`, `BreadcrumbList`, `ItemList` |
| Blog / artículo | `Blog` con sus artículos / `BlogPosting` (autor, editor, fechas, tiempo de lectura, palabras) + `BreadcrumbList` |
| Sobre nosotros, contacto | `AboutPage` + `Organization`, `ContactPage` |

Todos los nodos se enlazan por `@id` a una única `Organization`
(`https://buenchollotech.com/#organization`). Los datos estructurados se generan con
funciones puras y probadas en `src/lib/seo/` (cobertura ≥ 98 %).

### 2.4 Búsqueda con IA (GEO)

- **`/llms.txt`** (formato llmstxt.org), generado en cada petición con caché de una
  hora: qué es el sitio y cómo verifica los chollos, páginas clave, categorías con
  chollos, los **40 últimos chollos con precio, precio anterior, descuento y tienda**,
  guías del blog, preguntas frecuentes y contacto. Indica a los asistentes que enlacen
  siempre a la ficha, que muestra el precio vigente.
- **`robots.txt`** permite explícitamente `OAI-SearchBot`, `ChatGPT-User`, `GPTBot`,
  `PerplexityBot`, `Perplexity-User`, `ClaudeBot`, `Claude-SearchBot`, `Claude-User`,
  `Google-Extended`, `Applebot-Extended`, `meta-externalagent` y `MistralAI-User`,
  además de los buscadores clásicos.
- **Feed RSS de chollos** (`/rss.xml`) y del blog (`/blog/rss.xml`), anunciados en el
  `<head>` de todas las páginas.
- **Contenido citable**: respuestas directas en la FAQ, metodología explícita en
  «Sobre nosotros», precios y descuentos en texto plano en el HTML del servidor.

### 2.5 Rendimiento (Core Web Vitals)

- Logo de la cabecera en WebP de 7 KB (antes PNG de 588 KB) con `width`/`height`;
  favicon de 32 y 192 px, icono de Apple de 180 px y `logo-512.png` optimizado.
- Fuentes **Space Grotesk** y **JetBrains Mono** variables alojadas en la propia web
  (`@fontsource-variable`, `font-display: swap`): sin peticiones a Google Fonts.
- Fechas formateadas con `timeZone: "Europe/Madrid"` (`TIME_ZONE` en
  `src/lib/format.ts`): el HTML del servidor coincide con el del navegador.

---

## 3. Cómo mantenerlo

- **Toda página pública nueva** declara su `head` con `pageHead(...)` y, si lista
  chollos o es un contenido propio, sus nodos de `src/lib/seo/schema.ts`. Las privadas
  usan `noindex`.
- **Un loader de página de detalle** lanza `notFound()` ante un 404 de la API y deja
  propagarse los demás errores; nunca devuelve datos vacíos con 200.
- **Textos de `site-content.ts`** (resumen y FAQ): la FAQ se muestra en
  `/preguntas-frecuentes` (y su `FAQPage`) y en `/llms.txt`; el resumen, en «Sobre
  nosotros» y en `/llms.txt`. Todo lo que dicen tiene que ser cierto en el producto.
- **Categorías nuevas**: añadir su introducción a `CATEGORY_INTROS` si es principal.
- **Despliegue**: si cambia el contrato de `/v1/deals/sitemap`, desplegar la API antes
  que la web.

## 4. Verificación

- Local, contra la API de producción: códigos 200/404 por tipo de página, una sola
  etiqueta de cada tipo en el `<head>`, canonical y robots correctos, JSON-LD por
  página y salida de `/sitemap.xml`, `/llms.txt` y `/rss.xml`.
- Tests: `src/lib/seo/*.test.ts` y `src/lib/sitemap.test.ts`; E2E con la API caída
  (error temporal con `noindex`).

## 5. Pendiente (requiere acceso del propietario)

| Acción | Por qué | Cómo |
|---|---|---|
| Dar de alta el dominio en **Google Search Console** y **Bing Webmaster Tools** y enviar `/sitemap.xml` | Ver indexación, errores y búsquedas reales; Bing alimenta a ChatGPT y Copilot | Verificación por DNS en Cloudflare (registro TXT) |
| Revisar en Search Console el informe de **páginas no indexadas** tras el despliegue | Confirmar que desaparecen los *soft 404* y que las categorías vacías salen del índice | Inspección de URL y validación de la corrección |
| Activar **IndexNow** en Cloudflare (*Crawler Hints*) | Bing y Yandex indexan los chollos nuevos en minutos | Panel de Cloudflare → Caching → Crawler Hints |
| Ampliar la FAQ y las introducciones de categoría con datos propios (p. ej. ahorro medio publicado) | Contenido único que los asistentes de IA citan | Editar `site-content.ts` y `category.ts` |
| Publicar guías de compra por categoría en el blog y enlazarlas desde cada categoría | Las búsquedas informativas («mejores auriculares calidad precio») son la mayor fuente de tráfico de un sitio de chollos | Editor del blog |

---

## Referencias

- Código: `buenchollo-web/src/lib/seo/`, `src/lib/sitemap.ts`, `src/routes/llms[.]txt.ts`,
  `src/routes/rss[.]xml.ts`, `public/robots.txt`.
- Auditoría general: [`12-auditoria-tecnica-2026-11.md`](12-auditoria-tecnica-2026-11.md) (AUD-07, AUD-08, AUD-15).
