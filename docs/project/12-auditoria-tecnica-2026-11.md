# 🔍 12 · Auditoría técnica — noviembre de 2026

> **TL;DR** · Auditoría completa del proyecto con el enfoque de un comprador técnico
> (rama `develop`, commit `a127527`, 2026-11-18). **El código es sólido y profesional**
> (arquitectura coherente, seguridad por encima de la media, 83 % de cobertura en el
> backend). **Lo débil es la operación**: despliegue manual sobre la copia de trabajo,
> sin backups programados ni monitorización externa, y conocimiento concentrado en el
> autor. Veredicto: **comprable**, condicionado a cerrar los 8 hallazgos de prioridad
> alta (casi todos de esfuerzo pequeño).

---

## 1. Alcance y método

| Aspecto | Detalle |
|---|---|
| Código | Backend `buenchollo-api/` (≈ 17 300 sentencias Python, 19 módulos, 124 endpoints) y frontend `buenchollo-web/` (≈ 39 000 líneas TS/TSX, 40 rutas, 11 features) |
| Además | 19 ADR, CI de GitHub Actions, Docker/NAS, Cloudflare, documentación |
| Equipo | Seis revisiones en paralelo (arquitectura backend, arquitectura frontend, seguridad, calidad de código backend, testing/CI/operación, métricas) y una verificación final de todos los hallazgos altos contra el código y, cuando era de solo lectura, contra producción |
| Herramientas | `pytest --cov`, Vitest con cobertura, `tsc`, ESLint, `vite build`, `pip-audit`, `npm audit` (script `audit:prod`), `ruff`, `radon`, `alembic heads` |
| Límites | Revisión estática más medición. Sin pruebas de carga, sin pentest activo y sin acceso al panel de Supabase ni al de Cloudflare |

**Convenciones.** Severidad: **Alta** (riesgo real para datos, disponibilidad, SEO o la
continuidad del servicio), **Media** (deuda que encarece el mantenimiento o puede fallar
en un caso concreto), **Baja** (higiene). Esfuerzo: **S** (≤ 1 día), **M** (2–5 días),
**L** (más de una semana). ✅ = verificado durante la auditoría; ◐ = deducido del código,
sin reproducir. Los ID entre paréntesis remiten a la deuda ya registrada en
[`10-technical-debt.md`](10-technical-debt.md).

---

## 2. Resumen ejecutivo

| Área | Nota | Comentario |
|---|---|---|
| Arquitectura backend | **Alta** | Monolito modular con cuatro capas respetadas en los 19 módulos; dominio limpio; errores de dominio centralizados |
| Arquitectura frontend | **Media** | TypeScript estricto sin `any`, ADR-002 cumplido; pero componentes de 700–960 líneas y dos patrones de carga de datos |
| Seguridad | **Alta** | Sin IDOR, sin endpoints de escritura desprotegidos, SSRF tratado, XSS cerrado por diseño. Riesgo global bajo-medio |
| Calidad de código | **Media-Alta** | Legible y tipado; deuda de DRY concentrada en pocos puntos (cliente LLM, utilidades repetidas) |
| Testing | **Media** | Backend 83 % (812 unitarios + 59 de integración contra Postgres); frontend 38 % global; E2E sin contrato real con la API |
| SEO y rendimiento | **Media** | SSR, JSON-LD y sitemap correctos; pero *soft 404*, logo de 588 KB y bundle inicial de 776 kB |
| Operación y continuidad | **Baja** | Sin CD del backend, sin backups programados, sin alertas de caída, `main` sin protección de rama |

**Riesgos que un comprador debe conocer antes de firmar:**

1. **Despliegue y recuperación** (AUD-02, AUD-03): producción ejecuta la copia de trabajo
   montada desde un share de red, no hay rollback probado y los backups son manuales y
   se guardan en el mismo NAS.
2. **Visibilidad** (AUD-04): si el NAS, el túnel o el scheduler caen, nadie se entera
   hasta que alguien mira.
3. **Una trampa en las migraciones** (AUD-01): un `alembic revision --autogenerate`
   generaría el borrado de seis tablas con datos reales.
4. **SEO** (AUD-07): las fichas inexistentes y las caídas de la API se sirven con
   HTTP 200, lo que Google trata como *soft 404*.

