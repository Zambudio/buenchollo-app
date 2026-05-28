# Plan de Hardening Arquitectónico — BuenChollo
*Plan vivo. Última actualización: 2026-05-27*

> **Contexto**: tras la auditoría arquitectónica del 2026-05-27 (alto cumplimiento
> con el módulo de Arquitectura del máster), se identificaron 10 áreas mejorables
> (ARQ-01 a ARQ-10). Este plan las aborda todas, ordenadas por dependencias
> lógicas. Objetivo: dejar BuenChollo en estado "producción real", no sólo
> entregable de TFM, porque el proyecto va a crecer.
>
> **Forma de trabajo**: una tarea = un commit. Por cada tarea: modificar →
> verificar (manual + tsc/pytest) → commit + push → marcar `[x]` → siguiente.

---

## Resumen de fases

| Fase | Bloque | Tareas | Estado |
|---|---|---:|:---:|
| **F1** | Documentación arquitectónica (5 ADRs + diagrama) | 6 | ✅ 6/6 |
| **F2** | Backend: fundamentos (migraciones, Alembic, excepciones, UserService) | 5 | ✅ 5/5 |
| **F3** | Producción ready (request_id, logging, rate limit, audit log, health) | 5 | 🟡 3/5 |
| **F4** | API: versionado `/v1` | 2 | ⬜ |
| **F5** | Frontend: features-based + TanStack Query + tipado total | 6 | ⬜ |
| **F6** | CI/CD y calidad continua | 3 | ⬜ |
| **F7** | Validación final y entrega | 3 | ⬜ |

**Total**: 30 tareas.

---

## FASE 1 — Documentación arquitectónica

> Por qué primero: sienta el "norte" antes de tocar código. Cero riesgo,
> aporta cimiento documental defendible. Cada ADR es ~1 página.

### 1.1 ADR-003 — Autenticación con Supabase Auth + JWT en backend
- [x] Creado `docs/adr/ADR-003-autenticacion-supabase-jwt.md` (2026-05-27).
- Contexto, decisión, consecuencias, alternativas descartadas, evolución.
- Documenta dependencia de Supabase como IdP y el plan de migración a otro.

### 1.2 ADR-004 — Persistencia con SQLAlchemy async + PgBouncer
- [x] Creado `docs/adr/ADR-004-persistencia-sqlalchemy-pgbouncer.md` (2026-05-27).
- Justifica `statement_cache_size=0`, `Uuid(as_uuid=False)`, async + asyncpg.
- Documenta convenciones de modelado, repos como única vía a la BD y plan
  de migración a Alembic (F2.2).

### 1.3 ADR-005 — Validación en doble frontera (Zod + Pydantic)
- [x] Creado `docs/adr/ADR-005-validacion-doble-frontera.md` (2026-05-27).
- Documenta defensa en profundidad, mensajes en cliente vs servidor,
  trade-off de duplicación y plan de evolución (generador OpenAPI→TS opcional).

### 1.4 ADR-006 — Hardening de RLS y service_role
- [x] Creado `docs/adr/ADR-006-rls-service-role.md` (2026-05-27).
- Documenta el incidente, el fix por migración versionada, la separación
  estricta `anon` (público, RLS aplica) / `service_role` (server-only,
  bypassa RLS), y procedimientos de auditoría y reaplicación.

### 1.5 ADR-007 — Inyección de dependencias con `Depends` de FastAPI
- [x] Creado `docs/adr/ADR-007-di-fastapi-depends.md` (2026-05-27).
- Composition root distribuido en factories `get_X`, scopes resueltos
  automáticamente, `app.dependency_overrides` para tests, convención
  para añadir módulos nuevos.

### 1.6 README arquitectónico + diagrama del sistema
- [x] `README.md` raíz reescrito (2026-05-27):
  - Diagrama Mermaid renderizable en GitHub (Browser → FastAPI →
    Postgres/Supabase + Amazon/OpenAI/Telegram).
  - Tabla de los 7 ADRs con estado.
  - "Filosofía arquitectónica" en 6 reglas inviolables.
  - Estructura de carpetas por módulo (backend) y referencia a la
    reorganización por features prevista en F5.
  - Links a toda la documentación viva: PROJECT_STATUS, PLAN_ARQUITECTURA,
    LAUNCH_CHECKLIST, ADRs.

---

## FASE 2 — Backend: fundamentos arquitectónicos

