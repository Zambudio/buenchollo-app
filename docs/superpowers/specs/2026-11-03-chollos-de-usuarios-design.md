# Diseño: Chollos compartidos por usuarios (propuestas de la comunidad)

**Fecha**: 2026-11-03
**Estado**: Borrador (pendiente de aprobación de Pedro)
**Referencias de producto**: chollometro.com ("+ Publicar Chollo") y chollero.es ("+ Comparte")

## 1. Intención y por qué

Hasta ahora solo el admin publica chollos. Pedro quiere que **los usuarios registrados puedan compartir chollos** con la comunidad, como en Chollometro/Chollero, para que la web crezca con contenido de la comunidad, sin perder el control editorial (todo pasa por moderación) ni los ingresos por afiliación (los enlaces se sustituyen por los nuestros cuando se pueda).

Era el momento: la infraestructura que lo hace posible ya existe (registro email + Google, emails transaccionales por SMTP/Zoho con plantillas de marca, notificaciones in-app, previsualización de Amazon vía Creators API, detección de duplicados por ASIN).

**Éxito** = un usuario registrado pega un enlace, ve en segundos si ya está publicado, rellena (o ve autorrellenado si es Amazon) un formulario cómodo en móvil, añade imágenes sin fricción (incluido **pegar desde el portapapeles**), envía; Pedro recibe un email en su Gmail, revisa/edita/aprueba en el panel y el chollo sale publicado con nuestro enlace de afiliado y con "Compartido por @usuario"; el usuario recibe email + notificación.

## 2. Objetivos

1. Botón **"+ Publicar chollo"** en la cabecera, visible **también sin sesión**. Sin sesión → diálogo explicando que hay que registrarse para compartir chollos con la comunidad, con botones *Crear cuenta* / *Iniciar sesión* (tras el login se vuelve al flujo).
2. Flujo en dos pasos (como las referencias):
   - **Paso 1 — Enlace**: el usuario pega la URL; se comprueba si el chollo **ya existe** (publicado o en revisión).
   - **Paso 2 — Formulario**: datos del chollo. Si es Amazon, **autorrelleno** (título, precio, precio anterior, marca, descripción con las características, imágenes, fecha fin de la oferta si la hay). Otras tiendas: formulario vacío (salvo el enlace y la tienda detectada).
3. **Imágenes con mínima fricción**: importadas automáticamente de Amazon; además el usuario puede añadirlas por **URL**, **pegando (Ctrl/Cmd+V)** una imagen o una URL desde el portapapeles, **arrastrando** o **eligiendo archivo** (en móvil: galería/cámara). Reordenar y elegir portada.
4. **Moderación obligatoria**: nada se publica sin aprobación. Panel admin "Propuestas" con cola de pendientes, edición completa antes de aprobar, aprobar o rechazar con motivo.
5. **Aviso al admin por email** (Gmail personal de Pedro) en cada propuesta nueva, con enlace directo a la propuesta en el panel.
6. **Sustitución de enlaces de afiliado**: Amazon (amazon.es y acortadores) → enlace limpio con nuestro tag. Arquitectura extensible para añadir más tiendas/redes sin tocar el flujo.
7. Al aprobar: publicación en la web; check **"Publicar también en Telegram"** que reutiliza el flujo de Telegram existente.
8. Autoría pública: **"Compartido por @usuario"** (avatar + username) en la **ficha y en la tarjeta** de los chollos de la comunidad.
9. Aviso al usuario al aprobar/rechazar: **email + notificación web** (campanita). El rechazo incluye el motivo.
10. Panel del usuario **"Mis chollos"**: sus propuestas con estado (en revisión / publicado / rechazado + motivo), enlace al chollo publicado y opción de retirar una propuesta pendiente.
11. Campos extra decididos por Pedro: **código de descuento**, **gastos de envío**, **fecha de inicio**.

## 3. No objetivos (por ahora)

- Autorrelleno e importación de imágenes de tiendas distintas de Amazon (se diseñará extensible, pero solo se implementa Amazon).
- Afiliación de tiendas distintas de Amazon (la arquitectura lo permite; se añadirán una a una).
- Edición de una propuesta por el usuario tras enviarla (solo puede retirarla y volver a enviarla).
- Gamificación (puntos, niveles, rankings), comentarios en propuestas, moderación por la comunidad.
- Publicación automática sin moderación para usuarios "de confianza".
- Generación de copy con IA en el formulario del usuario (coste y latencia; el admin puede editar el texto al aprobar).

