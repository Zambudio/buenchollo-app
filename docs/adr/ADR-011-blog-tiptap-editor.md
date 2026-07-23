# ADR-011 — Editor de blog con Tiptap y JSON como fuente de verdad

## Estado

**Aceptado** · 2026-07-22 · decisión tomada al implementar el CMS de blog
(`feature/blog-cms`).

## Contexto

BuenChollo necesita una sección de blog (guías de compra, comparativas,
recomendaciones con enlaces de afiliado) para captar tráfico orgánico. El
contenido necesita algo más que texto plano: encabezados estructurados
(para tabla de contenidos y SEO), imágenes con atributos (alt, alineación,
ancho), tablas, bloques informativos (aviso/consejo/advertencia/veredicto)
y, sobre todo, un **bloque de producto recomendado** con dos modos (chollo
existente por `deal_id`, o producto manual con enlace de afiliado) que debe
validarse en el backend antes de publicarse.

El proyecto ya usa `react-markdown` + `@tailwindcss/typography` en otras
partes de la web, pero Markdown no modela de forma nativa nodos
estructurados con atributos propios (el bloque de producto, los
`callout`) sin recurrir a sintaxis inventada o HTML embebido — justo lo
que se quiere evitar por seguridad (nunca aceptar HTML arbitrario del
cliente, ver `domain/content.py`).

## Decisión

Usar **Tiptap** (`@tiptap/react`, `@tiptap/pm`, `@tiptap/starter-kit`,
extensiones oficiales de tabla/imagen/alineación/highlight/color/enlace/
listas de tareas) como editor administrativo, con:

- El **documento JSON de Tiptap como fuente de verdad canónica**
  (`BlogPost.content`, columna `JSONB`). Nunca se persiste ni se acepta
  HTML arbitrario del cliente.
- `immediatelyRender: false` obligatorio (la web usa SSR con TanStack
  Start; sin este flag Tiptap intenta renderizar antes de la hidratación).
- El editor es **exclusivo de rutas admin** — nunca se carga en el bundle
  público. La parte pública renderiza el JSON con un renderer estático
  controlado (`@tiptap/static-renderer` o un renderer propio que solo
  contempla los nodos/marcas soportados), no con `dangerouslySetInnerHTML`.
- Un nodo personalizado `productRecommendation` (modos `deal`/`manual`) y
  un nodo `callout` (con `attrs.variant` para info/consejo/advertencia/
  veredicto, en vez de cuatro tipos de nodo distintos).
- El backend **no confía en el JSON recibido**: `domain/content.py` valida
  recursivamente tipos de nodo, marcas, protocolos de URL, paleta de
  colores y atributos del bloque de producto antes de guardar o publicar.

## Consecuencias

**Positivas**
- Estructura real para TOC (H2/H3), tiempo de lectura, detección de
  bloques de afiliación y resolución en lote de `deal_id` — todo lógica
  pura y testeable sobre el JSON, sin parsear HTML.
- Superficie de ataque acotada: solo se acepta lo que el validador
  reconoce explícitamente (allowlist, no denylist).

**Negativas / trade-offs asumidos**
- Nueva dependencia no trivial (Tiptap/ProseMirror) que no existía en el
  proyecto; aumenta el bundle admin (mitigado con lazy loading del editor,
  fuera del bundle público).
- El validador de contenido (`content.py`) debe mantenerse en sincronía
  manual con los nodos/marcas que exponga el editor: añadir una extensión
  de Tiptap sin actualizar `ALLOWED_NODE_TYPES`/`ALLOWED_MARKS` hace que el
  backend rechace el contenido al publicar (fail-safe intencionado, pero
  requiere disciplina al tocar el editor).

## Alternativas consideradas

- **Markdown + `react-markdown`** (ya presente en el proyecto): cero
  dependencias nuevas, pero exige inventar sintaxis o front-matter para el
  bloque de producto y los `callout`, perdiendo la validación estructural
  por nodo/atributo que sí da un documento JSON tipado.
- **Editor HTML libre (contentEditable / TinyMCE) con sanitización**:
  requiere sanitizar HTML arbitrario en el servidor (mayor superficie de
  XSS) y no da una fuente de verdad estructurada para TOC/lectura/bloques
  de afiliado sin parsear el propio HTML. Descartada.
