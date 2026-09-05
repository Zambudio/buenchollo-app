# PROJECT_STATUS — BuenCholloTech
*Última actualización: 2026-09-05 (Hotfix Storage del recorte de imágenes de Telegram — ver § 3.quinvicies)*

> **⚠️ Revisar este documento antes de migrar a dominio web en producción.**
> Contiene el estado real del proyecto, deuda técnica pendiente y la hoja de ruta completa.

---

## 1. Estado general

**Valoración arquitectónica: 9.7 / 10** (subió desde 9.3 tras el hardening F1–F7 del 2026-05-30)

El proyecto está en producción funcionando, con CI verde en GitHub Actions, infraestructura
de calidad senior (observabilidad, rate limiting, audit log, request_id, Sentry) y frontend
con TypeScript strict + ESLint endurecido + TanStack Query + organización por features.
Las decisiones técnicas (Clean Architecture, DIP con Protocols, async/await, PgBouncer,
API versionada `/v1`, ADR-002) son correctas y defendibles profesionalmente.

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
| 8 | Refactor de buenas prácticas — ver § 3.bis | ✅ Completado (2026-05-26) |
| 9 | Failover resiliente a OpenAI oficial — ver § 3.quindecies | ✅ Completado (2026-08-29) |
| 10 | Cierre de deuda técnica (TD-15, TD-16, TD-17) — ver § 3.sexdecies | ✅ Completado (2026-08-29) |

---

### 3.quinvicies  Recorte persistente de imágenes para publicaciones de Telegram — 2026-09-05

- El panel de Telegram permite seleccionar por arrastre la zona de la imagen que se publicará,
  cancelar sin cambios o aceptar el recorte desde un diálogo responsive coherente con la UI admin.
- El navegador genera un JPEG optimizado (máximo 2560 px), lo sube al bucket público
  `deal-images` con la sesión admin y sustituye la URL de la imagen activa. La URL persistente se
  utiliza tanto en la publicación inmediata como en las publicaciones programadas.
- Se añadieron pruebas de aceptación y cancelación del flujo. Suite frontend: 29 ficheros y 173
  pruebas en verde; typecheck, lint y build de producción correctos.
- Se normalizó con Prettier el formato pendiente de `AmazonAutofillPanel` y `admin.chollos`, que
  estaba bloqueando el job frontend de CI sin afectar al comportamiento.
- **Incidente post-despliegue y hotfix**: el proyecto Supabase de producción no contenía el bucket
  `deal-images` ni sus políticas, aunque ambos figuraban en una migración SQL legacy de 2026-04 que
  no llegó al estado real de la infraestructura. El recortador reproducía de forma determinista
  `NoSuchBucket / Bucket not found`. Se añadió la migración idempotente
  `20260905140000_create_deal_images_storage.sql` y se aplicó en producción: bucket público con
  límite de 5 MB y cuatro políticas (lectura pública; escritura/actualización/borrado para admins
  autenticados mediante consulta inline a `user_roles`, ya que `public.has_role` no existe).
  Verificación final: la sonda pública devuelve `NoSuchKey / Object not found`, una subida JPEG de
  prueba respondió HTTP 200 y el objeto temporal se eliminó; API `/health` en 200.

---

### 3.bis  Refactor de buenas prácticas — 2026-05-26

Bloque grande de refactor previo al lanzamiento de la v1.0.0, con auditoría completa
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

### 3.sexies  Módulo de Seguridad — 2026-06-02

Sprint dedicado al módulo de Seguridad. Auditoría completa
OWASP Top 10 con 6 hallazgos medios resueltos (ninguno crítico).

- `docs/reference/SECURITY_AUDIT.md`: informe completo con threat model, mapa
  de superficie de ataque, evaluación OWASP Top 10, hallazgos
  priorizados con cómo se explotan, impacto y cambio mínimo.
- `docs/SECURITY.md`: política, controles, deuda asumida, plan de
  respuesta a incidentes, checklist pre-go-live.
- Fixes aplicados:
  - SEC-01: pin `python-multipart==0.0.27` (5 CVEs DoS resueltas).
  - SEC-02: handler 500 ya no refleja Origin arbitrario.
  - SEC-03: `SecurityHeadersMiddleware` con CSP, X-Frame-Options,
    X-Content-Type-Options, Referrer-Policy, Permissions-Policy y
    HSTS en producción.
  - SEC-04: `CORS_ORIGINS` default sensato + warning startup en prod.
  - SEC-05: `max_length` en schemas Pydantic de deals.
  - SEC-06: SSRF allowlist Amazon + bloqueo IPs privadas en preview.
  - SEC-09: quitar email de logger.debug (PII).
- CI ampliado con job `security-audit`: pip-audit, npm audit
  (--omit=dev --audit-level=high), gitleaks.

10 tests nuevos para Security Headers (5) y SSRF allowlist (10) → 97
pytest verde.

---

### 3.octies  Cierre completo de la auditoría — 2026-07-17