## 4. Anti-objetivos (fallaría aunque "funcione")

- Que un chollo **no aprobado** sea visible públicamente por cualquier vía (URL directa, listados, alertas, sitemap, Telegram, triggers de BD).
- Que se publique un enlace de Amazon con el **tag de afiliado de otro**.
- Que el bucket de imágenes quede abierto a escritura de cualquier usuario o que se puedan subir ficheros que no sean imágenes válidas.
- Que el backend descargue URLs internas (SSRF) al importar imágenes por URL.
- Que un usuario pueda inundar la cola (spam) o el buzón de Pedro.
- Romper el flujo actual del admin (`/admin/chollos`, autofill Amazon, Telegram, chollos programados).
- Una UI que en móvil desborde o sea incómoda (regla mobile-first del proyecto).

## 5. Restricciones

- Arquitectura vigente: monolito modular FastAPI, `api → application → domain ← infrastructure` (ADR-001), frontend solo habla con la API (ADR-002), SQLAlchemy async + PgBouncer (`statement_cache_size=0`), UUID `Uuid(as_uuid=False)`.
- Migraciones con Alembic (`YYYYMMDDHHMMSS_slug.py`, revision = timestamp). **Dev y prod comparten la misma BD de Supabase**: toda migración debe ser **aditiva y compatible hacia atrás** (el código actual de producción debe seguir funcionando con el esquema nuevo).
- Trabajo en `develop`; `main` solo por merge con CI verde y bajo petición de Pedro.
- Sin servicios externos de pago nuevos.
- Tests sin dependencias externas reales (mocks de Amazon, SMTP, Storage).

## 6. Diseño

### 6.1 Modelo de datos

**Tabla nueva `deal_submissions`** (las propuestas viven **fuera** de `deals`). Motivo: `GET /deals/{slug}` no filtra por estado, hay trigger + pg_cron que publican por estado, `AlertMatcher` se dispara en cada create/update y el limpiador borra caducados. Meter "pendiente" en `deals` obligaría a blindar todos esos caminos; una tabla aparte hace imposible por construcción que una propuesta se filtre (anti-objetivo nº1). Al aprobar se crea el `Deal` mediante `DealService` existente.

Columnas:

| Columna | Tipo | Notas |
|---|---|---|
| `id` | uuid PK | |
| `user_id` | uuid FK `profiles.user_id` ON DELETE CASCADE | autor |
| `status` | varchar(16) + CHECK (`pending`,`approved`,`rejected`,`withdrawn`) | sin enum de Postgres (evita `ALTER TYPE`) |
| `original_url` | text | tal cual la pegó el usuario |
| `canonical_url` | text | clave de duplicados (§6.3) |
| `affiliate_url` | text | enlace ya reescrito (§6.4) |
| `asin` | varchar(16) null | si es Amazon |
| `store_id` | uuid FK stores null | tienda detectada por dominio |
| `store_name` | varchar(80) null | si la tienda no existe en `stores` |
| `title` | varchar(200) | |
| `description` | text null | markdown plano (se renderiza con ReactMarkdown sin HTML) |
| `current_price` | numeric(10,2) | |
| `previous_price` | numeric(10,2) null | debe ser > `current_price` si se informa |
| `coupon_code` | varchar(64) null | |
| `shipping_info` | varchar(120) null | |
| `starts_at` / `expires_at` | timestamptz null | `expires_at > starts_at` |
| `category_id` / `subcategory_id` | uuid FK categories | categoría obligatoria |
| `image_url` | text null | portada |
| `images` | jsonb | lista (máx. 8) |
| `rejection_reason` | varchar(500) null | |
| `reviewed_by` / `reviewed_at` | uuid / timestamptz null | |
| `deal_id` | uuid FK deals ON DELETE SET NULL | deal creado al aprobar |
| `created_at` / `updated_at` | timestamptz | |

