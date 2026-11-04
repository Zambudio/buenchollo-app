# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Para consultar el diseño de arquitectura, ver [`docs/master/`](../master/00-index.md).

Última revisión: **2026-11-04** (cierre de chollos de usuarios: TD-23 a TD-30).

---

## 🔴 Alta — secretos de infraestructura

- **TD-21 — Rotar y verificar el token de Cloudflare Tunnel.** La guía operativa
  registra que `TUNNEL_TOKEN` quedó visible en una conversación y no contiene
  evidencia posterior de rotación. Revocar el token anterior desde Cloudflare
  Zero Trust, generar otro, actualizar únicamente el `.env` del NAS y reiniciar
  el servicio recreándolo con `docker compose up -d --force-recreate cloudflared`
  (un `docker restart` no recarga `env_file`); después comprobar
  `https://api.buenchollotech.com/health` y dejar
  fecha/evidencia en `docs/guides/Cloudflare.md`. No copiar el valor nuevo a Git,
  documentación, logs ni chat.

## 🟠 Media — chollos de usuarios (cierre 2026-11-04)

- **TD-23 — `POST /v1/products/preview-from-url` no exige autenticación.** Solo lo
  limita `10/min` por IP; cada llamada hace HTTP a Amazon Creators y al motor de IA.
  Es anterior a las propuestas, pero `check-link` (autenticado, 20/min por usuario) ya
  cubre el caso de usuarios. Proponer: exigir `require_admin` si solo lo usa el panel,
  o al menos usuario autenticado.

- **TD-24 — Imágenes huérfanas en `deal-images/submissions/`.** Una imagen subida y
  nunca enviada en una propuesta (usuario que abandona el formulario) o las de una
  cuenta eliminada no se borran. Falta una tarea programada (ADR-012) que borre objetos
  sin referencia en `deal_submissions.images` / `deals.images` con antigüedad suficiente.

- **TD-25 — Ventana de DNS rebinding en el fetcher de imágenes.** `core/ssrf.py`
  resuelve el host y valida la IP, pero `httpx` vuelve a resolverlo al conectar; un DNS
  malicioso podría responder distinto la segunda vez. Mitigación: conectar a la IP ya
  validada (con `Host`/SNI del original) o transporte con resolver propio.

- **TD-26 — El resumen nocturno de alertas lee atributos que no existen en `Deal`.**
  `emails/application/digest_worker.py` usa `deal.price`, `deal.original_price` y
  `deal.discount`; el modelo tiene `current_price`, `previous_price` y
  `discount_percentage`. Al montar el resumen de un chollo que coincide, `deal.price`
  debería lanzar `AttributeError`. Hallado al analizar el cierre de la feature (lectura de
  código); el efecto en producción no está comprobado (el digest solo actúa a las 21:00 con
  alertas activas y chollos recientes). Revisar y añadir un test con un `Deal` real.

- **TD-28 — Rate limit con almacenamiento en memoria por worker.** `slowapi`/`limits`
  sin Redis: con 2 workers los límites efectivos se duplican y se reinician al reiniciar
  el contenedor. Aceptable hoy (un solo proceso por servicio); revisar al escalar.

- **TD-29 — Cuota de propuestas "comprobar y luego insertar" no atómica.** Dos
  peticiones simultáneas del mismo usuario pueden pasar el límite de pendientes/día; solo
  los índices únicos parciales (mismo producto) lo acotan. Impacto bajo, con rate limit
  por usuario delante.

- **TD-30 — Menores diferidos de la revisión.** Sin reintento si falla el correo al
  usuario (solo se registra); `previously_published` pasa a verdadero para aprobadas cuya
  ficha ya expiró; el helper `_canonical_url_for` está duplicado entre `deal_service.py` y
  `scripts/backfill_canonical_urls.py`, y `storage.py` duplica `_clean_supabase_url`.
  Además: al aprobar, el `external_id` de tiendas no Amazon se pasa a mayúsculas (puede
  no detectar un duplicado con SKU en minúsculas; `canonical_url` sí lo detecta); los
  acortadores `amzn.asia` y `amzn.com` no se resuelven; y las peticiones sin autenticar
  a los 4 endpoints de propuestas se rechazan con 401 antes de que cuente el límite por
  usuario (aceptable: el JWT se verifica en local).

## 🟡 Baja — observabilidad y hardening de cuenta

- **TD-27 — `TelegramPanel` desborda 8 px a 375 px de ancho.** Preexistente (visto en la
  verificación visual de chollos de usuarios). Arreglar con `min-w-0`/`flex-wrap` en el
  panel y fijarlo con una comprobación a 375 px en el E2E.

- **TD-22 — Retirar los overrides npm temporales de `buenchollo-web`.**
  `overrides.miniflare.undici = 7.30.1` existe porque `@cloudflare/vite-plugin`
  1.65.0 arrastra `undici` 7.29.1 vía `miniflare` (GHSA-4qv8-2p9j-2685,
  GHSA-f72v-6w45-q472, GHSA-xjj6-f33q-929c): quitarlo cuando una versión
  estable del plugin traiga `undici >= 7.30.1`.
  `overrides["@tailwindcss/typography"]["postcss-selector-parser"] = 6.1.5`
  (GHSA-rj75-hqrm-r3gf): quitarlo cuando `@tailwindcss/typography` deje de
  fijar 6.0.10. Al retirar cada uno, `npm ls undici` /
  `npm ls postcss-selector-parser` y `npm audit` deben seguir limpios.
  Impacto bajo: son parches de la misma línea mayor, pero un override olvidado
  puede bloquear actualizaciones futuras.

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