Ninguno exige rediseñar nada: siete de los ocho hallazgos de prioridad alta son de
esfuerzo pequeño.

---

## 3. Métricas objetivas

| Métrica | Valor |
|---|---|
| Tests backend | 812 unitarios + 59 de integración (Postgres real en CI); 749 funciones de test en 81 ficheros |
| Cobertura backend | **83 %** (17 270 sentencias, 2 918 sin cubrir) |
| Tests frontend | 492 en 69 ficheros (Vitest) + 12 specs E2E (Playwright) |
| Cobertura frontend | **38 %** de líneas global; ≥ 90 % en `src/lib` (umbral obligatorio) |
| Tipado frontend | `tsc` sin errores; 0 `any`, 0 `@ts-ignore` |
| Lint frontend | 0 errores, 9 avisos (`react-refresh/only-export-components`) |
| Vulnerabilidades | `pip-audit`: ninguna. `npm audit` (producción): ninguna salvo la excepción aceptada TD-50 |
| Migraciones | Cadena lineal de 26 revisiones, una sola cabeza (`20261118120000`), todas con `downgrade` |
| Bundle | Chunk inicial 776 kB (235 kB gzip). Admin aislado en chunks propios (editor de blog 503 kB, analítica 427 kB) |
| Complejidad | 10 funciones con complejidad ciclomática ≥ 21 (radon D–F), la mayor `map_td_product` (53) |
| Marcadores | 0 TODO/FIXME reales |

---

## 4. Puntos fuertes

- **Arquitectura coherente y documentada.** Los 19 módulos siguen `api → application →
  domain ← infrastructure`; ningún `domain/` importa FastAPI ni clientes HTTP; ningún
  router lanza `HTTPException`; los errores de negocio heredan de `DomainError` y un
  único handler los traduce (`main.py`). 19 ADR explican las decisiones.
- **Seguridad por diseño.**
  - JWT validado en local por JWKS (ES256/RS256) con audiencia; el rol admin se consulta
    en BD en cada petición.
  - Todos los endpoints con datos privados filtran por el `user_id` del token: no hay IDOR.
  - Anti-SSRF en las tres salidas a URLs externas (IPs privadas, allowlist de hosts por
    salto, límites de tamaño y tiempo).
  - Imágenes reencodadas a WebP con Pillow y límite de píxeles; nombres generados por el
    servidor.
  - Blog validado como JSON de TipTap con lista cerrada de nodos y renderizado sin HTML.
  - SQL siempre parametrizado; `Cache-Control: no-store` por defecto con allowlist exacta.
  - CI con `gitleaks` sobre todo el historial, `pip-audit --strict` y `npm audit` con
    excepciones que caducan.
- **Base de datos preparada para PgBouncer** (`statement_cache_size=0`, pool acotado,
  `pool_pre_ping`), índices trigram y compuestos, migraciones idempotentes.
- **Tareas en segundo plano robustas.** Contenedor dedicado, `max_instances=1`,
  `FOR UPDATE SKIP LOCKED`, marcas atómicas y advisory locks.
- **Frontend estricto.** `strict`, `noUncheckedIndexedAccess`, `no-explicit-any: error`;
  un único `fetch` en `apiClient` con timeouts; SSR con JSON-LD serializado de forma
  segura, sitemap dinámico, RSS y `noindex` en páginas privadas; dependencias pesadas
  confinadas al panel de admin.
- **Observabilidad básica bien hecha.** Logs JSON con `request_id`, Sentry sin PII,
  `/health` y `/health/ready` separados, contenedor no-root con `HEALTHCHECK`.
- **Registro de deuda técnica vivo**, con escenarios concretos y fechas.

---

## 5. Hallazgos

### 5.1 Prioridad alta

#### AUD-01 · Alembic no conoce seis tablas: un autogenerate las borraría
- **Severidad** Alta · **Esfuerzo** S · ✅
- **Dónde**: `buenchollo-api/app/core/base.py:20-33`.
- **Evidencia**: el registro de modelos no importa `scheduled_tasks`,
  `scheduled_task_runs`, `scheduled_task_run_items`, `deal_submissions`, `blog_comments`
  ni `blog_comment_votes`. Comprobado importando todos los `domain/models.py`: esas seis
  tablas quedan fuera de `Base.metadata`.