Índices: `(status, created_at)`, `(user_id, created_at)`, y **dos índices únicos parciales** `WHERE status='pending'` sobre `asin` y sobre `canonical_url` → dos usuarios no pueden tener a la vez en cola el mismo producto (protege también ante carreras).

RLS: tabla con RLS activada **sin políticas** (solo accede el backend con service role, igual que el resto — ADR-006).

**Cambios aditivos en `deals`**:
- `coupon_code varchar(64) null` — se muestra en la ficha con botón copiar (y también se puede usar desde el formulario admin).
- `canonical_url text null` + índice — clave de duplicados para tiendas sin ASIN. `DealService` lo rellena al crear/actualizar. Script one-off de backfill para los deals existentes.
- `source = 'community'` (columna existente) identifica los chollos de la comunidad; `created_by` = el usuario autor. Solo cuando `source='community'` se muestra la autoría (los chollos del admin no muestran autor).
- **Unicidad de ASIN solo entre chollos vivos** (decisión de Pedro: un producto que vuelve a estar de oferta es un chollo **nuevo**, con sus propios votos, comentarios y autor). El índice `uq_deals_external_id` (hoy único sobre todo `external_id` no nulo) se recrea como único parcial `WHERE external_id IS NOT NULL AND status IN ('active','scheduled','draft')`, en la misma migración (crear el nuevo antes de borrar el antiguo, en transacción). Es más permisivo que el actual, así que el código de producción sigue funcionando. `DealService._check_external_id_unique` pasa a mirar solo esos estados (beneficio colateral: el admin también puede republicar un producto caducado). El flujo admin de "sobrescribir el existente" ante 409 no cambia. El slug del deal nuevo no puede colisionar con el del antiguo (`auto_slug` debe garantizar unicidad).
- `starts_at` del usuario se mapea a `status='scheduled'` + `scheduled_for` si es futura (el trigger existente lo activará solo).

### 6.2 Backend — módulo nuevo `app/modules/submissions/`

```
submissions/
├── domain/        models.py (DealSubmission), exceptions.py, rules.py (límites, validaciones puras)
├── application/   check_link.py, create_submission.py, review_submission.py (approve/reject),
│                  user_submissions.py (listar/retirar), notifier.py (orquesta emails + notificaciones)
├── infrastructure/repository.py, image_ingestor.py (descarga/valida/re-codifica/sube)
└── api/           router.py (usuario), admin_router.py, schemas.py
```

Módulo transversal nuevo `app/modules/affiliates/` (dominio puro, sin I/O salvo resolución de acortadores ya existente): canonicalización de URLs y reescritura de enlaces de afiliado (§6.3–6.4). Lo usan `submissions` y `deals`.

**Endpoints de usuario** (todos con `get_current_user`; además exigen perfil completo — `needs_onboarding == false` — porque la autoría usa el username):

| Método | Ruta | Qué hace | Límite |
|---|---|---|---|
| POST | `/v1/submissions/check-link` | `{url}` → canonicaliza, detecta tienda, busca duplicados (deal activo/programado o propuesta pendiente). Si es Amazon y no hay duplicado, devuelve `prefill` (datos de Creators API **sin IA**). | 20/min |
| POST | `/v1/submissions` | Crea propuesta `pending`. Revalida duplicados, reescribe enlace, valida reglas. Encola email al admin (BackgroundTask). | 10/min + reglas §6.6 |
| GET | `/v1/submissions/mine` | Lista paginada de sus propuestas. | |
| DELETE | `/v1/submissions/{id}` | Retira una propuesta **pending** propia (`withdrawn`). | |
| POST | `/v1/submissions/images` | `multipart/form-data` (archivo, también el blob pegado del portapapeles). Devuelve URL pública. | 30/min |
| POST | `/v1/submissions/images/from-url` | `{url}` → el backend la descarga y la trata igual que un archivo. | 30/min |

