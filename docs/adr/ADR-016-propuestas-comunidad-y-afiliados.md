# ADR-016 — Propuestas de comunidad en tabla separada y registro de reescritores de afiliado

## Estado

**Aceptado** · 2026-11-04 · decisión tomada al implementar las propuestas de chollos de
usuarios ([spec](../superpowers/specs/2026-11-03-chollos-de-usuarios-design.md)).

## Contexto

Los usuarios registrados pueden proponer chollos que el admin modera antes de publicar. Dos
decisiones eran difíciles de revertir: dónde viven las propuestas mientras no están
aprobadas y cómo se garantiza que **ningún enlace publicado conserve un tag de afiliado
ajeno** (o ninguno) cuando lo ha pegado un usuario. La BD es compartida entre dev y prod,
así que cualquier cambio de esquema debía además ser aditivo.

## Decisión

1. **Tabla separada `deal_submissions`** (módulo `submissions`), no filas de `deals` con un
   estado "pendiente". Una propuesta solo se convierte en `deals` al aprobarla:
   `ReviewSubmissionUseCase` reutiliza `DealService`, así que alertas, slug y reglas de
   duplicado son las de siempre. Estados: `pending`, `approved`, `rejected`, `withdrawn`.
   Índices únicos parciales impiden dos propuestas pendientes del mismo producto
   (ASIN / URL canónica). `deals` solo gana dos columnas nullable (`canonical_url`,
   `coupon_code`); el autor sale del `created_by` y `source="community"` ya existentes.
   Migración `20261103140000`, aditiva y con RLS activado.
2. **Registro de reescritores de afiliado** (módulo `affiliates`, dominio puro):
   `extract_url` → `canonicalize` → `rewrite_affiliate_link`. Cada tienda es un reescritor:
   `AmazonEsRewriter` fija el `?tag=` propio y elimina el ajeno; `AmazonOtherRewriter` deja
   limpios los enlaces de otros Amazon; el resto se limpia y se marca `not_affiliable`.
   Añadir una tienda es añadir un reescritor. Solo se reescribe `amazon.es`.
3. **Se rechazan los acortadores genéricos** (bit.ly, tinyurl, t.co, goo.gl, ebay.us,
   s.click.aliexpress.com, etc.) con 400 "Pega el enlace directo del producto": no se
   pueden verificar sin resolverlos y permitirían saltarse el reescritor. Los acortadores
   propios de Amazon (`amzn.to`, `amzn.eu`, `a.co`, `link.amazon`) sí se resuelven.
4. **Commit explícito antes de las tareas de fondo**: con FastAPI ≥ 0.118 las
   `BackgroundTasks` se ejecutan antes del cierre de la dependencia `get_db` (que es quien
   hace el commit), y el notificador no veía la fila nueva. Los endpoints que programan
   notificaciones hacen `await db.commit()` antes de `add_task`, y el notificador abre su
   propia sesión (`AsyncSessionLocal`). Es una desviación documentada de "solo `get_db`
   hace commit".
5. **Antiabuso**: máx. 5 propuestas pendientes por usuario y 15 por 24 h, perfil completo
   obligatorio y rate limit por usuario en los endpoints de propuestas (detalle en
   [`07-security.md`](../project/07-security.md); imágenes en [ADR-015](ADR-015-ingesta-imagenes-backend.md)).

## Motivo

Separar la moderación del catálogo público garantiza por construcción que una propuesta no
aprobada no puede filtrarse a listados, buscador, sitemap, alertas ni Telegram, sin tocar
ninguna consulta existente de `deals`. El registro de reescritores mantiene la regla de
afiliación (dinero) en el dominio, testeable sin red y extensible.

## Alternativas consideradas

- **`deals.status = 'pending_review'`**: menos tablas, pero obliga a filtrar el estado en
  todas las consultas públicas (riesgo de fuga) y mezcla campos de moderación con el catálogo.
- **Reescritura en el frontend**: no es fiable; el servidor debe ser quien fija el tag.
- **Permitir acortadores y resolverlos**: añade SSRF, latencia y reglas por servicio sin
  beneficio claro; pedir el enlace directo es barato para el usuario.
- **Notificar desde el scheduler en vez de commit explícito**: más piezas móviles; el
  commit explícito es una línea fácil de testear.

## Consecuencias

- El admin tiene una cola propia (`/admin/propuestas`). Aprobar crea el chollo con
  `source=community` y notifica al autor (correo + notificación in-app; el texto distingue
  publicado / programado / borrador).
- La cuota "comprobar y luego insertar" no es atómica (acotada por los índices únicos
  parciales) — TD-29.
- La migración es aditiva: revertir el código no requiere tocar la BD.
- Los chollos anteriores necesitan `canonical_url`: `scripts/backfill_canonical_urls.py`
  (idempotente; se re-ejecuta tras el despliegue).
- Aprobar borra los chollos **expirados** del mismo producto (comportamiento del spec).