- **Impacto**: la guía `docs/guides/MIGRATIONS.md` recomienda `alembic revision
  --autogenerate`, que generaría `drop_table` para las seis. La API ejecuta `alembic
  upgrade head` al arrancar, así que una revisión poco cuidadosa llega sola a producción.
- **Propuesta**: importar los seis modelos en `base.py` y añadir un test que recorra
  `app/modules/*/domain/models.py` y compare con `Base.metadata`.

#### AUD-02 · Producción ejecuta la copia de trabajo; sin CD ni rollback probado (TD-31)
- **Severidad** Alta · **Esfuerzo** M · ✅
- **Dónde**: `buenchollo-api/docker-compose.yml` (`.:/app`), `docs/project/08-deployment.md`,
  `docs/guides/NAS-SSH.md`.
- **Evidencia**:
  - El contenedor monta el share de red; cualquier reinicio del NAS carga lo que haya
    en esa carpeta en ese momento.
  - El "Rollback rápido" de `08-deployment.md` usa `git checkout` en el NAS, mientras
    `NAS-SSH.md` dice que el NAS no tiene git. Hay tres procedimientos distintos.
  - Ningún job de CI construye la imagen Docker: una dependencia nueva solo se descubre
    al reiniciar en producción.
- **Propuesta**: imagen con el código dentro y versión etiquetada (sin volumen de código),
  un único runbook de despliegue y rollback verificado, y un `docker build` en CI.

#### AUD-03 · Backups manuales, en el mismo NAS y sin restauración probada
- **Severidad** Alta · **Esfuerzo** S-M · ✅
- **Evidencia**: los únicos `pg_dump` son los previos a despliegues con migraciones
  (anotados en `PROJECT_STATUS.md`). No hay backup periódico, retención, copia fuera del
  NAS, procedimiento de restauración, RPO ni RTO. El plan de Supabase (y si incluye
  backups o PITR) no está documentado. El `.env` de producción solo existe en el NAS:
  perderlo es perder todas las credenciales.
- **Propuesta**: `docs/guides/BACKUP-RESTORE.md` con el procedimiento probado, `pg_dump`
  programado con copia fuera del NAS, inventario de secretos con su procedimiento de
  rotación y copia cifrada del `.env`.

#### AUD-04 · Sin alertas de caída ni latido del scheduler
- **Severidad** Alta · **Esfuerzo** S · ✅
- **Evidencia**: nada consulta `/health/ready` desde fuera. El contenedor del scheduler
  tiene el healthcheck desactivado (`docker-compose.yml`), solo captura
  `KeyboardInterrupt` (un `docker stop` corta un job a medias) y `BackgroundScheduler()`
  no fija zona horaria (◐ las horas de los jobs podrían interpretarse en UTC).
- **Impacto**: una caída del NAS, del túnel o del scheduler (revisión de precios,
  publicaciones programadas) puede pasar horas sin detectarse.
- **Propuesta**: monitor externo gratuito sobre `/health/ready` con aviso a Telegram,
  latido del scheduler (Sentry Crons o equivalente), `timezone="Europe/Madrid"` y manejo
  de SIGTERM.

#### AUD-05 · Token del Cloudflare Tunnel sin rotar (TD-21)
- **Severidad** Alta · **Esfuerzo** S · ✅ (abierto desde 2026-09-26)
- **Impacto**: quien tenga el token puede levantar otro conector para `api.buenchollotech.com`.
- **Propuesta**: rotarlo según `docs/guides/Cloudflare.md` §T8 (recrear el contenedor
  con `--force-recreate`, un `restart` no relee `env_file`).

#### AUD-06 · `main` sin protección de rama y CI que no corre en `develop`
- **Severidad** Alta · **Esfuerzo** S · ✅ (`GET /branches/main/protection` → 404; sin rulesets)
- **Evidencia**: Cloudflare despliega el frontend en cada push a `main`, pero nada
  impide hacer push o merge sin CI verde. `ci.yml` solo se dispara en `push`/`pull_request`
  hacia `main`.
- **Propuesta**: exigir los cinco checks en `main`, bloquear el push directo y ejecutar
  la CI también en `develop`.

#### AUD-07 · *Soft 404*: fichas inexistentes y caídas de la API con HTTP 200
- **Severidad** Alta · **Esfuerzo** S · ✅ (en producción, `/chollo/<slug inexistente>` y
  `/blog/<slug inexistente>` devuelven 200 con "no encontrado" y sin `noindex`)