**Endpoints admin** (`require_admin`, todos con `audit_log`):

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/v1/admin/submissions?status=` | Cola paginada (por defecto `pending`, más antiguas primero) + autor. |
| GET | `/v1/admin/submissions/count` | Nº de pendientes (badge del sidebar). |
| GET | `/v1/admin/submissions/{id}` | Detalle. |
| POST | `/v1/admin/submissions/{id}/approve` | Body = payload final del deal (mismo esquema que `DealCreate`, editado por el admin). Crea el deal con `source='community'`, `created_by=autor`, marca `approved`, guarda `deal_id`. Devuelve el deal (el frontend lo usa para Telegram). |
| POST | `/v1/admin/submissions/{id}/reject` | `{reason}` obligatorio. |

Aprobar/rechazar solo desde `pending` (si no → 409). La aprobación es atómica (deal + propuesta en la misma transacción); si entre tanto ya se publicó el mismo ASIN → 409 `DUPLICATE_DEAL` reutilizando el error existente.

**Prefill de Amazon**: se reutiliza `AmazonProductClient` directamente (Creators API: título, marca, precios, descuento, imágenes, `expires_at`, características → descripción). **No** se usa `PreviewProductFromUrlUseCase` porque mete enriquecimiento IA (coste/latencia por usuario). El endpoint público existente `POST /v1/products/preview-from-url` **no se toca** en este trabajo (queda anotado como deuda: no tiene auth).

### 6.3 Detección de duplicados

`canonicalize(url) -> CanonicalLink(canonical_url, host, asin|None)`:
- Solo `http/https`, longitud ≤ 2048. Host en minúsculas sin `www.`, sin fragmento, sin parámetros de tracking (`utm_*`, `fbclid`, `gclid`, `ref`, `tag`, `ascsubtag`, etc.) y con barra final normalizada.
- Amazon: se resuelven acortadores (`amzn.to`, `amzn.eu`, `a.co`…) con la resolución SSRF-safe que ya existe en `extract_asin_from_url`, y la forma canónica es `https://www.amazon.es/dp/{ASIN}`.

Resultado de `check-link`:
- **Deal `active`** con el mismo ASIN (o la misma `canonical_url`) → "Este chollo ya está publicado", con su tarjeta y enlace para votarlo. No se puede continuar.
- **Deal `scheduled` o `draft`** → "Este chollo ya está preparado y se publicará pronto" (sin enlace, no es público). No se puede continuar.
- **Propuesta `pending`** de cualquier usuario → "Este chollo ya está en revisión". No se puede continuar.
- Deal **expirado** → se permite (los chollos se repiten), avisando de que ya se publicó antes.
- Si no → se continúa (con `prefill` si es Amazon).

### 6.4 Reescritura de enlaces de afiliado

Registro de reescritores por tienda (patrón estrategia, como `TASK_HANDLERS` en tareas programadas):

```python
class AffiliateRewriter(Protocol):
    def matches(self, link: CanonicalLink) -> bool: ...
    def rewrite(self, link: CanonicalLink) -> str: ...
```

- `AmazonRewriter`: `amazon.es` → `https://www.amazon.es/dp/{ASIN}?tag={AMAZON_AFFILIATE_TAG}` (elimina cualquier tag ajeno). Otros marketplaces de Amazon (`.com`, `.de`…) **no** se reescriben (nuestro tag es de `.es`); se marcan para que el admin lo vea.
- Fallback: URL limpia de parámetros de tracking. Si el enlace lleva parámetros de afiliado conocidos de otras redes (p. ej. `aff_*`, `affiliate`, `clickref`), se eliminan y se marca en la propuesta para que el admin lo revise.
- Añadir una tienda nueva = añadir una clase al registro (y, si aplica, su `affiliate_id`/plantilla en `stores`).

Se aplica al crear la propuesta y **otra vez al aprobar** (por si el admin edita el enlace).

### 6.5 Imágenes

- Amazon: se usan las URLs del CDN de Amazon (hotlink, como hoy en el admin).
- Resto (archivo, portapapeles, arrastrar, URL): **todo pasa por el backend** (`ImageIngestor`), que:
  1. Descarga (si es URL) con `httpx`: solo `http/https`, bloqueo de IPs privadas/loopback/link-local y metadatos cloud (reutilizando el comprobador SSRF existente), sin redirecciones a hosts privados, timeout 10 s, **máx. 5 MB leyendo en streaming**.
  2. Valida que es imagen real con **Pillow** (no por extensión ni Content-Type), formatos JPEG/PNG/WebP/GIF (primer frame)/AVIF si Pillow lo soporta; rechaza > 40 MP (bomba de descompresión).
  3. Re-codifica a **WebP**, lado mayor ≤ 1600 px, sin EXIF/metadatos.
  4. Sube a Supabase Storage bucket `deal-images` en `submissions/{user_id}/{uuid}.webp` con la service role del backend.
