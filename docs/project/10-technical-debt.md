# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Para consultar el diseño de arquitectura, ver [`docs/master/`](../master/00-index.md).

Última revisión: **2026-11-07** (revisión general: cerrados TD-19, TD-23, TD-26, TD-32 y TD-38 b; ver `PROJECT_STATUS.md`). Anteriores: catálogo permanente, Fase 1: TD-39 a TD-45; chollos de usuarios: TD-24 a TD-35; entorno local: TD-36 a TD-38.

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

## 🟠 Media — catálogo permanente (Fase 1, 2026-11-06)

- **TD-41 — La ejecución manual de `price_check` es una petición HTTP síncrona.** Vista
  previa y «Aplicar» consultan Amazon dentro de la petición (≈ 1 s por cada 10 productos:
  ~18 s con 157). Con más de ~900 productos superaría los 100 s de Cloudflare (524). Ya no
  retiene conexión de BD durante la consulta ni puede solaparse con el worker. Proponer para
  Fase 3: ejecución en segundo plano (202 + estado del run), cadencia por prioridad (ofertas
  activas a diario, catálogo frío cada 3 días) y control del cupo diario de la Creators API,
  que depende de las ventas.
- **TD-39 — Precio de más de 24 h en las tarjetas si Amazon falla varios días.** La ficha
  avisa («Precio de hace N días: puede haber cambiado») y la de un chollo sin oferta oculta
  el precio, pero portada, listados y búsqueda siguen mostrando el último precio conocido.
  Con la revisión diaria solo ocurre si Amazon falla de forma prolongada. Opción: ocultar o
  marcar el precio en tarjetas cuando `last_price_check_at` supere 24 h.
- **TD-42 — Las alertas de usuario no vuelven a avisar de un chollo reactivado.**
  `AlertMatcher` deduplica por (alerta, deal) para siempre: quien ya recibió ese chollo no
  recibe su vuelta. Decidido así por prudencia; revisar con las alertas de precio de Fase 3.
- **TD-43 — Volver a dar de alta desde el panel un producto sin ASIN crea otro chollo.**
  El panel solo reconoce el producto por `external_id`; las propuestas sí buscan también
  por URL canónica y reactivan el existente. Unificar la búsqueda en `DealService`.
- **TD-44 — Menores de la revisión final del catálogo permanente.** (1) Un producto que
  entra y sale de stock a diario se reactiva cada día y sube a «Últimos» (el aviso a Admin
  sí está limitado a 1 cada 7 días). (2) Sin credenciales de Amazon todos los lotes fallan
  y aun así el run queda `completed`: registrar cuántos lotes fallaron o marcarlo fallido.
  (3) Revivir un chollo caducado como `scheduled` oculta su ficha indexada hasta la hora
  programada. (4) Sin savepoint por listing: un error de BD en uno revierte la revisión
  entera. (5) `started_at` y `finished_at` del run son el mismo instante (previo).
- **TD-45 — Menores del registro de publicaciones de Telegram.** (1) La corrección de
  precio solo cambia la primera línea 💶 y la primera «⚠️ Finaliza el» (un texto editado con
  dos líneas de precio o «⚠» sin selector de variante queda a medias) y no añade la fecha de
  fin si la publicación original no la tenía. (2) El panel registra los precios del chollo
  guardado, no los del texto editado si el formulario estaba sin guardar. (3) El panel no
  descarta respuestas tardías al cargar la última publicación. (4) El flujo rápido heredado
  (`/telegram/notify` sin `text`) no se registra; no lo usa el frontend. (5) Reenviar a mano
  desde el canal Admin al oficial no queda registrado.
- **TD-40 — Columnas `restored_at`/`restored_deal_id` sin uso** en
  `scheduled_task_run_items` desde que no hay nada que restaurar. Se conservaron para no
  tocar el histórico; eliminarlas en una migración posterior cuando deje de importar.

## 🟠 Media — chollos de usuarios (cierre 2026-11-04)

- **TD-24 — Imágenes huérfanas en `deal-images/submissions/`.** Una imagen subida y
  nunca enviada en una propuesta (usuario que abandona el formulario) o las de una
  cuenta eliminada no se borran. Falta una tarea programada (ADR-012) que borre objetos
  sin referencia en `deal_submissions.images` / `deals.images` con antigüedad suficiente.

- **TD-25 — Ventana de DNS rebinding en los fetchers de URL externas.** `core/ssrf.py`
  resuelve el host y valida la IP, pero `httpx`/`requests`/`urllib` vuelven a resolverlo
  al conectar; un DNS malicioso podría responder distinto la segunda vez. Afecta al
  fetcher de imágenes de propuestas, a la pre-descarga de imágenes para Telegram y a la
  resolución de acortadores de Amazon (esta última acotada por la allowlist de hosts).
  Mitigación: conectar a la IP ya validada (con `Host`/SNI del original) o transporte
  con resolver propio.

