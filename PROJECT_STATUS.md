# PROJECT_STATUS — BuenCholloTech
*Última actualización: 2026-05-30 (cierre del hardening arquitectónico — release v1.0.0-tfm)*

> **⚠️ Revisar este documento antes de migrar a dominio web en producción.**
> Contiene el estado real del proyecto, deuda técnica pendiente y la hoja de ruta completa.

---

## 1. Estado general

**Valoración arquitectónica: 9.7 / 10** (subió desde 9.3 tras el hardening F1–F7 del 2026-05-30)

El proyecto está en producción funcionando, con CI verde en GitHub Actions, infraestructura
de calidad senior (observabilidad, rate limiting, audit log, request_id, Sentry) y frontend
con TypeScript strict + ESLint endurecido + TanStack Query + organización por features.
Las decisiones técnicas (Clean Architecture, DIP con Protocols, async/await, PgBouncer,
API versionada `/v1`, ADR-002) son correctas y defendibles académicamente para el TFM.

---

## 2. Principios de arquitectura (no negociables)

1. **El router solo habla HTTP** — recibe request, llama al caso de uso, devuelve respuesta. Sin SQL ni lógica de negocio.
2. **Casos de uso en `application/`** — toda la orquestación va ahí, independiente de FastAPI y de la BD.
3. **El repositorio es el único que toca la BD** — ningún `session.execute()` fuera de `infrastructure/`.
4. **Módulos sin acoplamiento cruzado** — `deals` no importa de `products`. Lo compartido va a `core/`.
5. **Un proveedor externo = un adaptador en `infrastructure/`** — añadir AliExpress = crear `aliexpress_client.py` que implemente `ProductPreviewProvider`. Nada más cambia.
6. **ADR-002: el frontend nunca llama a Supabase DB directamente** — toda la lógica de datos pasa por FastAPI. Excepción aprobada: Supabase Auth y Storage.

---

## 3. Historial de refactorización completada

| Fase | Tarea | Estado |
|---|---|---|
| 1 | Documentación y onboarding | ✅ Completado |
| 2 | Limpiar router deals — extraer `DealService`, `auto_slug`, FK check | ✅ Completado |
| 3 | Favoritos vía FastAPI — eliminar `supabase.from("favorites")` del frontend | ✅ Completado |
| 4 | Stores CRUD admin — panel de gestión de tiendas | ✅ Completado |
| 5 | Scheduler — activación programada, expiración automática, limpieza al arrancar | ✅ Completado |
| 6 | Telegram — panel completo con preview, GPT, categorías, canales, emojis Premium | ✅ Completado |
| 7 | Tests unitarios (DealService, AlertMatcher, matches_alert) | ✅ Completado (2026-05-26) |
| 8 | Refactor de buenas prácticas para TFM — ver § 3.bis | ✅ Completado (2026-05-26) |

---

### 3.bis  Refactor de buenas prácticas — 2026-05-26

Bloque grande de refactor previo a la entrega del TFM, con auditoría completa
SOLID / DRY / KISS / YAGNI y plan por fases. Resumen:

**Fase 1 — Imprescindibles (P0)**
- `B-01` Sanitizados los mensajes de error internos en `security.py` y
  `main.py`: ya no se filtra `str(exc)` al cliente.
- `F-01` Eliminadas las llamadas directas a Supabase desde el frontend en
  `DealCard`, `Comments`, `routes/index`, `useAuth`, `admin.usuarios`. Nuevo
  módulo backend `comments/` (Clean Arch) y endpoint `GET /admin/users`.
- `F-02` Tipado fuerte en `services/api/client.ts` y servicios (`deals`,
  `categories`, `auth`, `comments`, `products`, `admin users`). Eliminados
  todos los `any` y `null as any`.
- **Bug crítico de datos**: el trigger `handle_new_user` de Supabase había
  sido modificado en producción para insertar `role='admin'`. Restaurado al
  valor original `'user'` (hotfix SQL aplicado por Pedro).

