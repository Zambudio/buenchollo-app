# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Para consultar el diseño de arquitectura, ver [`docs/master/`](../master/00-index.md).

Última revisión: **2026-09-05** (Alta de TD-20 tras revisar el Advisor completo de Supabase — seguridad + rendimiento).

---

## 🟡 Media — hardening Supabase (Advisor seguridad + rendimiento)

- **TD-20 — 4 avisos WARN del Advisor de Supabase pendientes de corregir.**
  Tras cerrar el crítico `rls_disabled_in_public` (ver `PROJECT_STATUS.md`
  § 3.tervicies), `get_advisors` (conector MCP de Supabase, 2026-09-05) reportó
  estos 4 hallazgos de nivel WARN — ninguno es una exposición de datos como el
  anterior, pero conviene cerrarlos. **Plan de implementación completo, listo
  para ejecutar tarea a tarea**: [`docs/superpowers/plans/2026-09-05-supabase-advisor-hardening.md`](../superpowers/plans/2026-09-05-supabase-advisor-hardening.md).

  1. **`anon_security_definer_function_executable` / `authenticated_security_definer_function_executable`** (×3): `public.handle_new_user()`, `public.recalc_comment_votes()`, `public.recalc_blog_comment_votes()` son funciones `SECURITY DEFINER` invocables por `anon`/`authenticated` vía `/rest/v1/rpc/<fn>` — son funciones de trigger, no pensadas para llamarse sueltas. Fix: `REVOKE EXECUTE ... FROM PUBLIC, anon, authenticated` (no afecta a la ejecución como trigger).
  2. **`auth_leaked_password_protection`**: protección de contraseñas filtradas (HaveIBeenPwned) desactivada en Supabase Auth. Fix: toggle en el dashboard (Authentication → Policies) — no se puede aplicar por migración ni por las tools del conector MCP disponibles.
  3. **`extension_in_public`**: `pg_trgm` instalada en el schema `public` en vez de uno dedicado. Fix: `ALTER EXTENSION pg_trgm SET SCHEMA extensions` — requiere verificar antes que el `search_path` de la conexión del backend incluya `extensions`, o el índice `ix_deals_title_trgm` (`gin_trgm_ops`) podría dejar de resolver el operador. Prioridad más baja (cosmético) por ese riesgo.
  4. **`auth_rls_initplan`** (rendimiento): la política `"Users view own role"` de `user_roles` reevalúa `auth.uid()` fila a fila en vez de `(select auth.uid())`. Fix trivial y de bajo riesgo — recomendado hacerlo primero.

  Impacto bajo en todos los casos (nada expone datos); es limpieza de higiene de seguridad/rendimiento recomendada por el propio Supabase.

---

## 🟡 Baja — observabilidad

- **TD-19 — El worker de tareas programadas se traga cualquier fallo de arranque.**
  `scheduled_tasks/application/scheduler.py::_run()` envuelve el cableado del
  servicio y la ejecución en un único `except Exception` que hace
  `logger.exception("Fallo global del worker de tareas programadas")` y devuelve
  `0`. Un `NameError` por un import perdido (ver `PROJECT_STATUS.md` § 3.duovicies)
  estuvo ~3 días fallando en cada tick horario sin que saltara ninguna alarma: en
  APScheduler el job figuraba como *"executed successfully"* y la única señal era
  una línea `ERROR` en los logs del contenedor. Propuesta: separar el fallo de
  cableado (`_build_service`) del fallo de ejecución de una tarea concreta y dejar
  que el primero propague / llegue a Sentry; o añadir un smoke check al arrancar
  `run_scheduler.py` que construya el servicio una vez y falle ruidosamente si el
  import está roto. Revisar el mismo patrón en `scheduled_deals` y `blog`. Impacto
  bajo (no corrompe datos), pero anula la observabilidad de un proceso desatendido.

---

> 🔁 **Cómo usar esta página:** revisar al empezar cada tanda de trabajo. Al cerrar un
> item, borrar su entrada y anotar el cierre (fecha + commit) en `PROJECT_STATUS.md`.
