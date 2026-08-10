# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Esta página es
> interna del proyecto; **no forma parte del bloque académico** ([`docs/master/`](../master/00-index.md)).

Última revisión: **2026-08-10** (deuda nueva registrada tras el motor de tareas
programadas — ver `PROJECT_STATUS.md` § 3.undecies).

---

## 🔴 Alta — resolver antes de seguir creciendo

*(vacío)*

---

## 🟡 Media — mejora de mantenibilidad

- **TD-15 — Sin base de datos de test aislada.** `DATABASE_URL` en `buenchollo-api/.env`
  apunta a la Supabase de producción real; no existe un proyecto/esquema Postgres
  dedicado a tests. Los tests de integración (`pytest.mark.integration`) crean y borran
  datos reales, mitigado caso por caso con limpieza `try/finally` (ver
  `test_scheduled_tasks_api.py`), pero cada test de integración nuevo reabre el mismo
  riesgo. Solución real: proyecto Supabase de test independiente o un Postgres local en
  CI (ver también el pendiente ya existente más abajo, "CI con servicio Postgres").
- **Regla `no_longer_deal` sin ajustar antes de activar el modo automático de
  revisión de precios.** Amazon a veces omite `savingBasis`/`savings.percentage` en
  productos que siguen genuinamente en oferta, lo que el handler
  (`price_check_handler.py`) interpreta como "ya no es oferta" y borra. En modo manual
  un admin ve la lista antes de confirmar; en modo automático no hay revisión humana.
  Antes de activar `enabled=true` en `/admin/tareas-programadas`: correr varias
  revisiones manuales y vigilar qué fracción de candidatos cae en ese motivo.

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