**Fase 2 — Recomendables (P1)**
- `F-02 cont.` Tipado completo de `admin.chollos.tsx`: nuevo tipo `DealForm`,
  helper `dealToForm()`, `DealStatus` literal. Antes 9+ `any`, ahora 0.
  Bonus: `productsApi.previewFromUrl` reemplaza el `fetch` inline.
- `B-02` `DealService` recibe `AlertMatcher` opcional por DI y dispara
  `notify_matching_alerts` internamente en create/update. El router queda
  solo HTTP.
- `B-06` 12 tests unitarios con mocks (sin BD): `DealService` (8) y
  `AlertMatcher` (4).
- `F-06` Helper `errorMessage(e, fallback)` en `lib/errors.ts` reutilizado
  en `admin.categorias`, `admin.tiendas`, `admin.chollos`, `chollo.$slug`.
- `F-05`/`F-07` Constantes y utilidades centralizadas: `lib/constants.ts`
  (`DEAL_STATUS_OPTIONS`, thresholds de temperatura) y `lib/format.ts`
  (`calculateDiscount`, `toDatetimeLocal`, `temperatureColor`).

**Fase 3 — Opcionales (P2/P3)**
- `B-03` Helper `_base_deal_query()` en `DealRepository` centraliza el
  `selectinload(category, subcategory, store)` repetido 6 veces.
- `B-04` `matches_alert(alert, deal)` sale del repo a `alerts/application/
  matching.py` (función pura). 8 tests unitarios adicionales.
- `B-05` `DealCleanerService._safe_run(name, action, default)` elimina el
  patrón triple try/except idéntico.
- `F-04` Schemas Zod en `lib/validation/`: `alertFormSchema` (al menos un
  criterio, max_price > 0, min_discount 1-100) y `dealFormSchema` (título
  3-200, URL afiliada válida, previous_price > current_price).
- `F-03` Split de `admin.chollos.tsx` y `chollo.$slug.tsx`: **pospuesto** y
  documentado como mejora identificada en la memoria. Razón: tras tipar,
  validar y mover orquestación, el SRP funcional ya está cubierto; sólo
  queda el "tamaño de fichero", de bajo valor frente al riesgo de refactor
  antes de la entrega.

**Métricas finales del refactor (tras cleanup 2026-05-26)**
- TypeScript: `tsc --noEmit` 0 errores.
- pytest: **49/49 verde** (incluyendo `test_amazon_client.py` reescrito para
  el cliente HTTP actual: 7 tests).
- ADR-002: **100% cumplido**. Cero `supabase.from()` / `supabase.rpc()` en
  todo el frontend. Sólo `supabase.auth.*` y `supabase.storage.*` (las dos
  excepciones aprobadas).

**Endpoints backend añadidos en el cleanup**
- `POST /deals/{deal_id}/click` — incrementa `click_count` atómicamente.
- `GET /users/me/profile` — perfil del usuario autenticado.
- `PUT /users/me/profile` — actualiza display_name + bio.
- `GET /users/me/stats` — encapsula el RPC `get_user_stats`.
- `GET /admin/stats` — 6 counts agregados en una sola query SQL.

---

### 3.ter  Hardening de seguridad — 2026-05-27

Supabase reportó la vulnerabilidad `rls_disabled_in_public` (crítica): las 12
tablas de `public` tenían RLS desactivado, así que con el `anon key` (público
en el bundle del frontend) cualquiera podía leer/borrar la BD entera.