Segunda tanda que cierra **todos** los hallazgos restantes de la auditoría
([`docs/archive/AUDIT_REPORT-2026-07.md`](docs/archive/AUDIT_REPORT-2026-07.md))
(PR #41, CI verde con 6 checks):

- **TD-05 cerrado** — `__init__.py` en los 20 subdirectorios de módulos que faltaban.
- **TD-13 cerrado** — Dockerfile con usuario no-root (`useradd app` + `USER app`)
  y `HEALTHCHECK` sobre `/health`. ⚠️ Requiere rebuild del contenedor NAS y
  verificar permisos de lectura del volumen.
- **M-07 cerrado** — scheduler extraído a `build_deals_scheduler()`
  (deals/application/scheduler.py) con flag `SCHEDULER_ENABLED` y entrypoint
  dedicado `python -m app.run_scheduler`; servicio comentado en compose listo
  para cuando se suba `--workers` (TD-11 desbloqueado).
- **TD-07 cerrado** — job CI "Backend (integración + Postgres)": `postgres:16`
  service + esquema generado desde los modelos ORM (`scripts/create_test_schema.py`;
  no vale `alembic upgrade head` porque el esquema base es de las migraciones SQL
  de Supabase). Los 9 tests de integración corren ahora en cada push/PR a main.
- **TD-14 y TD-08 cerrados** — `lib/logger.ts` con `logError()` central (consola
  siempre; Sentry browser si `VITE_SENTRY_DSN` está configurado, SDK lazy en chunk
  aparte, `sendDefaultPii=false`). Los 9 `console.error` de rutas migrados.
  ⚠️ Para activarlo: crear proyecto browser en Sentry y poner `VITE_SENTRY_DSN`
  en las build vars de Cloudflare Workers.
- **TD-03 cerrado** — split de `admin.chollos.tsx`: 999 → 349 líneas. Extraído a
  `features/admin/`: `deal-form.ts` (lógica pura + 7 tests), hooks `useAdminDeals`
  y `useDealImages`, componentes `AmazonAutofillPanel` / `DealFormPanel` /
  `AdminDealsTable` / `DuplicateDealDialog`. Comportamiento intacto (E2E verdes).
- TD-04/TD-06/TD-09/TD-11 cerrados el 2026-07-18 — ver § 3.novies.

**Suite total: 237 tests** (127 pytest = 118 unit + 9 integración · 102 vitest · 8 E2E).

---

### 3.novies  Cierre completo de la deuda técnica — 2026-07-18

Cierra los 4 items que quedaban abiertos en `10-technical-debt.md`, previo a
abrir la web al público:

- **TD-09 cerrado** — resultó estar casi resuelta de antemano: `POST /telegram/notify`
  ya existía en el backend (auth admin, rate limit 5/min, audit log) y el frontend
  ya lo consumía vía `apiClient` (no Supabase). Solo faltaba limpieza: borrada la
  Edge Function huérfana `buenchollo-api/supabase/functions/notify-telegram/index.ts`,
  que **no tenía autenticación** (cualquiera con la URL podía publicar en el canal) —
  cierre de deuda y fix de seguridad menor a la vez.
- **TD-06 cerrado** — vivía entera en `telegram/api/router.py`. Nuevo
  `telegram/domain/exceptions.py` (`TelegramNotConfigured`, `TelegramChannelNotConfigured`,
  `TelegramNotifyPayloadInvalid`, `TelegramSendFailed`) sustituye los 4
  `raise HTTPException(...)` directos, usando por primera vez `ServiceUnavailableError`/
  `ValidationError` de `core/exceptions.py`. Status codes preservados exactamente
  (503/503/422/503) — sin cambio de contrato de API. 4 tests nuevos
  (`test_telegram_api.py`).
- **TD-04 cerrado sin tocar código** — `categories/` y `stores/` tienen una nota
  arquitectónica explícita (F2.5, 2026-05-27) declarando la ausencia de capa
  `application/` como decisión YAGNI deliberada (CRUD sin reglas de negocio real).
  `users/` ya tenía su capa completa desde antes (`user_service.py`), más aislada
  del SDK de auth incluso que `deals`. La sección de abajo (antes contradictoria)
  queda corregida para reflejar el estado real en vez de "pendiente".
- **TD-11 cerrado (Fase 1 del plan de optimización, 100% completa)** —
  `docker-compose.yml`: `buenchollo-api` sube a `--workers 2` con
  `SCHEDULER_ENABLED=false`; se descomenta el contenedor dedicado
  `buenchollo-scheduler` (`python -m app.run_scheduler`, ya existía como código
  desde el cierre de M-07). `database.py`: pool SQLAlchemy acotado
  explícitamente (`pool_size=3, max_overflow=2, pool_recycle=300`) — con
  2 workers, máximo 10 conexiones simultáneas contra el pooler de Supabase en
  vez de los defaults sin límite documentado. Rebuild del contenedor en el NAS
  hecho y verificado (2026-07-18): `buenchollo-scheduler` arrancando, API en
  `--workers 2`. Cache Rule v2 de Cloudflare (§ T9), limitada a cinco rutas
  públicas exactas y respetando `Cache-Control`, verificada con `MISS → HIT`
  en `/v1/deals`; autenticados en `no-store` y nunca `HIT`. Validación funcional
  de votos/comentarios con F5 normal superada el 2026-07-19.

---

### 3.quattuorvicies  Cierre de 3/4 de TD-20: hardening del Advisor de Supabase (seguridad + rendimiento) — 2026-09-05

Continuación de § 3.tervicies: tras cerrar el crítico, el Advisor completo (seguridad + rendimiento, conector MCP autorizado) reportó 4 hallazgos WARN — ninguno una exposición de datos. Ejecutado siguiendo [`docs/superpowers/plans/2026-09-05-supabase-advisor-hardening.md`](docs/superpowers/plans/2026-09-05-supabase-advisor-hardening.md).

- **Verificación previa (Task 1, vía `execute_sql` del conector MCP)**: las 3 funciones `SECURITY DEFINER` señaladas son `RETURNS trigger` con 0 argumentos (revocar `EXECUTE` no afecta su disparo como trigger); `extensions` ya existe en el `search_path` por defecto (`"$user", public, extensions`) y aloja `pgcrypto`/`uuid-ossp`/`pg_stat_statements` — mover `pg_trgm` ahí es de bajo riesgo. `grep` confirmó que ningún código llama a esas funciones por RPC.
- **3 migraciones nuevas** (`20260902120000` → `20260905121000`, cadena única):
  - `20260905120000`: política `"Users view own role"` de `user_roles` reescrita con `(select auth.uid())` — cierra `auth_rls_initplan`.
  - `20260905120500`: `REVOKE EXECUTE ... FROM PUBLIC, anon, authenticated` en `handle_new_user`, `recalc_comment_votes`, `recalc_blog_comment_votes` — cierra `anon_security_definer_function_executable` / `authenticated_security_definer_function_executable` (×3).
  - `20260905121000`: `ALTER EXTENSION pg_trgm SET SCHEMA extensions` — cierra `extension_in_public`.
- **Verificación post-despliegue** (302 tests en verde antes de desplegar; `alembic upgrade head` en `buenchollo-api`, head confirmado en `20260905121000`):
  - `pg_trigger` confirma los 3 triggers (`on_auth_user_created`, `comment_votes_recalc`, `blog_comment_votes_recalc`) siguen adjuntos y `tgenabled = 'O'` — el `REVOKE` no los tocó.
  - `EXPLAIN SELECT ... WHERE title % 'iphone'` sigue usando `Bitmap Index Scan on ix_deals_title_trgm` tras mover la extensión — el operador `%` resuelve sin cambios en la app.
  - **Advisor real re-consultado**: `anon_security_definer_function_executable`, `authenticated_security_definer_function_executable`, `extension_in_public` y `auth_rls_initplan` ya **no aparecen**. Solo queda `auth_leaked_password_protection` (toggle manual de dashboard, sin API/migración disponible) — se mantiene abierto como TD-20 en `docs/project/10-technical-debt.md`.

---

### 3.tervicies  Seguridad: RLS desactivado en `scheduled_deals` (`rls_disabled_in_public`) — 2026-09-02

Supabase envió un aviso **crítico** el 31-ago: *"Table publicly accessible"* sobre el proyecto BuenChollo.

- **Diagnóstico** (consulta directa al Postgres de producción vía la conexión del backend): de las 22 tablas de `public`, **solo `scheduled_deals` tenía RLS desactivado** (0 políticas, `anon` con SELECT/INSERT/DELETE). Las otras 21 están correctas.
- **Causa raíz**: la migración `20260720120000_scheduled_deals.py` (20-jul) creó la tabla **sin** `ENABLE ROW LEVEL SECURITY`, saltándose la regla de [ADR-006](docs/adr/ADR-006-rls-service-role.md) (toda tabla nueva de `public` activa RLS en la misma migración). 2ª vez que ocurre esta clase de fallo.
- **Exposición real**: el `anon key` es público (va en el bundle del frontend). Con RLS off, cualquiera podía:
  - **Inyectar** una fila `status='programado'` con `telegram_text` / `image_url` / `affiliate_url` arbitrarios → el worker de publicaciones la habría publicado en el canal de Telegram y activado el chollo web asociado (secuestro de enlace de afiliado / contenido falso).
  - **Borrar** toda la cola de publicaciones (173 filas).
  - Sin PII de usuarios en esa tabla.
- **Solución**:
  - Migración `20260902120000_enable_rls_scheduled_deals.py`: `ALTER TABLE public.scheduled_deals ENABLE ROW LEVEL SECURITY`. RLS on + 0 políticas ⇒ `anon`/`authenticated` denegados; el backend usa la conexión de servicio (bypassa RLS) y el worker sigue operando igual.
  - Test de regresión `test_migrations_rls.py`: escanea todas las migraciones (alembic + supabase) y falla si alguna tabla de `public` se crea sin RLS. Cierra la deuda de F7.1 de ADR-006 (smoke test pendiente).
- **Despliegue**: `alembic upgrade head` en el contenedor `buenchollo-api` (prod estaba en la revisión padre `20260829140000`). Verificado tras aplicar: `scheduled_deals.rowsecurity = true`, worker leyendo/escribiendo con normalidad.
- **Verificado con el Advisor real de Supabase (2026-09-05, conector MCP autorizado)**: `get_advisors(type="security")` ya **no** reporta `rls_disabled_in_public`. `scheduled_deals` aparece ahora solo como `rls_enabled_no_policy` (nivel INFO, no crítico) — el mismo estado "RLS on, 0 políticas, denegado por defecto" que las otras 21 tablas. El aviso crítico queda cerrado.

---

### 3.duovicies  Fix: la revisión de precios de Amazon no se ejecutaba de forma automática — 2026-09-02

La tarea programada «Revisión de precios (Amazon)» solo funcionaba con el botón **Ejecutar ahora**; el ciclo automático del contenedor `buenchollo-scheduler` fallaba en silencio en cada tick horario.

- **Causa raíz**:
  - El commit `a3fc505` (cierre de TD-15/16/17, 29-ago) extrajo la creación de handlers a `factory.py` y eliminó el import de `DealRepository` de `scheduled_tasks/application/scheduler.py`, pero dejó viva la línea `deal_repo = DealRepository(session)` dentro de `_run()`.
  - Cada ejecución de `run_due_scheduled_tasks` lanzaba `NameError: name 'DealRepository' is not defined`, que el bloque `except Exception` de `_run()` capturaba, registraba como *"Fallo global del worker de tareas programadas"* y devolvía `0`. Confirmado en logs de producción (`scheduler.py` línea 71, en cada tick horario desde el deploy de `a3fc505` ~30-ago hasta el 2-sep).
  - El botón **Ejecutar ahora** no se veía afectado: usa el router FastAPI (`get_scheduled_task_service`), que sí importa `DealRepository`.
- **Solución (`db913bf`)**:
  - Reañadido el import de `DealRepository`.
  - Extraída `_build_service(session, settings)` para aislar el cableado repo + servicio de la creación del engine/sesión y poder cubrirlo con un test que no necesita BD (ningún test llegaba a esa línea: el de `_run` sale antes por falta de `DATABASE_URL`, los de `_execute_due_tasks` mockean el `service`).
  - Test de regresión `test_build_service_cablea_dependencias_sin_nameerror` en `test_scheduled_tasks_scheduler.py`.
- **Despliegue y verificación**:
  - El código va montado (`.:/app`); no requiere rebuild de imagen. `docker restart buenchollo-scheduler` → arranque limpio, 5 jobs registrados (`run_scheduled_tasks` incluido).
  - Verificado dentro del contenedor en marcha: `_build_service()` resuelve (`ScheduledTaskService`, `deal_repo` OK, handler `price_check` OK). `GET /health` → `{"status":"ok","environment":"production"}`.
  - Tests del módulo scheduler + price-check en verde (42/42).
- **Verificación funcional en producción (confirmado por Pedro, 2026-09-05)**: con la tarea en frecuencia **Diario**, el registro de ejecuciones muestra 3 corridas consecutivas tipo **AUTOMÁTICA** (una por día desde el despliegue), sin intervención manual — el ciclo automático queda confirmado end-to-end, no solo a nivel de código/logs.
- **Deuda derivada**: ver **TD-19** en `docs/project/10-technical-debt.md` — el `except Exception` de `_run()` ocultó este fallo ~3 días sin ninguna alarma.

---

### 3.unvicies  Cierre de TD-18: Refinación defensiva de la regla `no_longer_deal` en el revisor de precios — 2026-08-30

Resolución de **TD-18**, protegiendo la base de datos de borrados falsos positivos en las ejecuciones automáticas periódicas del revisor de precios:

- **Problema previo**:
  - Si Amazon omitía `savingBasis` o `discount_percentage` en la respuesta de la PA-API (algo frecuente incluso en productos con descuento activo), el handler `PriceCheckHandler._evaluate_one` marcaba el producto como `"no_longer_deal"` y lo borraba de forma indiscriminada.
- **Regla defensiva implementada**:
  - Si Amazon omite los campos de porcentaje o precio base, pero el precio actual de la tienda se mantiene dentro del rango de oferta (`current_price <= maximum_price`), **el chollo se conserva activo**.
  - Solo se marca `"no_longer_deal"` si Amazon reporta explícitamente descuento cero/negativo (`discount_percentage <= 0`), o si el precio actual iguala o supera el PVP anterior registrado en el deal (`current_price >= deal.previous_price`).
  - La condición de subida excesiva de precio (`"price_increase"`) y producto agotado (`"out_of_stock"`) siguen operando con su prioridad habitual.
- **Validación y Tests**:
  - Tests unitarios actualizados y ampliados en `test_price_check_handler.py` (13/13 pasando).
  - Suite completa de backend pasando al 100% (263 tests `pytest`).
  - `docs/project/10-technical-debt.md` actualizado con **0 ítems de deuda técnica pendientes**.

---

### 3.vicies  Selector de motor de IA en panel de autocompletar de Amazon (OmniRoute / OpenAI / Auto) — 2026-08-30

Incorporación de selector explícito de motor de IA en el panel de autocompletar de Amazon para el administrador:

- **Frontend (`buenchollo-web`)**:
  - `AmazonAutofillPanel`: Selector integrado con diseño acorde al UI System (estética terminal / bordes cyan glow / responsive) para elegir entre `OmniRoute (Modelos Gratuitos)`, `OpenAI (GPT-4o Oficial)` y `Automático (OmniRoute + Fallback)`.
  - Persistencia de la preferencia del administrador en `localStorage` (`buenchollo_ai_provider`).
  - `productsApi.previewFromUrl`: Envía el parámetro `provider` a la API (`/v1/products/preview-from-url`).
  - Tests unitarios añadidos en `AmazonAutofillPanel.test.tsx` (171 tests `vitest` en verde, build exitoso en TanStack Start / Vite).
- **Backend (`buenchollo-api`)**:
  - `ProductPreviewFromUrlRequest`: Campo opcional `provider` ("omniroute" | "openai" | "auto").
  - `OpenAICompatibleLLMClient`: Soporte directo para invocación a OpenAI oficial (`provider="openai"`) o ejecución prioritaria en OmniRoute (`provider="omniroute"`).
  - Propagación limpia a través de `PreviewProductFromUrlUseCase` -> `OpenAIAssistant` -> `ProductAIEnricher` -> `LLMClientProtocol`.
  - Tests unitarios en `test_product_preview_use_case.py` y suite completa de backend pasando con 100% de éxito (264 tests `pytest`).

---

### 3.undevicies  Blindaje de triple capa para sugerencias de categorías en Telegram — 2026-08-29

Refuerzo de resiliencia integral para garantizar que el panel de Telegram siempre entregue etiquetas sugeridas pertinentes:

- **Causa raíz del fallo intermitente**:
  - En `buenchollo-api/app/modules/telegram/api/router.py`, `asyncio.wait_for` tenía un timeout de 6.0s. Cuando los modelos gratuitos de OmniRoute experimentaban latencia o caídas, la cascada de 3 reintentos superaba los 6s y el bloque `except Exception:` descartaba las sugerencias devolviendo lista vacía `[]` antes de llegar a OpenAI.
- **Solución implementada**:
  - **Capa 1 (IA con Fast Timeout)**: `fast_free_timeout = 3.5s` en `llm_client.py` con `max_retries=0` para saltar inmediatamente a OpenAI `gpt-4o` en milisegundos si los modelos gratuitos tardan. Timeout de ruta ampliado a 10s.
  - **Capa 2 (Backend Heuristics & Synonyms)**: `TelegramAIService.extract_heuristic_tags` con mapa de sinónimos y lematización (`SYNONYM_MAP`) que rescata etiquetas canónicas si la IA falla o produce timeout en el router.
  - **Capa 3 (Frontend Client Fallback)**: `extractLocalSuggestions` en `TelegramPanel.tsx` calculando coincidencias locales inmediatas en el cliente si la red o API fallasen.
- **Verificación**: 168 tests vitest frontend y 264 tests pytest backend pasando con 100% de éxito.

---

### 3.duodevicies  Plan de optimización de rendimiento: Fase 2 (PostgreSQL Trigram, Code-Splitting y GZip) — 2026-08-29

Ejecución y validación completa de la Fase 2 de optimizaciones:

- **PostgreSQL Trigram (`pg_trgm`)**:
  - Migración Alembic `20260829140000_deals_pg_trgm_search_indexes.py` activando la extensión `pg_trgm` y creando el índice GIN `ix_deals_title_trgm` sobre `deals USING gin (title gin_trgm_ops)`.
  - Acelera las búsquedas de texto con `ILIKE '%query%'` en el buscador de la web y la API pública, evitando `Seq Scan` en PostgreSQL.
- **Code-Splitting y Carga Perezosa en Frontend**:
  - `TelegramPanel` desacoplado y cargado con `React.lazy` y `<Suspense>` en `admin.chollos.tsx`, separando su bundle en un chunk independiente bajo demanda (`TelegramPanel-*.js`).
  - Verificado con `npm run build` en TanStack Start / Vite y 28 archivos de tests `vitest` (168 tests pasando al 100%).
- **Compresión de Respuestas HTTP en FastAPI**:
  - Middleware `GZipMiddleware(app, minimum_size=500)` registrado en `buenchollo-api/app/main.py`.
  - Reduce entre un 70% y un 80% el ancho de banda transferido en listados grandes de chollos, blog y endpoints públicos.
  - Verificado con test unitario en `test_gzip_compression.py` (264 tests unitarios de backend pasando al 100%).

---

### 3.septendecies  Corrección de sugerencia de etiquetas/categorías en Telegram (case-insensitivity y normalización) — 2026-08-29

Resolución del fallo donde la IA no recomendaba etiquetas en el panel de publicación de Telegram:

- **Causa identificada**:
  - `TelegramAIService.suggest_categories` comparaba los tokens devueltos por el LLM contra el conjunto `available` con igualdad estricta sensible a mayúsculas/minúsculas (`t in allowed`).
  - Como el catálogo en `categories.json` usa PascalCase (ej: `#Auriculares`, `#Gaming`, `#SmartPhones`, `#FuentesAlimentación`) y los modelos devuelven texto en minúsculas (`#auriculares #gaming`), la comparación descartaba el 100% de las coincidencias y devolvía siempre lista vacía `[]`.
- **Solución implementada**:
  - **Normalización insensible a mayúsculas, acentos y almohadilla (`_normalize_tag`)**: Mapea cualquier variante devuelta por el LLM a su categoría canónica oficial.
  - **Extracción tolerante con expresiones regulares**: Capta etiquetas tanto si vienen en formato texto, con viñetas, comas o JSON.
  - **Fallback heurístico de rescate**: Si el motor de IA no devuelve resultados o se produce un timeout, busca coincidencias de términos clave en el título y descripción del producto contra el catálogo para asegurar siempre sugerencias pertinentes.
- **Tests añadidos**: 2 nuevos tests unitarios en `test_ai_llm_client.py` verificando normalización con acentos/minúsculas y fallback heurístico (18/18 pasando).

---

### 3.sexdecies  Cierre de deuda técnica (TD-15, TD-16, TD-17) — 2026-08-29

Resolución de los tres ítems principales de deuda técnica registrados en `docs/project/10-technical-debt.md`:

- **TD-15 (Alta) — Aislamiento y limpieza garantizada en tests de integración**:
  - `test_blog_api.py` y `test_blog_comments_api.py` ahora implementan fixtures automáticas de tracking y limpieza en cascada con `DELETE` por ID en teardown (`track_and_clean_blog_data` y `track_and_clean_comment_data`).
  - Se elimina definitivamente el riesgo de contaminar la base de datos compartida al ejecutar `pytest -m integration` en local.
- **TD-17 (Media) — Factoría centralizada de handlers de tareas programadas**:
  - Creado `app/modules/scheduled_tasks/application/factory.py` con la función `build_task_handlers(session, settings)`.
  - Unifica la instanciación de handlers entre el router FastAPI (`/admin/scheduled-tasks`) y el worker en segundo plano (`buenchollo-scheduler`), eliminando la duplicación hardcodeada (SRP/DRY).
- **TD-16 (Baja) — Snapshot de restauración completo en `scheduled_task_run_items`**:
  - Añadidas las columnas `previous_price`, `discount_percentage` y `short_description` a la tabla `scheduled_task_run_items` mediante migración Alembic `20260829120000_scheduled_task_run_items_discount_fields.py`.
  - Mapeadas en el modelo ORM, en la entidad `Candidate`, en el handler de precios y en `ScheduledTaskService.restore_item` para que al restaurar un chollo borrado conserve todos sus badges de descuento y eslogan originales.
- **Suite de tests verificada**: **260 tests unitarios backend en verde** + **168 tests vitest frontend en verde** (428 tests automáticos en total).

---

### 3.quindecies  Failover resiliente a OpenAI oficial ante fallos/respuestas vacías y optimización de latencia — 2026-08-29

Resolución de incidencias en la generación de textos de Telegram y preview de Amazon causadas por
indisponibilidad o timeouts en el gateway local de modelos gratuitos:

- **Problema identificado**:
  - Los modelos gratuitos en OmniRoute devolvían errores 404/502 o respuestas vacías sin salida utilizable.
  - El cliente agnóstico no interpretaba respuestas vacías como fallo para pasar al siguiente modelo y no tenía implementado el failover a la API oficial de OpenAI (`https://api.openai.com/v1`).
  - La librería de OpenAI aplicaba timeouts de 30s + `max_retries=2` con backoff por modelo gratuito caído, sumando más de 90s por llamada y provocando timeouts HTTP 524 en Cloudflare / navegador.
- **Solución implementada**:
  - **Umbral de fallos/respuestas vacías (`ai_max_empty_responses=3`)**: Detecta texto en blanco o JSON no parseable y tras 3 intentos fallidos consecutivos enruta de inmediato a OpenAI oficial (`OPENAI_API_KEY` y `OPENAI_MODEL=gpt-4o`).
  - **Timeouts rápidos para modelos gratuitos**: `fast_free_timeout = min(ai_timeout_seconds, 6.0)` y `max_retries=0` para saltar de inmediato al siguiente modelo o a OpenAI sin retener la petición.
  - **Protección con `asyncio.wait_for`** en `/v1/telegram/generate` para que la plantilla de post se entregue siempre en milisegundos sin bloquearse por la IA.
  - **Plantilla base de rescate en el frontend** ([`TelegramPanel.tsx`](buenchollo-web/src/features/telegram/components/TelegramPanel.tsx)) y en `ProductAIEnricher` para que el formulario y el panel de Telegram nunca queden en blanco ante cualquier fallo de red.
- **Despliegue y validación**:
  - Rebuild y restart en el NAS completados vía SSH.
  - Validado en producción con respuesta `200 OK` y health check verificado.

---

### 3.quaterdecies  Rebuild en NAS + corrección de APP_ENV en producción — 2026-08-15

Tras el § 3.terdecies, despliegue real del motor de IA unificado en el NAS y
auditoría rápida de la configuración de producción encontrada en el camino.

- **Rebuild**: `buenchollo-api`/`buenchollo-scheduler`/`cloudflared` reconstruidos
  y reiniciados vía SSH siguiendo [`docs/guides/NAS-SSH.md`](docs/guides/NAS-SSH.md).
  Sin incidentes: `alembic upgrade head` limpio, healthcheck OK,
  `https://api.buenchollotech.com/health` → 200.
- **Hallazgo de camino**: el directorio real del proyecto en el NAS
  (`/volume1/NAS-DRIVE-PEDRO/IA/02_Proyectos/WEB-Buenchollo/BuenCholloTech/buenchollo-api`)
  es el **mismo recurso de red** que `N:`/`Z:` en la máquina de desarrollo — no
  hace falta `tar`+`scp` para este proyecto en concreto, el NAS ya ve el código
  en tiempo real. Hay que tener cuidado de no confundirlo con
  `/volume1/docker/buenchollo-auto/`, un proyecto viejo y no relacionado (bot de
  scraping con sesión de Telegram + SQLite) que también contiene "buenchollo" en
  la ruta.
- **Config drift encontrado y corregido**: el `.env` del NAS tenía
  `APP_ENV=local` en vez de `production` (desde antes de esta sesión, no
  relacionado con el rebuild). Efecto real medido en logs:
  - `effective_cors_origins` (`config.py:72-95`) añadía automáticamente
    `localhost:8081/8082/5173` a la lista de orígenes permitidos de la API
    real, con `allow_credentials=True`, porque esa rama solo se activa cuando
    `app_env != "production"`.
  - `SecurityHeadersMiddleware` no mandaba cabecera HSTS (`main.py:110-112`)
    — mitigado en parte porque Cloudflare ya aplica HSTS a nivel de borde.
  - `/health` reportaba `"environment":"local"`, confuso para monitorización.
  - Corregido: `APP_ENV=production` en el `.env` del NAS + recreación de
    contenedores. Verificado: `/health` → `"environment":"production"`,
    `CORS origins configurados` → solo los 3 dominios reales, sin los
    `localhost:*` extra.
- **Sin cambios de código para este fix** (solo `.env` del NAS): no hay commit
  asociado, queda registrado aquí como único rastro.

---

### 3.terdecies  Validación local de OmniRoute, incidente de entorno y optimización de latencia — 2026-08-15

Sesión de verificación end-to-end de la migración del § 3.duodecies / ADR-013
(llamadas de IA de Telegram y preview de Amazon movidas de OpenAI a OmniRoute).
Antes de poder probarlo hubo que resolver dos problemas de entorno no
relacionados con el código de la feature:

- **Incidente "Antigravity"**: otro agente de IA (Google Antigravity), en un
  intento fallido de arrancar `buenchollo-web` durante ~1h, convirtió el
  proyecto de TanStack Start (SSR) en una SPA manual: añadió `appType: "spa"`
  a `vite.config.ts` y creó `index.html` + `src/main.tsx` (bootstrap
  `ReactDOM.createRoot` que no existían en el proyecto). Resultado: la página
  cargaba visualmente pero **ningún botón respondía** (dos sistemas de
  hidratación compitiendo por el DOM). Revertido (`git restore` + borrado de
  los ficheros nuevos).
- **Bug de entorno real, no relacionado con Antigravity**: tras revertir,
  TanStack Start seguía devolviendo `Cannot GET /` en local. Causa: la máquina
  tiene `N:` y `Z:` mapeadas a la **misma** ruta UNC del NAS
  (`\\Zambu-nas\nas-drive-pedro`); lanzar `npm run dev` desde `N:` hace que
  Vite/TanStack Start mezclen rutas `N:` y `Z:` para el mismo módulo y el SSR
  se rompe en silencio. Fix: arrancar siempre desde `Z:`, y añadir un alias
  `@` explícito de respaldo en `vite.config.ts` (`resolve.alias`) porque
  `vite-tsconfig-paths` tampoco resuelve `@/*` de forma fiable en esta unidad
  de red duplicada.

Con el entorno saneado, se verificó **con logs reales del backend** que las
llamadas de IA van a `http://192.168.1.3:20128/v1/chat/completions`
(OmniRoute), ninguna a `api.openai.com`; el fallback en `effective_ai_base_url`
(`config.py`) solo cae a OpenAI si `AI_BASE_URL` está vacío, no como failover
en caliente si OmniRoute deja de responder — queda documentado por si se
quiere ese failover real en el futuro.

**Optimización de latencia real encontrada probando "Autocompletar desde
Amazon"**: `/products/preview-from-url` encadena Amazon PA-API + Supabase + 2
llamadas secuenciales a OmniRoute (copywriting + categorización), 20–45s
totales — muy por encima del timeout de 15s de `apiClient` (fijado en el
AUDIT M-06 del § 3.septies). Fix de dos partes:

- `ProductAIEnricher.enrich_product()`
  (`buenchollo-api/app/modules/ai/infrastructure/product_enricher.py`)
  paraleliza copywriting y categorización con `ThreadPoolExecutor` — son
  independientes entre sí — y corta esa parte de ~40s a ~14s.
- Aun paralelizado, 14s sigue al borde del timeout global; `previewFromUrl`
  (`buenchollo-web/src/services/api/products.ts`) pasa ahora un `AbortSignal`
  propio de 45s solo para esta ruta, sin tocar el límite de 15s del resto de
  la app.

**Nueva guía operativa**: [`docs/guides/NAS-SSH.md`](docs/guides/NAS-SSH.md) —
acceso SSH al NAS y rebuild/redeploy de `buenchollo-api` sin `git` en el NAS
(tar + scp + docker-compose), trasladada desde fuera del repo para que quede
versionada y cargada automáticamente por Claude Code.

- **Tests**: 257 unitarios backend + 168 frontend en verde tras los cambios
  (ninguno nuevo añadido — sesión de verificación/fix de entorno, no de
  feature nueva).
- **Sin deuda técnica nueva.**

---

### 3.duodecies  Motor de IA Unificado desacoplado (OmniRoute / OpenCode / Fallback modelos gratuitos) — 2026-08-12

Eliminación de la dependencia de pago directo a OpenAI para operaciones de copywriting y categorización,
y creación de la infraestructura base para el futuro Chatbot conversacional de recomendaciones en la web (ADR-013).

- **Qué hace**: Centraliza todas las llamadas de IA del backend a través de un gateway OpenAI-compatible
  (**OmniRoute** en `http://127.0.0.1:20128/v1`, **OpenCode**, **Groq free tier**, **OpenRouter free models**,
  o **Ollama**), eliminando costes por tokens de OpenAI para operaciones deterministas de preview y Telegram.
- **Backend**:
  - Nuevo módulo `app/modules/ai/` con entidades (`AIProductEnrichment`, `AIChatMessage`, `AIChatResponse`),
    puertos (`LLMClientProtocol`, `ProductEnricherProtocol`, `TelegramAIServiceProtocol`, `DealRecommenderProtocol`)
    y adaptadores de infraestructura.
  - `OpenAICompatibleLLMClient`: cliente asíncrono y síncrono agnóstico con **fallback automático multi-modelo**
    en cascada (ante errores 429 Rate Limit o indisponibilidad) y **extractor de JSON defensivo**
    (`extract_json_payload`) tolerante a bloques markdown, trailing commas y texto conversacional.
  - `ProductAIEnricher`: generación de eslogan corto, descripción web en markdown, texto para Telegram
    y categorización taxonómica.
  - `TelegramAIService`: sugerencia de hashtags para Telegram validados contra el catálogo.
  - `DealRecommenderAssistant`: motor conversacional base para el futuro **Chatbot Web**, preparado para
    inyectar contexto de ofertas activas y responder con recomendaciones personalizadas.
  - `app/modules/products/infrastructure/openai_client.py` refactorizado como facade sobre `ProductAIEnricher`.
  - `app/modules/telegram/application/post_generator.py` y `telegram/api/router.py` actualizados para inyectar
    el servicio de IA desacoplado.
- **Configuración**: Variables `AI_PROVIDER`, `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, `AI_FALLBACK_MODELS`,
  `AI_TEMPERATURE`, `AI_TIMEOUT_SECONDS` en `app/core/config.py` y `.env.example`, con retrocompatibilidad
  transparente si existe `OPENAI_API_KEY`.
- **Tests**: 13 nuevos tests unitarios en `test_ai_llm_client.py` (JSON extraction, fallback multi-modelo,
  copywriting, categorización, sugerencia de hashtags, chatbot) + 14 tests de regresión en verde.

---

### 3.undecies  Motor de tareas programadas + revisión de precios — 2026-08-10

Feature nueva de punta a punta: primer motor genérico de **tareas programadas** en el
backend, con la revisión periódica de precios de Amazon como primera tarea registrada.
Spec y plan completos en [`docs/superpowers/specs/2026-08-09-tareas-programadas-revision-precios-design.md`](docs/superpowers/specs/2026-08-09-tareas-programadas-revision-precios-design.md)
y [`docs/superpowers/plans/2026-08-09-tareas-programadas-revision-precios.md`](docs/superpowers/plans/2026-08-09-tareas-programadas-revision-precios.md)
(13 tareas TDD + revisión final de rama con 2 rondas de arreglo).

- **Qué hace**: detecta chollos `active` sin `expires_at` y con ASIN, consulta Amazon
  (`AmazonProductClient`) y borra los que ya no son oferta válida (sin stock, ya no
  tiene descuento, o precio subió más de una tolerancia % configurable). Cada borrado
  queda en un registro con snapshot completo, restaurable desde el panel.
- **Backend**: 3 tablas nuevas (`scheduled_tasks`, `scheduled_task_runs`,
  `scheduled_task_run_items` — migración `20260809120000`, solo aditiva, RLS activado,
  sin tocar `deals`), módulo `scheduled_tasks/` con handler registrable
  (`PriceCheckHandler`), job horario de auto-chequeo en el scheduler existente
  (`buenchollo-scheduler`), y 9 endpoints admin (`/v1/admin/scheduled-tasks/*`).
- **Frontend**: nueva sección `/admin/tareas-programadas` — configuración con edición
  inline (draft local + commit en blur), "ejecutar ahora" con diálogo de confirmación
  mostrando la lista antes de borrar, tabla de registros con selección múltiple y
  borrado en bloque, y restauración por chollo desde el detalle de cada registro.
- **Seguridad de despliegue**: la fila sembrada por la migración tiene `enabled=false`
  — el modo automático no borra nada hasta que un admin lo active explícitamente desde
  el panel. Todos los endpoints exigen `require_admin`; los 2 más destructivos
  (`delete_run`, `bulk_delete`) quedan en `admin_audit_log`.
- **Tests**: 235 unitarios + 37 de integración en verde (venv del proyecto). Los tests
  de integración corren contra la Supabase de producción real (no hay BD de test
  aislada todavía — ver deuda técnica) y quedan protegidos con limpieza `try/finally`.
- **Deuda técnica abierta tras esta feature**: ver `docs/project/10-technical-debt.md`
  (DB de test aislada, ajuste de la regla `no_longer_deal` antes de activar el modo
  automático, snapshot de restauración incompleto, y el registro `TASK_HANDLERS`
  hardcodeado en dos sitios en vez de una fábrica genérica real).

**Deploy y validación en producción (mismo día)** — migración aplicada en la Supabase
real (aditiva, sin incidentes), merge `develop → main` y reinicio del contenedor NAS.

Al probar "Ejecutar ahora" por primera vez con datos reales apareció un bug: con
**197 chollos candidatos** en producción, `PriceCheckHandler.evaluate()` consultaba
Amazon **uno a uno** (197 llamadas HTTP secuenciales), agotando el timeout de 15 s del
frontend ("signal timed out"). Fix aplicado el mismo día:

- `AmazonProductClient.get_product_previews()` — una sola petición por lote de hasta
  `MAX_ITEMS_PER_REQUEST=10` ASIN (límite documentado de `GetItems` en PA-API 5) en vez
  de una llamada por producto. `PriceCheckHandler.evaluate()` trocea los deals en lotes
  de ese tamaño; la resiliencia ante fallos de Amazon (try/except que no aborta el
  ciclo) pasa a ser por lote en vez de por deal. Con 197 candidatos: ~20 llamadas en vez
  de 197. +9 tests (244 unitarios + 37 integración en verde).
- Toast añadido cuando "ejecutar ahora" no encuentra candidatos (antes no avisaba de
  nada, contradiciendo el spec).

**Validado en producción por el usuario**: ciclo completo probado con datos reales —
ejecutar (89 candidatos) → revisar lista → eliminar → restaurar un elemento → volver a
ejecutar → detecta correctamente el restaurado de nuevo. QA de navegador (antes
pendiente) queda cubierto por esta validación manual real. Tarea dejada **activada**
(`enabled=true`, frecuencia semanal) por el usuario al cierre de la sesión.

---

### 3.decies  Rediseño de Notificaciones & Alertas Recomendadas — 2026-08-09

Sprint enfocado en la experiencia de usuario para alertas y notificaciones in-app:

- **Popover de Notificaciones flotante ([NotificationsPopover.tsx](buenchollo-web/src/features/notifications/components/NotificationsPopover.tsx))**:
  - Reemplaza la redirección a página completa `/notificaciones` desde el icono de campana del Header.
  - Cabecera en azul corporativo (`#156287` / `sky`) con botón **"Marcar todas como leídas"** que aparece cuando existen notificaciones sin leer (`unread > 0`), ejecutando `POST /notifications/mark-read` e invalidando reactivamente queries de React Query.
  - Lista interactiva con scroll, icono circular `(i)`, título, fecha formateada (`d/m/yyyy`), descripción y navegación directa al chollo al hacer click.
  - Test unitarios e integración añadidos en [NotificationsPopover.test.tsx](buenchollo-web/src/features/notifications/components/NotificationsPopover.test.tsx).

- **Bloque de Alertas Recomendadas contextuales ([RecommendedAlertsBlock.tsx](buenchollo-web/src/features/alerts/components/RecommendedAlertsBlock.tsx))**:
  - Ubicado entre los *Chollos relacionados* y la sección de *Comentarios* en [chollo.$slug.tsx](buenchollo-web/src/routes/chollo.$slug.tsx).
  - Genera sugerencias contextuales automáticas basadas en el producto actual: modelo/término específico, marca, tienda, y categoría.
  - Presentación visual rica con imágenes reales del producto (`deal.image_url`), logos oficiales de tiendas y marcas reconocidas, e iconos temáticos con colores vibrantes por categoría.
  - Tarjeta especial `+ Otra alerta` con botón `Personalizar` que navega a `/alertas/nueva`.
  - Suscripción y activación en un clic con estado sincronizado (`Activar alerta` ↔ `✓ Alerta activa`).
  - Test unitarios e integración en [RecommendedAlertsBlock.test.tsx](buenchollo-web/src/features/alerts/components/RecommendedAlertsBlock.test.tsx).

---

### 3.septies  Estabilización post-auditoría — 2026-07-16

Auditoría técnica completa en [`docs/archive/AUDIT_REPORT-2026-07.md`](docs/archive/AUDIT_REPORT-2026-07.md) (veredicto:
*listo para continuar con correcciones menores*; 0 críticos). Fase 1 ejecutada
el mismo día:

- **TD-01 cerrado** — cifras de tests fijadas por fin bajo Python 3.11:
  **208 totales** = 109 pytest (100 unit + 9 integración) + 91 vitest + 8 E2E.
  Propagado a README raíz (badge + § tests), `buenchollo-api/README.md`,
  `docs/project/06` y `docs/master/06`.
- **TD-02 cerrado** — ya estaba resuelto en código: `config.py` usa
  `Annotated[list[str], NoDecode]` + validator, que acepta CSV. Solo quedaba
  cerrar el registro.
- **TD-10 cerrado** — verificado en código: 0 `supabase.from()/rpc()` en el
  frontend; la afirmación correcta es la del README (ADR-002 100%).
- **AUDIT H-01 cerrado** — `npm audit fix` + vitest 2→4: **0 vulnerabilidades**
  npm (prod y dev) y pip-audit ya estaba a 0. Suite verificada tras el bump.
- **AUDIT M-06/L-01 cerrados** — timeout de 15 s en `apiClient` y limpieza de
  import muerto.
- **Deuda nueva registrada**: TD-12 (JWT round-trip, era H-02), TD-13 (Docker
  root, era M-01), TD-14 (sin error tracking frontend, era M-04) y dependencia
  scheduler↔workers anotada en TD-11 (era M-07).

Pendiente de la auditoría: split de `admin.chollos.tsx` (TD-03) y CI con
Postgres para integración (TD-07).

**Cierre TD-12 (mismo día, 2026-07-16)** — validación JWT local con JWKS:
`get_current_user` verifica firma ES256/exp/aud en local contra el JWKS
público de Supabase (PyJWT + caché 1 h), con soporte HS256 opcional
(`SUPABASE_JWT_SECRET`) y fallback a `get_user` remoto si no hay material
de firma. Elimina un round-trip HTTP a Supabase **por cada request
autenticada** y el SPOF de Auth. Decisión y trade-offs en
[`ADR-010`](docs/adr/ADR-010-validacion-jwt-local.md). +16 tests
(9 de JWT: firma inválida, expiración, audiencia, fallback, JWKS caído; 7 de parseo CORS_ORIGINS) →
**suite total: 224** (125 pytest + 91 vitest + 8 E2E).
De propina: el smoke de arranque destapó que un `.env` con `CORS_ORIGINS` en
formato JSON (el que exigía el antiguo TD-02) se parseaba como CSV crudo tras
el fix `NoDecode`, dejando corchetes en los orígenes. El validator ahora
acepta **ambos formatos** (JSON array y CSV), así que no hay que tocar los
`.env` desplegados.

---

### 3.quinquies  Módulo de Calidad QA — 2026-05-30

Sprint dedicado al módulo de Calidad del software. El backend ya
tenía cobertura razonable (87 pytest); el frontend no tenía una sola
línea de test. Tras este sprint:

- Vitest + Testing Library + jsdom configurados con coverage estratégico.
- 72 tests Vitest verde (59 unit CORE + 13 integration user-centric).
- Playwright + chromium con 8 E2E críticos.
- Husky con pre-commit (lint + typecheck) y pre-push (test:run).
- CI GitHub Actions ampliado: 4 jobs (backend, frontend con coverage,
  e2e Playwright). Artifacts subidos en cada run / en fallo.
- Documento [`docs/master/06-calidad-testing-y-refactorizacion.md`](docs/master/06-calidad-testing-y-refactorizacion.md) con pirámide, coverage
  100/80/0, métricas accionables y deuda asumida documentada.

Suite total automatizada: **158 tests verde**.

---

### 3.quater  Hardening arquitectónico F1–F7 — 2026-05-30 (release v1.0.0)

Sprint final de hardening definido en [`docs/reference/PLAN_ARQUITECTURA.md`](docs/reference/PLAN_ARQUITECTURA.md).
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
- `F7.1` [`docs/reference/SMOKE_TEST.md`](docs/reference/SMOKE_TEST.md) con guion exhaustivo manual
  pre-release (10 secciones, ~50 checks).
- `F7.2` Esta sección.
- `F7.3` Tag `v1.0.0`.

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

### 3.duodecies  Incidente: artículos de blog falsos publicados en producción — 2026-08-10

El usuario detectó decenas de artículos de blog que no había creado, visibles en
`buenchollotech.com`. Diagnóstico confirmado con consultas de solo lectura directas
contra la Supabase real (mismo `.env` que usa el backend):

- **Causa**: `buenchollo-api/.env` apunta a la Supabase de **producción** real
  (`APP_ENV=production`), sin base de datos de test aislada (**TD-15**, ya conocida).
  Entre el 2026-08-09 21:42 y el 2026-08-10 14:14 se ejecutó en local varias veces
  (~7 corridas) `pytest -m integration` sobre `test_blog_api.py` y
  `test_blog_comments_api.py`. A diferencia de `test_scheduled_tasks_api.py` (que sí
  limpia con `try/finally` — ver § 3.undecies), estos dos módulos **no limpian los
  datos que crean**, y varios tests dejan el post en `status=published`, visible
  públicamente.
- **Impacto real** (confirmado por consulta directa antes de borrar): de 135
  `blog_posts` en producción, 126 eran de test (títulos fijos repetidos: *"Guía de
  compra de auriculares 2026"*, *"Artículo con comentarios"*, *"Solo título"*; slugs
  `<prefijo>-<8 hex>`); de 151 `blog_categories`, 144 eran de test (`cat-<8 hex>`);
  27 `blog_comments` y su cascada de votos, todos sobre posts falsos. Los 9 posts y 7
  categorías reales del usuario quedaron intactos y sin ningún comentario/voto
  contaminado.
- **No fue una cuenta comprometida ni generación por IA**: el `author_id` de los
  posts de test coincide con el UUID real del admin porque el `MockUser` de los tests
  lo hardcodea así para satisfacer la FK `blog_posts.author_id → profiles` contra la
  BD compartida.
- **Remediación aplicada**: backup JSON de las 126+144+27 filas antes de borrar,
  borrado en una única transacción con guarda de recuento (aborta con rollback si no
  quedan exactamente 9 posts / 7 categorías), verificado también contra la API
  pública real (`GET /v1/blog/posts` → 9 resultados, los correctos).
- **Deuda técnica reabierta**: TD-15 pasa a 🔴 Alta — el mismo riesgo puede repetirse
  con cualquier módulo de tests de integración que no tenga limpieza `try/finally` (o,
  mejor, con una BD de test aislada de verdad). Pendiente: aislar la BD de test o, como
  mínimo, añadir limpieza defensiva a `test_blog_api.py` y `test_blog_comments_api.py`.

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

#### Capas `application/` — estado real (corregido 2026-07-18, cierre TD-04)

```
deals/        ✅  api → DealService → DealRepository
products/     ✅  api → PreviewProductFromUrlUseCase → adapters
users/        ✅  api → UserService → ProfileRepository
telegram/     ✅  api → TelegramPostGenerator/TelegramBot → infrastructure
categories/   ⚠️  api → repository  (sin application layer, YAGNI deliberado)
stores/       ⚠️  api → repository  (sin application layer, YAGNI deliberado)
```

`users/` ya tiene su capa completa (`user_service.py`) — el párrafo anterior de
esta página decía lo contrario, era información desactualizada. `categories/` y
`stores/` omiten `application/` a propósito: hay una nota arquitectónica en cada
router (F2.5, 2026-05-27) explicando que son CRUD sin reglas de negocio reales
todavía, y que crear un service que solo delegue sería boilerplate puro (YAGNI).
Extraer el service cuando aparezca la primera regla real, siguiendo el patrón de
`users/application/user_service.py`.

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
- [ ] **Ejecutar `docs/reference/SMOKE_TEST.md` completo** antes del go-live al dominio definitivo

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
```

---

## 7. Arquitectura objetivo (referencia)

```
buenchollo-api/
├── app/
│   ├── core/           # config, database, security, logging
│   └── modules/
│       ├── ai/            # domain (entities, ports) + infrastructure (llm_client, product_enricher, telegram_ai, deal_recommender)
│       ├── deals/
│       │   ├── domain/        # Deal, DealVote, Favorite — modelos ORM + lógica pura
│       │   ├── application/   # DealService, DealCleanerService
│       │   ├── infrastructure/# DealRepository
│       │   └── api/           # router (solo HTTP) + schemas Pydantic
│       ├── products/
│       │   ├── domain/        # ProductPreview, Protocols (DIP)
│       │   ├── application/   # PreviewProductFromUrlUseCase
│       │   └── infrastructure/# AmazonClient, ProductAIEnricher adapter (OpenAIAssistant facade)
│       ├── telegram/          # api + application (post_generator) + infrastructure (bot, category_repo)
│       ├── scheduled_tasks/   # motor genérico tareas programadas + price_check
│       ├── scheduled_deals/   # programación y publicación de chollos
│       ├── blog/              # blog con editor Tiptap y posts
│       ├── blog_comments/     # comentarios de blog
│       ├── categories/        # catálogo maestro
│       ├── stores/            # catálogo maestro
│       ├── users/             # /auth/me, Profile model
│       ├── alerts/            # alertas de usuario y matcher
│       └── notifications/     # notificaciones in-app

buenchollo-web/
├── src/
│   ├── services/api/  # Única capa que habla con FastAPI (apiClient)
│   ├── routes/        # Páginas — solo llaman a services/api/ o Supabase Auth/Storage
│   ├── components/    # UI sin lógica de datos
│   └── hooks/         # useAuth, otros hooks de estado
```
