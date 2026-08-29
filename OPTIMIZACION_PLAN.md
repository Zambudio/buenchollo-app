# ⚡ Plan de optimización de rendimiento

> Registro vivo. **Fase 1 completada** (cierre de TD-11, antes de abrir la web
> al público). Fase 2 y 3 siguen sin ejecutarse — se retoman cuando haya base
> de usuarios real que lo justifique.

Última actualización: 2026-07-18

---

## Contexto

Home y `/chollo/:slug` tardan varios segundos en cargar en producción. Ya se
corrigieron las causas de frontend (waterfall duplicado SSR+CSR en el detalle,
índices compuestos en `deals`), pero la latencia de fondo sigue siendo
estructural: el backend vive en un NAS Synology doméstico detrás de Cloudflare
Tunnel, sin capacidad de paralelizar peticiones.

**Decisión explícita**: no migrar de infraestructura ni asumir gasto mensual
hasta que haya tráfico real que lo justifique. El NAS es gratis (coste hundido)
y hoy no hay usuarios suficientes para que el coste de una VPS/PaaS se
justifique. Este plan prioriza mejoras **gratuitas o de bajo coste** primero.

---

## Fase 1 — Gratis, bajo riesgo (hacer primero) — ✅ HECHA 2026-07-18

### 1. `--workers` en uvicorn — ✅ hecho
`buenchollo-api/docker-compose.yml`: `buenchollo-api` corre ahora con
`--workers 2`. El scheduler se desacopló a un contenedor propio
(`buenchollo-scheduler`, `python -m app.run_scheduler`) con
`SCHEDULER_ENABLED=false` en la API para no duplicar jobs (M-07).
Contenedores recreados y verificados en el NAS el 2026-07-18.

### 2. Cache en el borde (Cloudflare) — ✅ rehecha y verificada
La v1 de la Cache Rule `Cache API GET publicos` (Edge TTL fijo 30s ignorando
al origen, matcheo por `starts_with`) cacheaba también endpoints autenticados
(`/v1/deals/my-votes`, `/favorites` — fuga potencial entre usuarios) y causaba
contadores obsoletos con F5 en la web. **v2**: la política la dicta el origen —
middleware `app/core/cache_headers.py` (`no-store` en todo `/v1`;
`public, max-age=0, s-maxage=30` solo en los 5 listados públicos exactos) y
regla del panel con rutas exactas y Edge/Browser TTL "respect origin".
Config completa, verificación y bitácora en
[`docs/guides/Cloudflare.md`](docs/guides/Cloudflare.md) § T9.
Aplicada y verificada en producción: API y scheduler recreados en el NAS;
`/v1/deals` responde `MISS → HIT`, los endpoints autenticados responden
`Cache-Control: no-store` y nunca `HIT`, y votos/comentarios se actualizan
correctamente tras un F5 normal.

### 3. Medir el pool de conexiones SQLAlchemy vs PgBouncer — ✅ hecho
`buenchollo-api/app/core/database.py`: pool acotado explícitamente
(`pool_size=3, max_overflow=2, pool_recycle=300`) en vez de los defaults de
SQLAlchemy sin límite documentado. Con `--workers 2`: máximo 10 conexiones
simultáneas contra el pooler. Verificación de latencia vía
`GET /health/ready` (ya expone `checks.db.latency_ms`).

---

## Fase 2 — Optimización de base de datos, bundles y compresión — ✅ HECHA 2026-08-29

### 1. Índices GIN Trigram (`pg_trgm`) en PostgreSQL — ✅ hecho
Migración Alembic `20260829140000_deals_pg_trgm_search_indexes.py` activando la extensión
`pg_trgm` y creando el índice `ix_deals_title_trgm` sobre `deals USING gin (title gin_trgm_ops)`.
Acelera drásticamente las búsquedas de texto con `ILIKE '%query%'` en el buscador de la web
y la API (`search_active`), transformando `Seq Scan` en `Bitmap Index Scan`.

### 2. Code Splitting y Carga Perezosa en Frontend — ✅ hecho
- `TelegramPanel` desacoplado y cargado con `React.lazy` y `<Suspense>` en `admin.chollos.tsx`,
  generando un chunk independiente (`TelegramPanel-*.js`) y reduciendo el peso de carga inicial.
- `BlogEditor` (Tiptap) ya aislado en chunk bajo demanda para el panel de administración.
- `DealCard` implementa `decoding="async"`, dimensiones fijas y `loading="lazy"` sin CLS.

### 3. Compresión GZip en FastAPI — ✅ hecho
Middleware `GZipMiddleware(app, minimum_size=500)` registrado en `buenchollo-api/app/main.py`.
Reduce hasta un 75-80% el payload transferido en listados de chollos, blog y endpoints públicos,
probado con tests automáticos en `test_gzip_compression.py`.

---

## Fase 3 — Migración de infraestructura (solo con base de usuarios real)

Cuando el tráfico lo justifique, opciones a valorar (sin decidir todavía):

- **Fly.io / Railway / Render**: planes desde ~5€/mes, mismo Docker que ya
  existe hoy (migración de bajo esfuerzo porque no cambia el empaquetado).
- Mantener Supabase como está (ya es gestionado, no NAS).
- Evaluar si compensa separar backend y NAS (NAS solo para storage/backups,
  backend en la nube) o migrar todo junto.

**Trigger para pasar a esta fase**: métricas reales de tráfico/latencia que
muestren que Fase 1 y 2 ya no dan más margen, o que el NAS se convierte en un
punto de fallo inaceptable para usuarios reales.

---

## Cómo usar esta página

Se revisa igual que la deuda técnica: al **cambiar de tarea**, recordar
brevemente que este plan existe y sigue pendiente. Al empezar a ejecutar
alguna fase, mover ese punto a trabajo activo y marcarlo aquí como en curso;
al cerrarlo, anotar el cierre en `PROJECT_STATUS.md` y quitarlo de aquí.