- **Dónde**: loaders de `routes/chollo.$slug.tsx`, `blog_.$slug.tsx` y
  `categoria.$slug.tsx` (`catch { return { meta: null } }`); `notFound()` no se usa en
  ningún sitio.
- **Impacto**: además del *soft 404*, una caída o timeout del NAS se sirve al crawler como
  página vacía con canonical, y una URL buena puede quedar indexada así. El SEO es el
  canal principal de un sitio de chollos.
- **Propuesta**: `throw notFound()` ante 404 de la API, relanzar los demás errores con un
  `errorComponent` en español y `noindex` en la página de no encontrado.

#### AUD-08 · Logo y favicon de 588 KB en todas las páginas
- **Severidad** Alta · **Esfuerzo** S · ✅
- **Dónde**: `src/assets/logo-bctech.png` y `public/favicon.png` (753×731 px, 588 KB,
  mostrados a 36–40 px con `loading="eager"`); `public/logo-512.png` (443 KB).
- **Impacto**: entre 0,6 y 1,2 MB extra en la primera visita desde móvil, compitiendo con
  la imagen principal (LCP).
- **Propuesta**: logo de 80×80 en WebP (< 10 KB), favicon de 32/180 px y `logo-512`
  comprimido.

### 5.2 Prioridad media