> Por qué ahora: dejar el backend en estado canónico antes de añadirle
> middleware, versionado y demás capas. Cambios mecánicos, bajo riesgo.

### 2.1 Mover migraciones SQL al backend
- [x] Movido `buenchollo-web/supabase/` → `buenchollo-api/supabase/` (2026-05-27).
  Decisión: mover el directorio completo (`migrations/`, `functions/`,
  `config.toml`) para mantener la simetría con `supabase init`. Las
  Edge Functions (`amazon-autofill`, `notify-telegram`) son legado en
  proceso de migración al backend Python (CLAUDE.md ya lo indica).
- [x] Actualizadas referencias en `PROJECT_STATUS.md`, `docs/adr/ADR-004`,
  `docs/adr/ADR-006`.
- [x] Comprobado: no había scripts ni configs apuntando a la ruta vieja.

### 2.2 Configurar Alembic en backend
- [x] `alembic/env.py` reescrito (2026-05-27): `include_object` filtra
  schemas externos (`auth.*`, `storage.*`) y tablas legacy no modeladas
  (`user_roles`, `import_logs`); `compare_type` y `compare_server_default`
  activados para autogenerate más preciso.
- [x] `app/core/base.py` ampliado con todos los modelos (alerts,
  notifications, comments, dealvote, favorite, commentvote).
- [x] Migración baseline `alembic/versions/20260527120000_baseline.py`
  vacía a propósito para marcar el punto donde SQL legacy y Alembic se
  encuentran. Listo para `alembic stamp head` en producción.
- [x] `buenchollo-api/MIGRATIONS.md` documenta setup inicial, flujo
  diario, reglas y troubleshooting.
- **Acción pendiente del operador** (una sola vez, en NAS y en local):
  ejecutar `alembic stamp head` para registrar la baseline como aplicada.

### 2.3 Excepciones de dominio + handler global (ARQ-03)
- [x] `app/core/exceptions.py` con jerarquía `DomainError` (raíz) →
  `NotFoundError` (404), `ForbiddenError` (403), `ConflictError` (409),
  `ValidationError` (400), `ServiceUnavailableError` (503).
- [x] Excepciones específicas en `<modulo>/domain/exceptions.py` para
  `deals` (DealNotFound), `comments` (CommentNotFound, NotCommentOwner,
  InvalidParentComment, InvalidVote), `alerts` (AlertNotFound),
  `categories` (CategoryNotFound), `stores` (StoreNotFound), `users`
  (ProfileNotFound). `products` reaprovecha sus excepciones existentes
  haciéndolas heredar de la jerarquía nueva.
- [x] `@app.exception_handler(DomainError)` en `main.py` mapea cada
  subtipo a su `http_status` con formato `{"detail": "..."}`.
- [x] Routers de `deals`, `comments`, `alerts`, `categories`, `stores`,
  `users` y `products` sustituyen `raise HTTPException(...)` por las
  excepciones de dominio correspondientes.
- [x] 4 tests nuevos en `test_domain_exceptions.py` cubriendo herencia,
  mensajes y traducción HTTP. 53/53 pytest verde.
- **Nota**: `security.py` mantiene `HTTPException` (401/403/500) por ser
  middleware HTTP puro; no aporta abstraerlas a dominio.

### 2.4 Extraer `UserService` en `users/application/` (ARQ-02)
- [x] `users/application/user_service.py` con `get_me_overview`,
  `get_my_profile`, `update_my_profile`, `get_my_stats`, `list_admin_users`,
  `get_admin_stats` (2026-05-27).
- [x] El router queda fino: HTTP + DI + delegación. 165 → 80 líneas, sin
  SQL ni `text()` inline.
- [x] Helper `get_user_service(db)` como composition root (patrón ADR-007).
- [x] Repo enriquecido con `get_user_roles`, `get_username`,
  `list_admin_users` y `get_admin_stats` para encapsular el SQL que
  vivía en el router.
- [x] DTO `CurrentUser(id, email)` desacopla el service del modelo `User`
  de Supabase.
- [x] 7 tests unitarios nuevos en `test_user_service.py` con mocks. 60/60
  pytest verde.

### 2.5 Capa `application/` mínima en `categories`, `stores`, `notifications`
**Decisión (2026-05-28): NO extraer servicios.** Tras evaluar caso a caso:

- **`categories`** y **`stores`** son CRUD admin trivial sin reglas de
  negocio. Un `XService` que sólo delegue al repo sería boilerplate puro.
- **`notifications`** tampoco aporta: los 3 endpoints son consultas
  directas; la única lógica (crear notificaciones cuando un deal coincide
  con una alerta) ya vive en `alerts/application/alert_matcher.py`.

Aplicamos KISS/YAGNI: cuando aparezca la primera regla cross-field o
cross-repo, se extrae el service en ese momento siguiendo el patrón de
`users/application/user_service.py`.

- [x] Documentada la decisión en docstring al inicio de los 3 routers
  (`categories/api/router.py`, `stores/api/router.py`,
  `notifications/api/router.py`) con criterios concretos para cuando sí
  haya que crear el service.
- [x] Reafirma la regla de la arquitectura: capa `application/` cuando
  hay valor (`UserService`, `DealService`, `AlertMatcher`,
  `PreviewProductFromUrlUseCase`), no por simetría visual.

---

## FASE 3 — Producción ready (observabilidad y seguridad)

> Lo que falta para que el día que algo falle en producción, podamos
> debuggearlo y no caigamos en ataques triviales.

### 3.1 Middleware `request_id` + structured logging (ARQ-06)
- [x] `core/request_id.py` con `ContextVar`, `RequestIdMiddleware`,
  helper `get_request_id()` y constante `REQUEST_ID_HEADER`. Genera UUID4
  hex si no viene en la petición; respeta `X-Request-Id` entrante para
  trazabilidad end-to-end con proxy/LB. (2026-05-28)
- [x] `core/logging.py` reescrito con `_RequestIdFilter` que añade
  `record.request_id` automático y dos formatters intercambiables:
  `_JsonFormatter` (producción, una línea JSON con ts/level/logger/msg/
  request_id + campos extra) y formato texto legible para desarrollo.
- [x] `Settings.log_format` (`json`|`text`, default `json`) configurable
  por env.
- [x] `main.py` registra `RequestIdMiddleware` antes que CORS y expone
  `X-Request-Id` como header CORS. Handlers globales de error añaden
  manualmente el header a las respuestas 4xx/5xx via
  `_with_request_id_header()`.
- [x] 5 tests nuevos en `test_request_id.py`. 65/65 pytest verde.

### 3.2 Rate limiting con slowapi (ARQ-07)
- [x] `slowapi==0.1.9` añadido a `requirements.txt`. (2026-05-28)
- [x] `core/rate_limit.py` con `Limiter` configurado:
  - Key function por IP respetando `X-Forwarded-For` (proxy/Nginx delante).
  - Storage en memoria (basta para el monolito; switch a Redis si hay
    múltiples instancias).
  - `Settings.rate_limit_enabled` para desactivar globalmente.
  - `headers_enabled=False` para evitar exigir `response: Response` en
    cada endpoint.
  - Handler `rate_limit_exceeded_handler` con `{"detail": "..."}` en
    español + `Retry-After` calculado a partir del rule de slowapi +
    `X-Request-Id` propagado.
- [x] `main.py` registra el limiter (`app.state.limiter`),
  `SlowAPIMiddleware` y el exception handler para `RateLimitExceeded`.
- [x] Límites aplicados:
  - `POST /products/preview-from-url`: **10/min** (caro: HTTP a Amazon + OpenAI).
  - `POST /deals/{id}/click`: **60/min** (anti-spam de contador, público).
  - `POST /deals/{id}/vote`: **30/min**.
  - `POST /deals/{id}/comments`: **10/min**.
  - `POST /telegram/notify`: **5/min** (publicación admin).
- [x] 3 tests nuevos en `test_rate_limit.py`. 68/68 pytest verde.

### 3.3 Audit log en acciones admin críticas
- [x] Modelo `AuditLog` en `core/audit/models.py`: tabla
  `admin_audit_log` (id, user_id FK profiles, action, target_type,
  target_id, payload JSON, request_id, created_at). Índices por user_id,
  action, target_id, created_at. (2026-05-28)
- [x] **Primera migración real con Alembic**:
  `alembic/versions/20260528120000_add_admin_audit_log.py`. RLS activada.