Fix aplicado: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` en las 12 tablas,
versionado en la migración
[`20260527090000_enable_rls_all_tables.sql`](buenchollo-api/supabase/migrations/20260527090000_enable_rls_all_tables.sql).

Por qué no rompe nada:
- El backend usa la `service_role key` que **bypassa RLS por diseño**.
- ADR-002 garantiza que el frontend nunca llama a Supabase DB directamente
  (sólo Auth y Storage, que tienen su propio sistema de policies).
- Las políticas previas (definidas en migraciones anteriores) siguen
  vigentes; al activar RLS pasan a aplicarse.

Probado tras el fix: home, login, favoritos, comentarios, votos, panel admin
(usuarios + resumen + chollos), perfil y notificaciones — todo OK.

---

### 3.quater  Hardening arquitectónico F1–F7 — 2026-05-30 (release v1.0.0-tfm)

Sprint final de hardening definido en [`docs/PLAN_ARQUITECTURA.md`](docs/PLAN_ARQUITECTURA.md).
30 tareas en 7 fases. Todas verdes.

**F1 — Documentación arquitectónica (6 ADRs + diagrama)**
- ADR-001 a ADR-006 actualizados o creados (Clean Arch, ADR-002, versionado API,
  observabilidad, seguridad, infraestructura).
- Diagrama Mermaid de arquitectura en `README.md`.

**F2 — Backend fundamentos**
- Alembic configurado con migración inicial. Auto-`alembic upgrade head` al
  arrancar el contenedor (sin SSH al NAS).
- Excepciones de dominio propias en cada módulo (`DealNotFoundError`,
  `CategoryNotFoundError`, etc.). Routers traducen a HTTPException.
- `UserService` y capa `application/` añadida a `users/` y `categories/`.

**F3 — Producción ready**
- `request_id` middleware con ContextVar + logs JSON estructurados.
- Rate limiting por IP con SlowAPI (X-Forwarded-For aware) en endpoints sensibles.
- Admin audit log con SAVEPOINT (`session.begin_nested()`) para best-effort sin
  envenenar la sesión SQLAlchemy. Tabla `admin_audit_log` con `request_id`.
- Health check separado: `/health` (liveness) y `/health/ready` (readiness con
  latencia BD).
- Sentry SaaS con `LoggingIntegration` y `before_send` que adjunta `request_id`.

**F4 — API versionada `/v1`**
- Backend: `APIRouter(prefix="/v1")` envuelve auth, products, categories, deals,
  stores, telegram, alerts, notifications, comments. `health_router` queda fuera
  del prefijo.
- Frontend: `apiClient` apunta a `${VITE_API_URL}/v1`.

**F5 — Frontend pro-grade (6/6)**
- `F5.1` Reorganización: `components/layout/` (chrome) y `features/{deals,admin,
  notifications,telegram}/` (componentes + hooks por dominio).
- `F5.2` Tipado completo eliminando los últimos `any` residuales.
- `F5.3` TypeScript strict mode + `noUncheckedIndexedAccess` + `noImplicitOverride`.
- `F5.4` TanStack Query 5.83 con `QueryClient` compartido. Hooks:
  `useUnreadNotifications`, `useNotificationsList`, `useMarkNotificationsRead`,
  `useAdminStats`. Migrados: Header badge, `/notificaciones`, `/admin/`.
- `F5.5` Hooks de dominio en cada `features/<dominio>/hooks/`.
- `F5.6` ESLint endurecido: `no-explicit-any` (error), `exhaustive-deps` (error),
  `no-unused-vars` con patrón `^_`.

**F6 — CI/CD (3/3)**
- `F6.1` GitHub Actions: jobs `Backend (pytest)` y `Frontend (typecheck + lint)`
  en cada push/PR. Verde en main.
- `F6.2` `.pre-commit-config.yaml` con hooks de higiene (trailing whitespace,
  EOL final, check-yaml, check-json, large files, detect-private-key).
- `F6.3` Dependabot semanal con grupos: pip + npm + github-actions, agrupando
  minor/patch para no ahogar PRs.

**F7 — Cierre**
- `F7.1` [`docs/SMOKE_TEST.md`](docs/SMOKE_TEST.md) con guion exhaustivo manual
  pre-release (10 secciones, ~50 checks).
- `F7.2` Esta sección.
- `F7.3` Tag `v1.0.0-tfm`.

**Decisión arquitectónica notable durante el sprint**
- Tests separados por tipo: 78 unitarios (mockean Supabase/Amazon, corren en CI
  en ~1s) + 9 de integración (marcador `@pytest.mark.integration`, requieren
  Postgres real, se ejecutan en local antes del release). El workflow CI usa
  `pytest -m "not integration"` para no exigir BD en GitHub.

**Métricas finales del sprint**
- pytest: **87 verde** (78 unit + 9 integración local).
- TypeScript: `tsc --noEmit` 0 errores en `buenchollo-web` con `strict` activado.
- ESLint: 0 errores (10 warnings inocuos de Fast Refresh en componentes UI).
- CI en main: verde ✅ (commits `7bf012d` y siguientes).

---

## 4. Deuda técnica — Auditoría Mayo 2026 (revisada 2026-05-26)

### 🟢 ADR-002 — **CUMPLIDO AL 100%**

Tras el cleanup final del 2026-05-26 **no queda ninguna llamada directa a
Supabase DB desde el frontend**. Únicas referencias `supabase.*` restantes:

- `supabase.auth.*` — login, registro, sesión, refresh token.
- `supabase.storage.*` — subida de imágenes de chollos (excepción aprobada).

Histórico completo:

| Archivo | Tablas / operaciones | Estado |
|---|---|---|
| `explorar.tsx` | `favorites` (read) | ✅ Migrado a `favoritesApi.getFavorites()` |
| `index.tsx` | `favorites` (read) | ✅ Migrado a `favoritesApi.getFavorites()` |
| `chollo.$slug.tsx` | `deals` click_count + comment_count | ✅ `dealsService.trackClick()` + refetch con `getBySlug()` |
| `alertas.tsx` | `alerts` CRUD completo | ✅ El módulo `alerts` en FastAPI ya existe |
| `alertas.nueva.tsx` | `categories`, `stores`, `alerts` | ✅ Usa `alertsApi`, `categoriesService`, `storesService` |
| `notificaciones.tsx` | `notifications` (read + mark read) | ✅ Módulo `notifications` en FastAPI |
| `perfil.tsx` | `profiles` read/update + RPC stats | ✅ `authApi.getMyProfile/updateMyProfile/getMyStats` |
| `admin.index.tsx` | 6 counts agregados | ✅ Endpoint `GET /admin/stats` + `adminApi.getStats()` |
| `admin.usuarios.tsx` | `profiles` con roles | ✅ Endpoint `GET /admin/users` + `adminUsersApi` |
| `DealCard.tsx` | `favorites` toggle | ✅ Migrado a `favoritesApi.toggle()` |
| `Comments.tsx` | `deal_comments`, `comment_votes`, `profiles` | ✅ Nuevo módulo `comments` + `commentsApi` |
| `useAuth.tsx` | `user_roles` | ✅ Migrado a `authApi.me()` |
| `Header.tsx` | `notifications` unread count | ✅ Migrado a `notificationsApi.unreadCount()` |

**Excepción aprobada:** `login.tsx`, `registro.tsx` — usan Supabase Auth directamente, correcto por diseño.

---

### 🟡 Media prioridad

#### Capas incompletas en módulos menores

`categories/`, `stores/` y `users/` van directamente `router → repository` sin capa `application/`.
Funcional pero inconsistente con la arquitectura declarada.

```
deals/        ✅  api → DealService → DealRepository
products/     ✅  api → PreviewProductFromUrlUseCase → adapters
categories/   ⚠️  api → repository  (sin application layer)
stores/       ⚠️  api → repository  (sin application layer)
users/        ⚠️  api → repository  (sin application layer)
telegram/     ✅  api → TelegramPostGenerator → infrastructure
```

Para `categories` y `stores` (lógica CRUD simple) es aceptable.
Para `users` (gestión de perfiles, roles) debería tener su capa de uso.

#### `__init__.py` faltantes en subdirectorios

Python 3.3+ funciona sin ellos (namespace packages), así que no rompe nada.
Pero es mala práctica: problemas con linters, IDEs y herramientas de testing.

Faltan en: `deals/api/`, `deals/domain/`, `deals/infrastructure/`,
`categories/` (y todos sus subdirectorios), `stores/` (ídem), `users/` (ídem), `telegram/api/`.

#### `test_amazon_client.py` desactualizado

El cliente Amazon fue reescrito a HTTP directo pero el test sigue mockeando el SDK antiguo.
Es el único test roto conocido.

---

### 🟢 Baja prioridad

- **`admin.index.tsx` stats**: para lectura admin es tolerable, pero lo correcto es `GET /admin/stats`
- **Sin excepciones de dominio propias**: solo existe `ProductNotFoundError`. El resto usa `HTTPException` directamente en routers, mezclando protocolo HTTP con lógica de negocio.
- **Sin READMEs de setup**: `CLAUDE.md` cubre decisiones técnicas pero no "cómo arrancar desde cero"

---

## 5. Pendientes antes de migrar a dominio web en producción

> Esta sección es la checklist de producción. No migrar al dominio hasta completarla.

### Obligatorio
- [ ] **Variables de entorno de producción** revisadas: `CORS_ORIGINS` con el dominio real, `APP_ENV=production`, `LOG_LEVEL=WARNING`
- [ ] **CORS configurado** con el dominio exacto (no `*`) antes del go-live
- [x] **Supabase RLS** activado en las 12 tablas (ver § 3.ter)
- [ ] **Dockerfile** probado con `docker build` limpio desde el repo (no desde imagen cacheada)
- [ ] **`categories.json`** del backend sincronizado con el catálogo definitivo de Telegram
- [ ] **Ejecutar `docs/SMOKE_TEST.md` completo** antes del go-live al dominio definitivo

### Muy recomendable (todos completados en hardening F1–F7)
- [x] ~~Migrar `explorar.tsx` e `index.tsx` a `favoritesApi`~~ (cumplido en cleanup 2026-05-26)
- [x] ~~`GET /admin/stats` para `admin.index.tsx`~~ (cumplido en cleanup 2026-05-26)
- [x] ~~Reparar `test_amazon_client.py`~~ (7/7 verde en CI)
- [x] ~~README de setup~~ (cubierto por README + ADRs en `docs/`)

### Opcional (mejora calidad)
- [ ] `__init__.py` en todos los subdirectorios de módulos
- [x] ~~Módulo `alerts` y `notifications` en FastAPI~~ (existen y están versionados en `/v1`)
- [x] ~~Capa `application/` en `users/`~~ (cumplido en F2)
- [ ] Migrar tests de integración a CI con servicio Postgres (actualmente solo en local)

---

## 6. Cómo escalar a nuevos proveedores (AliExpress, PCComponentes…)

La arquitectura ya está preparada. Para añadir AliExpress:

```
1. Crear buenchollo-api/app/modules/products/infrastructure/aliexpress_client.py
   └── class AliexpressProductClient:
           def get_product_preview(url: str) -> ProductPreview | None
           # Implementa el Protocol ProductPreviewProvider