- **TD-28 — Rate limit con almacenamiento en memoria por worker.** `slowapi`/`limits`
  sin Redis: con 2 workers los límites efectivos se duplican y se reinician al reiniciar
  el contenedor. Aceptable hoy (un solo proceso por servicio); revisar al escalar.

- **TD-29 — Cuota de propuestas "comprobar y luego insertar" no atómica.** Dos
  peticiones simultáneas del mismo usuario pueden pasar el límite de pendientes/día; solo
  los índices únicos parciales (mismo producto) lo acotan. Impacto bajo, con rate limit
  por usuario delante.

- **TD-30 — Sin reintento si falla el correo al usuario.** El notificador de propuestas
  solo registra el fallo; el usuario conserva la notificación in-app.

- **TD-31 — El runtime del NAS depende de la copia de trabajo de desarrollo.** Los
  contenedores montan `.:/app` y el NAS ve la misma carpeta que `Z:`: la rama activa al
  reiniciar o reconstruir es lo que ejecuta producción. Trabajar en `develop` cambia en
  silencio lo que correría tras un reinicio (a 2026-11-04 la API se caería: sin `Pillow` en
  la imagen y, al volver a `main`, Alembic no encuentra la revisión). Proponer desplegar
  desde un checkout o tag separado en el NAS, o copiar el código a la imagen en lugar de
  montarlo. Mientras tanto, ver el aviso en `08-deployment.md`.

- **TD-32 — Duplicación menor de lógica.** El cálculo de `canonical_url` está duplicado entre
  `DealService._canonical_url_for` (`deal_service.py`) y `compute_canonical`
  (`scripts/backfill_canonical_urls.py`). (La limpieza de la URL de Supabase ya está
  centralizada en `Settings.supabase_base_url` desde 2026-11-07.)

- **TD-33 — `external_id` no Amazon en mayúsculas al aprobar.** Puede no detectar un
  duplicado con SKU en minúsculas (`canonical_url` sí lo detecta).

- **TD-34 — Acortadores sin resolver.** `amzn.asia` y `amzn.com` no se resuelven (los
  acortadores genéricos se rechazan; los de Amazon `amzn.to`/`amzn.eu`/`a.co`/`link.amazon`
  sí se resuelven).

- **TD-35 — Menores de la revisión.** `previously_published` pasa a verdadero para
  aprobadas cuya ficha ya expiró; las peticiones sin autenticar a los endpoints de
  propuestas se rechazan con 401 antes de que cuente el límite por usuario (aceptable: el
  JWT se verifica en local).

- **TD-36 — `supabase/migrations/*.sql` no describe el esquema real de producción.**
  Detectado al montar el entorno local (2026-11-04): en producción los enums
  (`deal_status`, `app_role`, …) son `text`, `deals.images` es `jsonb`, varias columnas
  son nullable y no existen los triggers/funciones de esas migraciones (contadores,
  `process_deal_statuses`, pg_cron). Reproducir esas migraciones da otro esquema. El
  entorno local usa `pg_dump --schema-only` de producción (ver `docs/guides/LOCAL-ENV.md`).
  Proponer: generar una migración *baseline* SQL a partir del volcado real y archivar las
  antiguas, para que un proyecto Supabase nuevo salga igual que producción.

- **TD-37 — Los clientes Supabase REST del backend ignoran `DATABASE_URL`.**
  `DealCleanerService` (scheduler), `SupabaseCategoryClient` (preview con IA) y la
  borrada de cuenta hablan con Supabase por REST/Admin API, no con la base configurada.
  En producción da igual, pero en local obliga a mantener el scheduler apagado (su
  limpieza borraría chollos de PRODUCCIÓN). Proponer: pasar la limpieza a SQLAlchemy.

## 🟡 Baja — observabilidad y hardening de cuenta

- **TD-27 — `TelegramPanel` desborda 8 px a 375 px de ancho.** Preexistente (visto en la
  verificación visual de chollos de usuarios). Arreglar con `min-w-0`/`flex-wrap` en el
  panel y fijarlo con una comprobación a 375 px en el E2E.

- **TD-38 — Menores vistos en la prueba exhaustiva en local (2026-11-04).**
  (a) `AppearanceToggle` (menú lateral) provoca un *hydration mismatch* en consola
  (el tema se lee de `localStorage` solo en cliente). (c) Una subida de
  más de 5 MB que se salta la validación del cliente recibe la conexión cerrada en vez del
  413 (la web ya valida antes de subir).

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

---

> 🔁 **Cómo usar esta página:** revisar al empezar cada tanda de trabajo. Al cerrar un
> item, borrar su entrada y anotar el cierre (fecha + commit) en `PROJECT_STATUS.md`.
