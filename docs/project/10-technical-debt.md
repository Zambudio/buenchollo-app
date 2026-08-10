# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Esta página es
> interna del proyecto; **no forma parte del bloque académico** ([`docs/master/`](../master/00-index.md)).

Última revisión: **2026-08-10** (incidente de datos de test en producción — ver
`PROJECT_STATUS.md` § 3.duodecies — sube TD-15 a Alta).

---

## 🔴 Alta — resolver antes de seguir creciendo

- **TD-15 — Sin base de datos de test aislada (ya causó un incidente real).**
  `DATABASE_URL` en `buenchollo-api/.env` apunta a la Supabase de producción real; no
  existe un proyecto/esquema Postgres dedicado a tests. El 2026-08-09/10, correr en
  local `pytest -m integration` sobre `test_blog_api.py` y `test_blog_comments_api.py`
  (que, a diferencia de `test_scheduled_tasks_api.py`, no limpian con `try/finally`)
  creó 126 `blog_posts` y 144 `blog_categories` falsos en producción, varios
  publicados y visibles públicamente — ver `PROJECT_STATUS.md` § 3.duodecies para el
  incidente y la limpieza aplicada. Cada test de integración nuevo sin limpieza propia
  reabre este mismo riesgo. Solución real: proyecto Supabase de test independiente o
  un Postgres local para ejecución local (ver también el pendiente ya existente más
  abajo, "CI con servicio Postgres" — CI ya está a salvo, el riesgo es solo local).
  Mitigación rápida mientras tanto: añadir limpieza `try/finally` a
  `test_blog_api.py` / `test_blog_comments_api.py`.

---

## 🟡 Media — mejora de mantenibilidad

- **TD-18 — Vigilar la regla `no_longer_deal` ahora que el modo automático está
  activado.** El usuario activó `enabled=true` (frecuencia semanal) el 2026-08-10 tras
  validar el flujo manual con datos reales (89 candidatos, todo correcto). Amazon a
  veces omite `savingBasis`/`savings.percentage` en productos que siguen genuinamente
  en oferta, lo que el handler (`price_check_handler.py`) interpreta como "ya no es
  oferta" y borra — en modo automático no hay revisión humana antes del borrado (sí
  queda registro restaurable). Revisar el registro de ejecuciones tras las primeras
  corridas automáticas y comprobar qué fracción de los borrados cae en el motivo
  `no_longer_deal`; si es alta, ajustar la regla o volver a `enabled=false` hasta
  afinarla.

---

## 🟢 Baja — pulido

- **TD-16 — Snapshot de restauración incompleto.** `scheduled_task_run_items` no guarda
  `previous_price`/`discount_percentage`/`short_description`, así que un chollo
  restaurado desde el panel pierde el badge de descuento. Fix barato si se quiere:
  añadir esas columnas (migración + `Candidate`/`_candidate_to_item`).
- **TD-17 — `TASK_HANDLERS` no es una fábrica genérica real.** El diccionario
  `{"price_check": handler}` está hardcodeado por duplicado en
  `scheduled_tasks/api/router.py` y `scheduled_tasks/application/scheduler.py`. El
  motor de tareas programadas es genérico en esquema (`scheduled_tasks`,
  `scheduled_task_runs`) pero `scheduled_task_run_items` es deal-shaped (columnas
  `NOT NULL` específicas de `deals`), así que una futura segunda tarea que no borre
  chollos necesitaría tocar el esquema pese a la intención original de "sin
  rediseñar". Revisar si aparece una segunda tarea real antes de refactorizar
  especulativamente.

---

> 🔁 **Cómo usar esta página:** revisar al empezar cada tanda de trabajo. Al cerrar un
> item, borrar su entrada y anotar el cierre (fecha + commit) en `PROJECT_STATUS.md`.
