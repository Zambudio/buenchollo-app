# ⚡ Plan de optimización de rendimiento

> Registro vivo, no urgente. **No se ejecuta todavía** — se retoma cuando haya
> base de usuarios real que lo justifique. Mientras tanto queda aquí guardado
> para no perder el hilo. Relacionado con [TD-11](docs/project/10-technical-debt.md).

Última actualización: 2026-07-09

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

## Fase 1 — Gratis, bajo riesgo (hacer primero)

### 1. `--workers` en uvicorn
Hoy el contenedor corre un solo proceso uvicorn, así que las peticiones se
sirven en serie. Pasar a 2-4 workers en `buenchollo-api/docker-compose.yml` /
`Dockerfile` permite atender varias peticiones en paralelo con el mismo
hardware del NAS. Sin coste, cambio acotado.

### 2. Cache en el borde (Cloudflare)
Los endpoints públicos de listado de chollos (GET, sin auth: home, explorar,
categoría) son buenos candidatos para una regla de cache de unos segundos o
minutos en Cloudflare (Cache Rules / Page Rules). Evita ida y vuelta al NAS en
visitas repetidas al mismo contenido. Gratis en el plan actual.

### 3. Medir el pool de conexiones SQLAlchemy vs PgBouncer
No se ha medido si el pool async de SQLAlchemy contra el pooler de Supabase
(puerto 6543, modo transacción) añade latencia de conexión por request.
Revisar tamaño de pool, timeouts, y si `statement_cache_size=0` (obligatorio
para PgBouncer) tiene algún coste medible que se pueda mitigar.

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