- [x] Helper `audit_log(session, *, user_id, action, target_type,
  target_id, payload)` en `core/audit/service.py`:
  * Best-effort: cualquier fallo NO propaga al endpoint.
  * Usa `session.begin_nested()` (SAVEPOINT) para contener errores y
    evitar que un fallo envenene la sesión principal con
    `PendingRollbackError`.
  * Inyecta `request_id` automáticamente del contextvar de F3.1 para
    correlacionar con los logs.
  * `_sanitize_payload` reemplaza valores no JSON-serializables por
    `repr()` antes de guardar.
- [x] Llamado desde: `deal.create/update/delete`,
  `category.create/delete`, `store.create/update/delete`,
  `telegram.notify`.
- [x] Endpoint `GET /admin/audit` paginado y filtrable (action,
  target_type, user_id) en `users/api/router.py`. UserService + repo
  enriquecidos con `list_audit_log`.
- [x] 6 tests nuevos en `test_audit_log.py`. 76/76 pytest verde.
- **Acción operador**: en NAS, una sola vez antes de reiniciar el
  contenedor con este commit:
  ```bash
  docker exec -it buenchollo-api alembic stamp 20260527120000_baseline
  docker exec -it buenchollo-api alembic upgrade head
  ```

### 3.4 Health check enriquecido
- [ ] Ampliar `/health` para reportar también `db: ok|error` y `supabase_auth: ok|error`.
- [ ] Endpoint `/health/ready` (k8s-style) que falle si la BD está caída.
- [ ] **Razón**: cuando despliegues con un load balancer o k8s, el orchestrator necesita saber si la app está realmente lista.

### 3.5 Errores no manejados → Sentry-style (opcional pero recomendable)
- [ ] Evaluar si añadir Sentry / GlitchTip free tier ahora o esperar.
- [ ] Si sí: integrar `sentry-sdk[fastapi]` mínima.
- [ ] Si no: documentar como decisión "logs estructurados son suficientes hasta X usuarios".

---

## FASE 4 — API: versionado

### 4.1 Prefijo `/v1` global en backend (ARQ-04)
- [ ] Refactor de `main.py`: todos los `include_router(...)` con `prefix="/v1"`.
- [ ] Probar manualmente que `/v1/deals/latest`, `/v1/auth/me`, etc. responden.
- [ ] Endpoint `/health` se queda sin versionar (correcto, es infra).

### 4.2 Actualizar `apiClient` frontend
- [ ] `services/api/client.ts`: `const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/v1"`.
- [ ] Smoke test: pasar por todos los flujos principales (home, login, favorito, comentario, admin, perfil).

---

## FASE 5 — Frontend: features-based + tipado total + caché

> El frontend está bien tipado pero organizado por tipo técnico. Lo
> reorganizamos por dominio y añadimos TanStack Query para caché y
> deduplicación de peticiones (preparándolo para escalar a más usuarios).

### 5.1 Carpeta `components/layout/` y `features/` (ARQ-01)
- [ ] `mkdir src/components/layout` y mover `Header.tsx`, `Footer.tsx`, `Layout.tsx`, `Logo.tsx`.
- [ ] `mkdir src/features/` con subcarpetas por dominio: `deals/`, `comments/`, `alerts/`, `admin/`, `profile/`, `notifications/`.
- [ ] Mover componentes:
  - `DealCard.tsx` → `features/deals/`
  - `Comments.tsx` → `features/comments/`
  - `TelegramPanel.tsx` → `features/admin/`
  - `CategoriesDrawer.tsx` → `features/categories/` (o `components/layout/` si lo consideramos navegación).
  - `ShareBox.tsx` → `features/deals/` (es feature de deal).
- [ ] Actualizar imports (TS reportará todos los rotos).
- [ ] `tsc --noEmit` verde.

### 5.2 Tipar lo que quede con `any`
- [ ] Auditar con `grep -rn ": any" src/`.
- [ ] Tipar `chollo.$slug.tsx` (queda algún `any` en `setDeal((d: any) => ...)`, etc.).
- [ ] `useState<any[]>` que queden en rutas no críticas.
- [ ] **Meta**: 0 `any` en `src/`.

### 5.3 Activar TypeScript strict mode (si no lo está)
- [ ] Revisar `tsconfig.json`: `"strict": true`, `"noUncheckedIndexedAccess": true`, `"noImplicitOverride": true`.
- [ ] Arreglar errores que aparezcan.
- [ ] `tsc --noEmit` verde.