- Motivo: el bucket hoy solo admite escritura de admins; abrirlo a usuarios dejaría subir cualquier cosa. Pasar por backend da validación real, imágenes ligeras y homogéneas, y no requiere cambiar políticas del bucket. Se documenta como **ADR-015** (excepción inversa a "Storage directo desde el frontend").
- Límite: 8 imágenes por propuesta.
- Frontend: zona de imágenes que escucha `paste` (imagen → sube archivo; texto con URL de imagen → `from-url`), botón "Pegar" con `navigator.clipboard.read()` donde el navegador lo soporte, drag & drop, selector de archivo (`accept="image/*"`, en móvil abre galería/cámara), campo URL. Miniaturas con estado de subida, reordenar, elegir portada, quitar.
- Huérfanas (imágenes subidas de propuestas nunca enviadas): fuera de alcance; se anota como deuda técnica de bajo impacto.

### 6.6 Antiabuso

- Rate limits por IP (slowapi, tabla §6.2).
- Reglas de dominio por usuario: **máx. 5 propuestas pendientes** a la vez y **máx. 15 propuestas en 24 h** → 429 con mensaje claro.
- Validación estricta en la frontera (Pydantic): longitudes, precios > 0 y `previous_price > current_price`, fechas coherentes, URLs http(s), categorías existentes.
- Email al admin: uno por propuesta (con los límites anteriores el máximo teórico es acotado). Si el SMTP falla, la propuesta se guarda igual (el email es best-effort y se registra el error en logs).

### 6.7 Notificaciones y emails

- Config nueva: `ADMIN_NOTIFICATION_EMAIL` (en `.env` del NAS = Gmail de Pedro). Vacía → no se envía (dev).
- Plantillas Jinja2 nuevas con el layout de marca existente: `submission_admin` (nueva propuesta: título, precio, tienda, autor, miniatura, botón "Revisar en el panel"), `submission_approved` (enlace al chollo publicado), `submission_rejected` (motivo).
- Notificaciones in-app (tabla `notifications` existente) tipos `submission_approved` (con `deal_id`/`link_url`) y `submission_rejected` (link a "Mis chollos").
- Envíos en `BackgroundTasks` tras confirmar la transacción.

### 6.8 Frontend

- **Cabecera** (`Header.tsx`): botón destacado "+ Publicar chollo" (escritorio: junto a los iconos; móvil: compacto con icono "+" y también en el menú). Sin sesión → diálogo de registro. Con sesión pero perfil incompleto → al onboarding existente.
- **Ruta `/publicar`** (TanStack file route), wizard de 2 pasos, mobile-first:
  - Paso 1: campo enlace grande + "Comprobar". Estados: comprobando / ya publicado (tarjeta del deal) / en revisión / anteriormente publicado (aviso) / OK.
  - Paso 2: formulario (título, precio, precio anterior con % calculado en vivo, código de descuento, gastos de envío, tienda —autodetectada o texto—, categoría/subcategoría, fecha inicio/fin, descripción, imágenes). Vista previa de la tarjeta tal como se verá. Envío → pantalla de éxito ("Lo revisaremos pronto, te avisaremos por email").
  - Validación con zod (coherente con las reglas del backend), errores en línea.
- **"Mis chollos"**: nueva pestaña en `/perfil?tab=chollos` (patrón de pestañas existente) con lista y estados; retirar pendientes.
- **Autoría**: `DealCard` y ficha muestran "Compartido por @username" con avatar cuando `source==='community'`. El backend añade `author {username, display_name, avatar_url}` a las respuestas de tarjeta/ficha (carga en la misma consulta, sin N+1).
- **Código de descuento**: en la ficha, bloque con el código y botón copiar.
- **Admin**: nueva entrada "Propuestas" en el sidebar con badge de pendientes; ruta `admin.propuestas.tsx` con la cola (más antiguas primero) y detalle que **reutiliza `DealFormPanel`** precargado desde la propuesta (el admin puede editar todo, cambiar categoría, imágenes, enlace…). Muestra avisos (enlace no afiliable, marketplace extranjero, deal expirado previo). Acciones: **Aprobar** (con check "Publicar también en Telegram" → tras aprobar abre el panel de Telegram existente precargado, mismo flujo que `admin.chollos`) y **Rechazar** (motivos predefinidos + texto libre).
- Toda llamada HTTP vía `apiClient`. Hay que permitir `FormData` (hoy fuerza `Content-Type: application/json`): no fijar el header cuando el body es `FormData`.