| ID | Hallazgo | Dónde | Propuesta | Esf. |
|---|---|---|---|---|
| AUD-09 | **E/S síncrona dentro de rutas `async`**: `requests` del bot de Telegram (hasta 42 s), API admin de Supabase y descarga del JWKS bloquean el bucle de eventos del worker. Un JWT falso con `kid` inventado fuerza una descarga del JWKS sin timeout corto y después la validación remota: vector de DoS barato ◐ | `telegram/api/router.py:196,207`, `emails/application/welcome_service.py`, `users/application/user_service.py:123`, `core/security.py:62-91` | `asyncio.to_thread` (patrón ya usado en `products`); JWKS precargado, con `timeout` corto y sin degradar a remoto ante `kid` desconocido | S |
| AUD-10 | **El worker de publicaciones programadas puede publicar dos veces en Telegram**: todo el lote va en una transacción y se envía a Telegram antes del commit; un fallo de BD deshace el lote ya enviado ◐ | `scheduled_deals/application/publication_worker.py:56-72` | Commit por elemento (como `scheduled_tasks`) o marcar "publicando" antes de enviar | S-M |
| AUD-11 | **Transacciones confirmadas en tres sitios** (`get_db`, routers y repositorios). El commit de `get_db` ocurre después de enviar la respuesta: el cliente puede recibir 2xx de un dato que no se guardó | `submissions/api/*`, `scheduled_tasks/api/router.py:88`, `catalog/infrastructure/top_repository.py:88`, `affiliates/infrastructure/repository.py:39` | Cerrar la unidad de trabajo antes de responder y prohibir `commit()` en repositorios; incremental | M |
| AUD-12 | **`GET /deals/{slug}` devuelve también borradores y programados** y campos internos (`import_snapshot`, `price_reference_evidence`, `data_source`) ✅ | `deals/infrastructure/repository.py:41`, `deals/api/router.py:234` | Endpoint público solo `active`/`expired`; vista previa por `/deals/admin/{id}`; quitar campos internos del schema público | S-M |
| AUD-13 | **Comentarios sin moderación admin** (solo borra el autor), votos de comentario sin rate limit y listados sin paginar ✅ | `comments/api/router.py`, `blog_comments/api/router.py` | DELETE admin, límite en votos y paginación | S |
| AUD-14 | **Alertas sin cuota por usuario y cruce que no escala**: cada chollo nuevo carga todas las alertas activas y hace 3 viajes a BD por coincidencia, dentro del `POST` de admin | `alerts/api/router.py`, `alerts/infrastructure/repository.py:49-58`, `alerts/application/alert_matcher.py` | Tope por usuario y rate limit; prefiltro en SQL e `INSERT … ON CONFLICT` | S-M |
| AUD-15 | **Metadatos de la ficha incoherentes**: chollos caducados con precio en `<title>`, metas y JSON-LD; "Opiniones" sin reseñas; sin `twitter:title`; rama `aggregateRating` muerta. **Fechas formateadas en SSR sin zona horaria** (UTC en el Worker, Madrid en el navegador): desajuste de hidratación y hora de fin errónea en el HTML | `routes/chollo.$slug.tsx:76-156,397-404`, `lib/format.ts` | Metas sin precio en caducados, `twitter:*`, `timeZone: "Europe/Madrid"` centralizado | S |
| AUD-16 | **Errores técnicos mostrados al usuario** (`API Error: 500…`, validaciones de Pydantic en inglés, `Failed to fetch`) en 22 toasts; pantalla de error global en inglés; `localStorage` sin `try/catch` en el banner de cookies (con cookies bloqueadas, la web cae al error global) | `lib/errors.ts`, `services/api/client.ts`, `router.tsx`, `components/layout/CookieBanner.tsx` | Mostrar `detail` solo en 4xx; mensajes genéricos en español; helper `safeStorage` | S |
| AUD-17 | **Bundle inicial de 776 kB** (235 kB gzip) para todos los visitantes; **Google Fonts** externo, bloqueante, con 7 pesos (y envío de la IP a Google) | `vite build` (`assets/index-*.js`), `__root.tsx:83-88` | Analizar el chunk inicial y separar por ruta; fuentes alojadas en local con `font-display: swap` | M |
| AUD-18 | **Componentes "Dios"** (`chollo.$slug.tsx` 959 líneas, `RecommendedAlertsBlock` 758, `ScheduledDealsCalendar` 717, `admin.chollos.tsx` 712, `TelegramPanel` 707) y **dos patrones de carga de datos** (TanStack Query en 12 ficheros, `useEffect` + `fetch` en ≈ 28); `QueryClient` como singleton de módulo en el Worker (sin fuga hoy, sí en cuanto un loader lo use) | `src/routes`, `src/features`, `lib/query-client.ts` | Extraer hooks y subcomponentes empezando por la ficha; `QueryClient` por petición; migrar a `useQuery` por feature | M-L |
| AUD-19 | **Accesibilidad**: lightbox y panel de Telegram hechos a mano (sin foco ni Escape); etiquetas sin `htmlFor` en login y registro (≈ 82 de 169 controles sin etiqueta programática); 97 textos de 10 px. **Pie legal fuera del HTML de SSR** (◐ posible problema con la LSSI-CE, a valorar por un jurista) | `chollo.$slug.tsx:615-700`, `TelegramPanel.tsx`, `login.tsx`, `components/layout/Layout.tsx` | Radix `Dialog`/`Sheet`, `useId`, `autoComplete`, mínimo 12 px; enlaces legales siempre en el HTML | M |
| AUD-20 | **Cliente LLM con cuatro métodos clonados** (668 líneas; `"gpt-4o"` ×8). Fallo de comportamiento: con `provider="openai"` y respuesta vacía cae a la cascada de modelos gratuitos aunque se pidió OpenAI ✅ | `ai/infrastructure/llm_client.py:164,286,418,540` | Núcleo único de cascada y un `_call_openai`; borrar los métodos sin uso | M |
| AUD-21 | **CI incompleta**: sin linter ni type-checker en el backend (`ruff` encuentra 2 `raise` sin `from`, 3 `except: pass`, 83 imports desordenados); sin `permissions:` en el workflow; acciones por tag mutable (`gitleaks-action@v2`); sin `timeout-minutes` | `.github/workflows/ci.yml`, `requirements-dev.txt` | `ruff` (E,F,I,B,UP) y `mypy` gradual en `application/` y `domain/`; `permissions: contents: read`; SHA fijados con Dependabot | S |
| AUD-22 | **Huecos de test**: frontend al 38 %; `notifications` y `comments` sin tests propios; `ai` con un solo fichero; 322 mocks y `supabase`/`amazon_paapi` sustituidos en `sys.modules`; E2E con API simulada (no prueban el contrato real) y sin E2E de la ficha pública | `buenchollo-api/conftest.py`, `buenchollo-web/e2e/` | Tests de contrato con fixtures grabadas (Amazon, OmniRoute); tests mínimos de los módulos sin cobertura; un E2E de humo con la API real y otro de la ficha (404, JSON-LD, 375 px) | M-L |
| AUD-23 | **Ventana front/back en cada despliegue**: el Worker se publica al hacer merge y la API se actualiza a mano después; `/health` no dice qué versión corre | `docs/project/08-deployment.md` | Desplegar la API primero, endpoints aditivos y `git sha` en `/health` | S |
| AUD-24 | **`.env.example` incompleto**: faltan `SMTP_*`, `PUBLIC_SITE_URL`, `TELEGRAM_ENABLED`, `AWIN_FEED_*`, `AWIN_RATE_LIMIT_PER_MINUTE` ✅ | `buenchollo-api/.env.example`, `app/core/config.py` | Completarlo y añadir un test que compare `Settings` con el ejemplo | S |
| AUD-25 | **Documentación operativa dispersa**: runbooks contradictorios (ver AUD-02), `08-deployment.md` mezcla vigente e histórico, `06-testing-and-quality.md` con cifras de 2026-09, procedimientos solo en `.claude/memory/`, índice de ADR sin ADR-017/018/019, datos de acceso al NAS (IP, puerto, usuario) en el repo | `docs/`, `.claude/memory/`, `docs/adr/00-index.md` | Un `RUNBOOK.md` único; podar `08-deployment.md`; subir a `docs/` lo útil de la memoria; actualizar el índice de ADR; retirar los datos del NAS antes de traspasar el repo | M |
| AUD-26 | **Resumen nocturno de alertas con el pool de la web desde otro bucle de eventos** (los otros cinco jobs usan NullPool) y SQL directo en `application` con N+1 sobre `auth.users` ◐ | `emails/application/digest_worker.py` | Helper NullPool común y consultas en repositorios | S |