### 5.4 Añadir TanStack Query (caché y deduplicación)
- [ ] `npm install @tanstack/react-query`.
- [ ] Configurar `QueryClient` en `__root.tsx`.
- [ ] Migrar fetches críticos a `useQuery`:
  - `useDeals()` (home, explorar)
  - `useDeal(slug)` (chollo detalle)
  - `useFavorites()` (badge, listado)
  - `useUnreadNotifications()` (header badge)
  - `useAdminStats()` (panel)
- [ ] Mantener `apiClient` como capa subyacente.
- [ ] **Razón**: deduplicación automática, caché por staleTime, refetch en focus. Esencial para escalar UX.

### 5.5 Hooks de dominio en cada `feature/`
- [ ] `features/deals/hooks/useDealVote.ts`, `useFavorite.ts`.
- [ ] `features/comments/hooks/useComments.ts`.
- [ ] Etc.
- [ ] **Razón**: encapsulación de la lógica de cada feature en su propia carpeta, accesible vía import explícito.

### 5.6 ESLint con reglas estrictas
- [ ] Revisar `eslint.config.js` (o equivalente).
- [ ] Reglas que activar: `@typescript-eslint/no-explicit-any`, `@typescript-eslint/no-floating-promises`, `react-hooks/exhaustive-deps` (error, no warn).
- [ ] Arreglar lo que reporte.
- [ ] **Razón**: prevención de bugs típicos en runtime.

---

## FASE 6 — CI/CD y calidad continua

> Que cada PR/push verifique automáticamente que no se rompe nada.

### 6.1 GitHub Actions con tsc + pytest
- [ ] `.github/workflows/ci.yml`:
  - Job `frontend`: `npm ci && npx tsc --noEmit && npm run lint`.
  - Job `backend`: `pip install -r requirements-dev.txt && pytest`.
- [ ] Disparar en `pull_request` y `push` a `main`.
- [ ] **Razón**: red de seguridad automática para no romper main por descuido.

### 6.2 Pre-commit hook básico
- [ ] `pre-commit` (Python) con: ruff, black, eslint, prettier.
- [ ] `pre-commit install`.
- [ ] **Razón**: formato y lint uniformes sin pensar.

### 6.3 Dependabot / renovate
- [ ] Activar Dependabot básico para npm y pip.
- [ ] Frecuencia semanal.
- [ ] **Razón**: parches de seguridad llegan solos.

---

## FASE 7 — Validación final y entrega

### 7.1 Recorrido manual exhaustivo
- [ ] Lista de pruebas (~15 flujos) en `docs/SMOKE_TEST.md`.
- [ ] Ejecutar y firmar (commit).

### 7.2 Actualizar PROJECT_STATUS.md
- [ ] Nueva sección `§ 3.quater` con resumen de este plan completado.
- [ ] Valoración arquitectónica actualizada.
- [ ] Lista de pendientes futuros (post-TFM): featurefactor lo que no se hizo.

### 7.3 Commit final tag `v1.0.0-tfm`
- [ ] `git tag v1.0.0-tfm -m "Versión presentada como Trabajo Final de Máster"`.
- [ ] `git push --tags`.
- [ ] **Razón**: punto fijo del repo para volver si algo se rompe después.

---

## Resumen de impacto esperado

| Bloque | Tiempo estimado | Valor TFM | Valor producción |
|---|---|:---:|:---:|
| F1 - ADRs | 2-3h | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| F2 - Backend fundamentos | 4-6h | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| F3 - Producción ready | 4-5h | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| F4 - Versionado API | 30min | ⭐⭐ | ⭐⭐⭐⭐ |
| F5 - Frontend reorganización | 4-6h | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| F6 - CI/CD | 1-2h | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| F7 - Validación | 1h | ⭐⭐ | ⭐⭐ |

**Tiempo total estimado**: 17-24 horas de trabajo focado, divisibles en sesiones.

---

## Reglas de oro del plan

1. **Una tarea = un commit**. No batchear.
2. **Verificación manual + tsc/pytest** antes de cada commit.
3. **Marcar `[x]` en este fichero** al cerrar cada tarea, y commitearlo junto al cambio.
4. **Reiniciar backend** cuando una tarea afecte a Python (recordatorio explícito).
5. **Si una tarea se descubre demasiado grande** durante la ejecución, partirla en este plan antes de seguir.
6. **No saltar fases** salvo justificación explícita (algunas dependen de otras: F4 antes de F5, F1 antes de F7).