### 6.9 Testing y validación

- **Backend (pytest)**: unitarios del dominio (`canonicalize`, reescritores, reglas), casos de uso con repositorios falsos, `ImageIngestor` con imágenes generadas con Pillow (válida, corrupta, bomba, SVG/HTML disfrazado, > 5 MB, SSRF a IPs privadas), API con `dependency_overrides` (auth, admin, límites, 409/429), aprobación atómica y no-filtración (una propuesta nunca aparece en `/deals/*`).
- **Frontend (Vitest + Testing Library)**: wizard (estados del paso 1, prefill, validación), zona de imágenes (paste de imagen y de URL, drop, reordenar), botón de cabecera sin sesión, pestaña Mis chollos, pantalla admin.
- **E2E (Playwright, API mockeada)**: flujo usuario completo; flujo admin aprobar/rechazar.
- **Pruebas reales en local** contra la API levantada (Amazon real con un producto, subida real a Storage, email real a la cuenta de Pedro) y **en navegador** (escritorio y móvil).
- **Estrés**: script de carga concurrente (`httpx` asyncio) contra la API local: `check-link`, creación concurrente del mismo producto (debe quedar exactamente 1 pendiente), subidas simultáneas, y verificación de que los rate limits y las reglas por usuario responden bien bajo carga.
- CI en verde (backend + frontend) antes de proponer el merge a `main`.

### 6.10 Documentación

- ADR-015 (ingesta de imágenes por backend) y ADR-016 (propuestas en tabla separada + registro de reescritores de afiliado).
- `docs/project/*` (endpoints, configuración `ADMIN_NOTIFICATION_EMAIL`, flujo de moderación), `PROJECT_STATUS.md`, `10-technical-debt.md` (preview sin auth, imágenes huérfanas, digest nocturno roto detectado en el análisis).
- Ficha en OBSIDIAN VAULT según `SCHEMA.md` (patrón transferible: moderación de contenido de usuario + ingesta segura de imágenes + reescritura de afiliados).

## 7. Decisiones de Pedro

- Telegram al aprobar: **opcional** mediante check en la moderación.
- Autoría visible: **sí, en ficha y tarjeta**.
- Aviso al usuario: **email + notificación web**.
- Campos extra: **código de descuento, gastos de envío, fecha de inicio**.
- Destino del aviso al admin: su **Gmail personal** (vía `ADMIN_NOTIFICATION_EMAIL`).
- Afiliación: **de momento solo Amazon**, pensando en ampliar.
- Producto ya publicado y caducado que se vuelve a compartir: **chollo nuevo** (unicidad de ASIN solo entre chollos vivos).
- Autorrelleno e importación de imágenes: **solo Amazon** por ahora.

## 8. Decisiones del diseñador (revisables)

- Propuestas en tabla separada en vez de estado nuevo en `deals`.
- Ingesta de imágenes por backend (Pillow, WebP ≤1600 px) en lugar de subida directa al bucket.
- Sin IA en el autorrelleno del usuario.
- Límites: 5 pendientes / 15 al día por usuario, 8 imágenes, 5 MB.
- Exigir perfil completo (username) para proponer.
- Deal expirado previo no bloquea; publicado/programado/borrador/pendiente sí.
- Solo `amazon.es` se reescribe con nuestro tag.
- Texto del botón: "+ Publicar chollo".
- "Mis chollos" como pestaña del perfil.

## 9. Lo que queda al constructor

Orden de tareas, nombres internos, diseño visual concreto dentro del sistema de diseño actual (tokens `surface-*`, shadcn), estructura de los tests y del script de estrés.