### 5.3 Prioridad baja (higiene)

**Seguridad**
- `/docs`, `/redoc` y `/openapi.json` públicos en producción ✅ (responden 200): publican el mapa de rutas de admin. Desactivarlos con `APP_ENV=production`.
- `avatar_url` del perfil acepta cualquier URL (píxel de seguimiento en comentarios). Restringir al bucket `avatars` y a Google.
- Valores por defecto abiertos: `cors_origins=["*"]` y `scheduler_enabled=True`. Que el arranque falle en producción con CORS `*`.
- `ANALYTICS_HASH_SECRET` cae a la `service_role` si está vacío. Exigirlo en producción.
- IDs no UUID provocan 500 (`/deals/{id}/click`, `my-votes`, comentarios); `X-Request-Id` sin límite; `ilike` sin escapar `%`/`_`; email del destinatario en logs INFO; `cloudflared` recibe todo el `.env`.
- `psycopg2-binary` sin versión fijada; `uvicorn` 0.34 y `sentry-sdk` 2.20 rezagados (◐ sin avisos conocidos).
- La web no tiene CSP de scripts (aceptado y documentado en `07-security.md`).

**Código backend**
- Utilidades repetidas: formato de precio ×3 (y `_format_price_es`, privado, importado desde otros módulos), slug ×3, paginación ×3 con comportamientos distintos, `amazon.es/dp/{asin}` ×3, `_canonical_url_for` duplicado con un script.
- Configuración que existe en `Settings` pero se escribe a mano (`https://buenchollotech.com` en emails y Telegram) y 9 timeouts distintos en el bot de Telegram.
- Tres pilas HTTP (`requests`, `httpx`, `urllib`): fijar `httpx` como estándar y migrar al tocar cada módulo (relacionado con TD-25).
- `DealCreate`/`DealUpdate` repiten 28 campos; precios como `float` en schemas frente a `Numeric` en BD.
- Código muerto: el chatbot de recomendación (ADR-013), `ProductEnricherProtocol`, `get_featured`, `get_purgeable`, `get_username` y `activate_scheduled_deals` (este último, confirmar antes de borrar).
- Funciones largas con complejidad alta: `map_td_product` (53), `_tradedoubler` (37), `get_overview` de analítica (129 líneas), `_process_one` del worker (88 líneas).
- 11 `except` sin log, dos de ellos importantes (reintento sin `response_format` en el LLM y validación del blog).
- El arranque del scheduler vive en `deals` (crea 6 dependencias circulares entre módulos) y el engine NullPool está copiado en 5 jobs.
- Fugas de capas puntuales (`application` que importa schemas de `api`, routers que importan factories de otros módulos, router de Telegram con lógica de publicación).
- Clientes con estado creados por petición (token OAuth de Amazon pedido en cada vista previa).
- Listados con `selectinload` para relaciones muchos-a-uno (5 consultas) y `/deals/page` fuera de la caché del borde.
- Ruta antigua `/telegram/notify` sin `text` con MarkdownV2 mal escapado (◐ el frontend no la usa).
- Caracteres de control Unicode sin escapar en una expresión regular de `affiliates/domain/offers.py:170` (intencionados, pero conviene escribirlos como `​`).

