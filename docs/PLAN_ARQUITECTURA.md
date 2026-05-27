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
| **F1** | Documentación arquitectónica (5 ADRs + diagrama) | 6 | 🟡 3/6 |
| **F2** | Backend: fundamentos (migraciones, Alembic, excepciones, UserService) | 5 | ⬜ |
| **F3** | Producción ready (request_id, logging, rate limit, audit log, health) | 5 | ⬜ |
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
- [ ] Crear `docs/adr/ADR-006-rls-service-role.md`.
- Documentar el incidente del 2026-05-27 y el fix aplicado.
- Cómo se gestiona el `anon key` (público) vs `service_role` (server-only).

### 1.5 ADR-007 — Inyección de dependencias con `Depends` de FastAPI
- [ ] Crear `docs/adr/ADR-007-di-fastapi-depends.md`.
- Composition root distribuido en factories `get_X`.
- `app.dependency_overrides` para testing.

### 1.6 README arquitectónico + diagrama del sistema
- [ ] Sección "Arquitectura" en `README.md` raíz con:
  - Diagrama Mermaid: Browser → FastAPI → Postgres/Supabase + adaptadores externos.
  - Resumen de los 7 ADRs.
  - Estructura de carpetas por módulo (backend) y por features (frontend, post F5).
  - Links a documentación viva.

---

## FASE 2 — Backend: fundamentos arquitectónicos

> Por qué ahora: dejar el backend en estado canónico antes de añadirle
> middleware, versionado y demás capas. Cambios mecánicos, bajo riesgo.

### 2.1 Mover migraciones SQL al backend
- [ ] `git mv buenchollo-web/supabase/migrations/ buenchollo-api/supabase/migrations/`.
- [ ] Actualizar `PROJECT_STATUS.md` y `CLAUDE.md` con la nueva ubicación.
- [ ] Verificar que `supabase/config.toml` (si existe) sigue funcionando.
- **Razón**: el backend es dueño del esquema, no la web.

### 2.2 Configurar Alembic en backend
- [ ] `alembic init alembic/` ya está parcialmente; revisar `alembic.ini`.
- [ ] Hacer baseline con `alembic stamp head` sobre el esquema actual.
- [ ] Documentar en `buenchollo-api/README.md` cómo crear/aplicar migraciones.
- **Razón**: queremos versionar el esquema desde Python yendo adelante.

### 2.3 Excepciones de dominio + handler global (ARQ-03)
- [ ] Crear `core/exceptions.py` con `DomainError`, `NotFoundError`, `ForbiddenError`, `ValidationError`.
- [ ] Cada módulo añade sus excepciones específicas en `<modulo>/domain/exceptions.py` (heredan de las anteriores).
- [ ] Refactor de servicios y repos: `raise DealNotFound("...")` en vez de devolver `None` o lanzar `HTTPException` desde application.
- [ ] `main.py`: `@app.exception_handler(DomainError)` que mapea cada subtipo a su status HTTP.
- [ ] Routers: ya no necesitan `raise HTTPException(404, ...)`; sólo dejan burbujear.
- [ ] Test: añadir 2-3 unitarios que comprueben que las excepciones se lanzan correctamente.

### 2.4 Extraer `UserService` en `users/application/` (ARQ-02)
- [ ] Crear `users/application/user_service.py` con `get_my_profile`, `update_my_profile`, `get_my_stats`, `list_admin_users`.
- [ ] El router pasa a delegar en el service.
- [ ] Repo (`ProfileRepository`) sigue igual; service lo usa por DI.
- [ ] Tests unitarios mínimos del service con mock del repo.

### 2.5 Capa `application/` mínima en `categories`, `stores`, `notifications`
- [ ] Sólo si la lógica lo merece (CRUD trivial puede quedarse). Evaluar caso a caso.
- [ ] Para `notifications`: añadir `NotificationService.mark_as_read_for_user`, `unread_count` (si añade valor frente al repo).
- [ ] Para `categories` y `stores`: si sólo es CRUD, dejar como están y **documentarlo** como decisión consciente.

---

## FASE 3 — Producción ready (observabilidad y seguridad)

> Lo que falta para que el día que algo falle en producción, podamos
> debuggearlo y no caigamos en ataques triviales.

### 3.1 Middleware `request_id` + structured logging (ARQ-06)
- [ ] `core/middleware/request_id.py` que genera `uuid4` por request, lo añade como header `X-Request-Id` y lo inyecta en un `contextvars.ContextVar`.
- [ ] `core/logging.py` configura un `Formatter` JSON que incluye el `request_id` del contextvar.
- [ ] Registrar el middleware en `main.py`.
- [ ] Probar con `curl` que la respuesta incluye `X-Request-Id` y que el log lo muestra.

### 3.2 Rate limiting con slowapi (ARQ-07)
- [ ] `pip install slowapi`, añadir a `requirements.txt`.
- [ ] Configurar limiter por IP en `main.py`.
- [ ] Aplicar límites donde tiene sentido:
  - `POST /products/preview-from-url`: 10/min (caro, hace HTTP a Amazon + OpenAI).
  - `POST /deals/{id}/click`: 60/min (anti-spam de contador).
  - `POST /deals/{id}/vote`: 30/min.
  - `POST /deals/{id}/comments`: 10/min.
  - `POST /telegram/notify`: 5/min (publicación admin, evita doble envío).
- [ ] Excepciones rate limit → 429 con mensaje claro.
- [ ] Probar con un bucle de curl que llega al límite.

### 3.3 Audit log en acciones admin críticas
- [ ] Nueva tabla `admin_audit_log` (id, user_id, action, target_type, target_id, payload, created_at).
- [ ] Migración Alembic.
- [ ] Helper `audit_log(...)` en `core/audit.py`.
- [ ] Llamar desde: crear/editar/borrar deal, crear/borrar categoría/tienda, promote/demote admin.
- [ ] Endpoint `GET /admin/audit` (paginado) sólo para admins.
- [ ] **Razón**: trazabilidad de acciones sensibles. Si mañana hay un deal borrado por error, sabremos quién y cuándo.

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