2. Registrar el adaptador en products/api/router.py como nueva dependencia.
   El caso de uso PreviewProductFromUrlUseCase no cambia nada.

3. El campo Deal.source ya existe para identificar el origen del chollo.

Nada más. deals, categories, stores, users, telegram: sin tocar.
```

---

## 7. Arquitectura objetivo (referencia)

```
buenchollo-api/
├── app/
│   ├── core/           # config, database, security, logging
│   └── modules/
│       ├── deals/
│       │   ├── domain/        # Deal, DealVote, Favorite — modelos ORM + lógica pura
│       │   ├── application/   # DealService, DealCleanerService
│       │   ├── infrastructure/# DealRepository
│       │   └── api/           # router (solo HTTP) + schemas Pydantic
│       ├── products/
│       │   ├── domain/        # ProductPreview, Protocols (DIP)
│       │   ├── application/   # PreviewProductFromUrlUseCase
│       │   └── infrastructure/# AmazonClient, OpenAIClient, [AliexpressClient]
│       ├── categories/        # mismo patrón — pendiente application layer
│       ├── stores/            # mismo patrón — pendiente application layer
│       ├── users/             # mismo patrón — pendiente application layer
│       ├── telegram/          # api + application (post_generator) + infrastructure
│       ├── alerts/            # ⬜ pendiente crear módulo
│       └── notifications/     # ⬜ pendiente crear módulo

buenchollo-web/
├── src/
│   ├── services/api/  # Única capa que habla con FastAPI (apiClient)
│   ├── routes/        # Páginas — solo llaman a services/api/ o Supabase Auth/Storage
│   ├── components/    # UI sin lógica de datos
│   └── hooks/         # useAuth, otros hooks de estado
```
