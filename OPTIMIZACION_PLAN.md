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
⚠️ Requiere recrear el contenedor en el NAS para tomar el compose nuevo.

### 2. Cache en el borde (Cloudflare) — ✅ hecho
Cache Rule `Cache API GET publicos` creada en el dashboard (Caching → Cache
Rules) para `api.buenchollotech.com`, método GET, rutas `/v1/deals`,
`/v1/categories`, `/v1/stores`. Edge TTL fijo 30s (ignora `Cache-Control` del
origen). Verificado: `curl -D - .../v1/deals` → 1ª petición `cf-cache-status: MISS`,
2ª `HIT`. Documentado en [`docs/guides/Cloudflare.md`](docs/guides/Cloudflare.md) § T9.

### 3. Medir el pool de conexiones SQLAlchemy vs PgBouncer — ✅ hecho
`buenchollo-api/app/core/database.py`: pool acotado explícitamente
(`pool_size=3, max_overflow=2, pool_recycle=300`) en vez de los defaults de
SQLAlchemy sin límite documentado. Con `--workers 2`: máximo 10 conexiones
simultáneas contra el pooler. Verificación de latencia vía
`GET /health/ready` (ya expone `checks.db.latency_ms`).

---

## Fase 2 — Si Fase 1 no es suficiente

- Revisar si conviene mover imágenes (subidas por Amazon/Storage) a un CDN de
  imágenes propio o a transformaciones de Cloudflare Images.
- Revisar si `search_active` (ilike sobre título) necesita índice GIN/trigram
  (`pg_trgm`) — descartado en la migración de índices de 2026-07-09 por no ser
  aún un cuello de botella medido.

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
