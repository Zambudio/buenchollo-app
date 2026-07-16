# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Esta página es
> interna del proyecto; **no forma parte del bloque académico** ([`docs/master/`](../master/00-index.md)).

Última revisión: **2026-07-17** (cierre completo de la auditoría [`AUDIT_REPORT.md`](../../AUDIT_REPORT.md):
TD-03/05/07/08/12/13/14 y M-07 resueltos — ver `PROJECT_STATUS.md` § 3.septies).

---

## 🔴 Alta — resolver antes de seguir creciendo

*(vacío)*

---

## 🟡 Media — mejora de mantenibilidad

### TD-04 · Capas `application/` incompletas en módulos menores
`categories/` y `stores/` van `router → repository` sin capa de aplicación.
Aceptable para CRUD simple, pero inconsistente con la arquitectura declarada.
Revisar también `users/` (PROJECT_STATUS tiene afirmaciones contradictorias sobre si
ya tiene capa de uso).
- **Deuda consciente**: resolver al tocar cada módulo, no en bloque (AUDIT_REPORT §12).

### TD-06 · Excepciones de dominio incompletas
No todos los módulos tienen excepciones de dominio propias; varios routers lanzan
`HTTPException` directa, mezclando protocolo HTTP con lógica de negocio.
- **Deuda consciente**: resolver al tocar cada módulo, no en bloque (AUDIT_REPORT §12).

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
- ~~El round-trip de validación JWT a Supabase por request~~ — eliminado el
  2026-07-16 (ADR-010, validación local con JWKS); medir cuánto mejora.
- **Acción:** revisar `--workers` de uvicorn en `docker-compose.yml`/`Dockerfile`,
  medir tiempos reales con el NAS bajo carga normal, y decidir si compensa mover
  algo de I/O (imágenes) a un CDN o cache.
- ✅ **Desbloqueado (2026-07-17)**: el scheduler ya es desacoplable — flag
  `SCHEDULER_ENABLED` + servicio dedicado comentado en `docker-compose.yml`
  (`python -m app.run_scheduler`). Al subir `--workers`, activar ese servicio y
  poner `SCHEDULER_ENABLED=false` en la API para no duplicar jobs.

---

## 🟢 Baja — pulido

### TD-09 · Telegram aún usa Supabase Functions
Pendiente migrar a `POST /telegram/notify` en el backend (coherencia con ADR-002).

---

> 🔁 **Cómo usar esta página:** revisar al empezar cada tanda de trabajo. Al cerrar un
> item, borrar su entrada y anotar el cierre (fecha + commit) en `PROJECT_STATUS.md`.
