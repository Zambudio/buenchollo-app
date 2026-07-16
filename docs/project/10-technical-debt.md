# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Esta página es
> interna del proyecto; **no forma parte del bloque académico** ([`docs/master/`](../master/00-index.md)).

Última revisión: **2026-07-16** (post-auditoría [`AUDIT_REPORT.md`](../../AUDIT_REPORT.md)).

---

## 🔴 Alta — resolver antes de seguir creciendo

### TD-12 · Validación JWT con round-trip HTTP a Supabase por request (H-02)
`core/security.py` llama a `supabase.auth.get_user(token)` en `get_current_user`,
es decir, **cada request autenticada paga un viaje HTTP a Supabase** además del
salto NAS↔Tunnel. Contribuye a TD-11 y convierte a Supabase Auth en punto único
de fallo de toda la API autenticada.
- **Acción:** validar el JWT localmente (JWKS o HS256 con `SUPABASE_JWT_SECRET` —
  el CI ya inyecta esa variable), dejando `get_user` como fallback. Documentar en
  ADR el trade-off (revocación inmediata vs latencia). Ver AUDIT_REPORT H-02.

---

## 🟡 Media — mejora de mantenibilidad

### TD-03 · God Component `admin.chollos.tsx` (≈986 líneas)
Mezcla UI + lógica de negocio + 13 estados; sin tests unitarios dedicados (se cubre
vía E2E/smoke). Es el punto más atacable en SRP.
- **Acción:** extraer hooks (`useAdminDeals`, `useDealForm`) y subcomponentes de
  formulario/listado. Mientras tanto, queda registrado aquí como deuda consciente.

### TD-04 · Capas `application/` incompletas en módulos menores
`categories/` y `stores/` van `router → repository` sin capa de aplicación.
Aceptable para CRUD simple, pero inconsistente con la arquitectura declarada.
Revisar también `users/` (PROJECT_STATUS tiene afirmaciones contradictorias sobre si
ya tiene capa de uso).

### TD-05 · `__init__.py` faltantes en subdirectorios de módulos
Funciona por namespace packages, pero da problemas con linters/IDEs/herramientas de
test. Faltan en varios subdirectorios de `deals/`, `categories/`, `stores/`, `users/`,
`telegram/api/`.

### TD-06 · Excepciones de dominio incompletas
No todos los módulos tienen excepciones de dominio propias; varios routers lanzan
`HTTPException` directa, mezclando protocolo HTTP con lógica de negocio.

### TD-07 · Tests de integración no corren en CI
Los marcados `@pytest.mark.integration` solo se ejecutan en local (requieren Postgres
real). Migrar a CI con un servicio Postgres para cubrirlos automáticamente.

### TD-11 · Latencia general al cargar chollos (home y detalle)
Home y `/chollo/:slug` tardan varios segundos en cargar en producción. Diagnosticado
2026-07-09: el waterfall duplicado del detalle ya se corrigió (fetch SSR+CSR
redundante + relacionados bloqueando el render), y se añadieron índices compuestos
`(status, published_at)` / `(status, temperature)` en `deals` (ya aplicados en BD),
pero con solo ~117 filas ese índice apenas influye — el grueso sigue siendo:
- El contenedor `uvicorn` del NAS corre **sin `--workers`** (proceso único) detrás de
  Cloudflare Tunnel: cada request paga el salto NAS↔Tunnel↔cliente en serie.
- No se ha medido el pool de conexiones SQLAlchemy async contra el pooler PgBouncer
  (puerto 6543, modo transacción) — posible latencia extra de conexión por request.
- El round-trip de validación JWT a Supabase por request (TD-12) se suma al coste.
- **Acción:** revisar `--workers` de uvicorn en `docker-compose.yml`/`Dockerfile`,
  medir tiempos reales con el NAS bajo carga normal, y decidir si compensa mover
  algo de I/O (imágenes) a un CDN o cache.
- ⚠️ **Dependencia (AUDIT_REPORT M-07):** NO subir `--workers` sin antes sacar el
  scheduler del proceso web (`main.py` lifespan) o gatearlo con lock — con N workers
  los jobs correrían N veces (dobles notificaciones Telegram).

### TD-13 · Contenedor API como root e imagen no inmutable (AUDIT_REPORT M-01)
El `Dockerfile` no declara `USER` ni `HEALTHCHECK`, y el compose monta `.:/app`
pisando el código de la imagen. Mitigado por el túnel (NAS no expuesto) y el WAF.
- **Acción:** usuario no-root + `HEALTHCHECK /health`; valorar eliminar el volumen
  en producción. Probar en local antes de tocar el NAS.

### TD-14 · Frontend sin error tracking (AUDIT_REPORT M-04)
Sentry solo existe en el backend; los errores de usuarios reales en el
navegador/Worker son invisibles. Al resolverlo se cierra también TD-08.

---

## 🟢 Baja — pulido

### TD-08 · `console.error` en rutas frontend
8 ocurrencias en rutas (`chollo.$slug.tsx`, `explorar.tsx`, `favoritos.tsx`,
`categorias.tsx`, `index.tsx`, `CategoriesDrawer.tsx`). Enrutar a un logger central o
justificar por qué se dejan.

### TD-09 · Telegram aún usa Supabase Functions
Pendiente migrar a `POST /telegram/notify` en el backend (coherencia con ADR-002).

---

> 🔁 **Cómo usar esta página:** revisar al empezar cada tanda de trabajo. Al cerrar un
> item, borrar su entrada y anotar el cierre (fecha + commit) en `PROJECT_STATUS.md`.