**Frontend**
- 30 de 47 componentes de `components/ui/` sin uso (≈ 2 700 líneas), restos de la plantilla inicial (incluido un cliente server-only con `service_role`, no importado), `types.ts` de un esquema antiguo (TD-36).
- `Comments.tsx` y `BlogComments.tsx` iguales en más del 90 %.
- `/blog` renderizado solo en cliente; canonical de la portada paginada apuntando a `/`; `/explorar` (con `noindex`) en el sitemap; una fecha vacía rompe el bloque del blog en el sitemap.
- Tipos de la API escritos a mano (2 020 líneas) en lugar de generarse desde OpenAPI.
- Logos de marcas enlazados en directo desde Wikimedia en `RecommendedAlertsBlock`.

**Documentación de decisiones**
- ADR-001 "superado parcialmente" frente a "Aceptado" en el índice; ADR-012 describe un registro de handlers ya centralizado; decisiones sin ADR: contenedor del scheduler con NullPool por job, caché en el borde, rate limit en memoria (TD-28).

---

## 6. Lo que no tocaría

- **El monolito modular (ADR-001).** Partirlo en servicios a este tamaño solo añadiría coste.
- **Los modelos ORM como dominio (ADR-004)** y `Depends` como inyección de dependencias (ADR-007). Un contenedor de DI o entidades puras con mappers serían sobreingeniería.
- **APScheduler en contenedor dedicado con locks en BD.** Redis/Celery solo si hay varias instancias.
- **La autenticación** (JWKS local + rol en BD), **la política RLS + `service_role` en backend** (ADR-006), **`SafeHttp`/`core/ssrf.py`** y **el validador de TipTap**: son las piezas mejor diseñadas.
- **La configuración para PgBouncer** y la paginación por offset.
- **La organización `features/*`** con lógica pura extraída (`deal-form.ts` es el modelo a seguir) y la configuración estricta de TypeScript y ESLint.
- **La subida directa a Supabase Storage**, el stack TanStack Start + Worker y `apiClient`.
- **El `local-env/`** basado en el esquema real de producción y el `npm audit` con excepciones que caducan.
- **No migraría todo a TanStack Query de golpe** ni haría una pasada masiva de refactor: por features y protegido por los tests que ya existen.

---

## 7. Plan de acción

**Fase 1 — Antes de vender o traspasar (≈ 1 semana)**
1. AUD-01: registrar los seis modelos en `base.py` y test de cobertura del metadata.
2. AUD-05: rotar el token del túnel.
3. AUD-06: protección de rama en `main` y CI en `develop`.
4. AUD-03: backup programado fuera del NAS, restauración probada y copia cifrada del `.env`.
5. AUD-04: monitor externo de `/health/ready` y latido del scheduler.
6. AUD-07 y AUD-08: *soft 404* y logo (impacto SEO y rendimiento inmediato).
7. Higiene de seguridad rápida: `/docs` cerrado en producción, AUD-12 y AUD-13.

**Fase 2 — Robustez (2–3 semanas)**
- AUD-02 (imagen con versión, runbook único, build en CI) y AUD-23.
- AUD-09, AUD-10, AUD-11 y AUD-26 (async, idempotencia y transacciones).
- AUD-21 (ruff, mypy gradual, permisos de CI) y AUD-24.
- AUD-15 y AUD-16 (metadatos, fechas y errores al usuario).

**Fase 3 — Mantenibilidad (continuo, por features)**
- AUD-18 y AUD-19 (componentes grandes, accesibilidad), AUD-17 (bundle y fuentes).
- AUD-20 (cliente LLM), AUD-14 (alertas), AUD-22 (tests de contrato y E2E).
- AUD-25 (documentación operativa) y los puntos de prioridad baja, al tocar cada módulo.

**Validación de cada fase**: CI completa en verde, `pytest -m integration`, E2E, build del
frontend, y en producción `/health/ready`, una ficha existente (200) y una inexistente
(404).

