# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Para consultar el diseño de arquitectura, ver [`docs/master/`](../master/00-index.md).

Última revisión: **2026-09-05** (Cierre de 3/4 sub-items de TD-20 — ver `PROJECT_STATUS.md` § 3.quattuorvicies).

---

## 🟡 Baja — observabilidad

- **TD-20 — Protección de contraseñas filtradas desactivada en Supabase Auth.**
  `auth_leaked_password_protection` (Advisor de Supabase, nivel WARN): Supabase
  Auth no comprueba las contraseñas nuevas contra HaveIBeenPwned.org. Los otros
  3 sub-items de este TD (funciones `SECURITY DEFINER` expuestas por RPC,
  `pg_trgm` en `public`, política de `user_roles` sin optimizar) ya están
  cerrados — ver `PROJECT_STATUS.md` § 3.quattuorvicies. Este último requiere
  un toggle manual en el dashboard (Authentication → Policies): no hay
  migración ni tool del conector MCP que lo aplique. Detalle completo (por si
  se automatiza en el futuro vía Management API) en
  [`docs/superpowers/plans/2026-09-05-supabase-advisor-hardening.md`](../superpowers/plans/2026-09-05-supabase-advisor-hardening.md) Task 4.
  Impacto bajo (no expone datos; endurece cuentas de usuario contra
  credential stuffing).

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