---

---

## 8. Veredicto

Para un comprador técnico, BuenCholloTech es **un activo bien construido**: la base de
código está por encima de lo habitual en un proyecto de una sola persona (capas claras,
seguridad cuidada, tests reales, decisiones documentadas) y no necesita rehacerse. El
precio debería descontar el trabajo de **profesionalizar la operación**: hoy el servicio
depende de un NAS doméstico, de despliegues manuales y del conocimiento del autor. Con la
Fase 1 cerrada, el riesgo de compra pasa a ser bajo.

---

## 9. Estado de las correcciones (2026-11-18)

| Hallazgo | Estado |
|---|---|
| AUD-01 Registro de modelos de Alembic | ✅ Seis modelos registrados y test que falla si vuelve a faltar alguno |
| AUD-02 Despliegue sobre la copia de trabajo | 🟡 Runbook único y coherente, build de la imagen en CI; imagen versionada pendiente (TD-61, TD-31) |
| AUD-03 Backups | 🟡 Servicio `db-backup` diario y validado, guía de restauración; copia fuera del NAS pendiente (TD-52) |
| AUD-04 Alertas de caída | 🟡 Monitor de GitHub Actions cada 15 min (web, API y una ficha real); latido del scheduler pendiente (TD-60) |
| AUD-05 Token del túnel | ⏳ Requiere al propietario (TD-21) |
| AUD-06 Protección de `main` | ✅ Checks obligatorios en `main`; la CI corre también en `develop` |
| AUD-07 *Soft 404* | ✅ 404 y 5xx reales con `noindex` (ver [`13-seo.md`](13-seo.md)) |
| AUD-08 Logo de 588 KB | ✅ 7 KB (WebP) y favicons optimizados |
| AUD-09 E/S síncrona en rutas `async` | ✅ Telegram, Supabase y JWKS fuera del bucle; JWKS con timeout y sin respaldo remoto ante `kid` desconocido |
| AUD-10 Doble publicación en Telegram | 🟡 Commit por programación con bloqueo por fila; queda el caso límite TD-56 |
| AUD-11 Transacciones | ⏳ TD-54 |
| AUD-12 Borradores por slug | ⏳ TD-55 |
| AUD-13 Moderación de comentarios | ✅ Borrado admin (API y web), rate limit en votos |
| AUD-14 Alertas | ✅ Tope de 50 por usuario, rate limit y longitudes en la edición |
| AUD-15 Metadatos y fechas | ✅ Ver `13-seo.md` |
| AUD-16 Errores al usuario | ✅ Mensajes en español sin detalles internos; `localStorage` protegido |
| AUD-17 Bundle y fuentes | 🟡 Fuentes alojadas en la web; bundle inicial pendiente (TD-57) |
| AUD-18 Componentes grandes | 🟡 Un único hilo de comentarios para chollos y blog; resto pendiente (TD-57) |
| AUD-19 Accesibilidad | ⏳ TD-58 (el pie ya está en el HTML del servidor) |
| AUD-20 Cliente LLM | ✅ De 668 a 320 líneas, un único núcleo; corregido el fallo con `provider="openai"` |
| AUD-21 CI | ✅ Permisos mínimos, acciones por SHA, límites de tiempo, `ruff`, build de la imagen |
| AUD-22 Tests | 🟡 Tests nuevos en todos los cambios (backend 851, frontend 544); contrato y E2E real pendientes (TD-59) |
| AUD-23 Versión en `/health` | ⏳ TD-60 |
| AUD-24 `.env.example` | ✅ Completo y con test que compara con `Settings` |
| AUD-25 Documentación | ✅ Reordenada, sin histórico ni datos sensibles, índices y enlaces verificados |
| AUD-26 Resumen nocturno y jobs | ✅ Helper único `core/jobs.py` con NullPool para los seis jobs |
| Bajos de seguridad | ✅ `/docs` cerrado en producción, CORS `*` bloquea el arranque, aviso si falta `ANALYTICS_HASH_SECRET`, `psycopg2-binary` fijado; resto en TD-62 |
| Código muerto | ✅ Chatbot sin uso, protocolos y métodos huérfanos eliminados |
| Scheduler | ✅ Hora de Madrid (antes UTC) y apagado limpio con SIGTERM |
