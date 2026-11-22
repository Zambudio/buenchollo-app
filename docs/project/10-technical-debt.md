# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Para consultar las decisiones de arquitectura, ver [`docs/adr/`](../adr/00-index.md).

Última revisión: **2026-11-18** (auditoría técnica: lo corregido se cierra en `PROJECT_STATUS.md` y en el § 9 de [`12-auditoria-tecnica-2026-11.md`](12-auditoria-tecnica-2026-11.md); lo pendiente entra aquí como TD-52 a TD-62). Anteriores: catálogo permanente, Fase 1: TD-39 a TD-45; chollos de usuarios: TD-24 a TD-35; entorno local: TD-36 a TD-38.

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

## 🔴 Alta — requieren al propietario (auditoría 2026-11-18)

- **TD-52 — Copia de seguridad fuera del NAS.** El servicio `db-backup` hace un `pg_dump`
  diario validado con 14 días de retención, pero en el propio NAS: si se pierde el NAS, se
  pierden las copias y el `.env` (todas las credenciales). Decidir destino externo (Synology
  Hyper Backup de `buenchollo-api/backups/` y de una copia cifrada del `.env`) y, si se
  quiere RPO menor de 24 h, un plan de Supabase con backups gestionados o PITR. Ver
  `docs/guides/BACKUP-RESTORE.md`.
- **TD-53 — Alta en Google Search Console y Bing Webmaster Tools.** Verificar el dominio por
  DNS en Cloudflare, enviar `/sitemap.xml`, revisar el informe de páginas no indexadas tras
  el despliegue SEO y activar *Crawler Hints* (IndexNow). Ver `13-seo.md` § 5.

## 🟠 Media — auditoría técnica 2026-11-18 (pendiente)

- **TD-54 — Transacciones confirmadas en varios sitios (AUD-11).** `get_db`, algunos routers
  (`submissions`, `scheduled_tasks`) y repositorios (`catalog/top_repository`,
  `affiliates/repository`) hacen `commit()`; el de `get_db` ocurre tras enviar la respuesta.
  Unificar la unidad de trabajo antes de responder y prohibir `commit()` en repositorios.
- **TD-55 — `GET /deals/{slug}` devuelve borradores y programados (AUD-12)** y campos internos
  (`import_snapshot`, `price_reference_evidence`). La ficha pública ya los marca `noindex`,
  pero la API los sirve a quien adivine el slug. Requiere mover la vista previa de borradores
  del admin a un endpoint de admin antes de filtrar el público.
- **TD-56 — Reenvío de una publicación programada si falla la BD justo después de enviarla.**
  AUD-10 confirma cada programación por separado; queda el caso de fallo al guardar el
  estado final de la misma. Solución completa: marcar «publicando» antes de enviar
  (patrón *outbox*).
- **TD-57 — Frontend: bundle inicial de 776 kB y componentes grandes (AUD-17, AUD-18).**
  Analizar el chunk inicial y separar por ruta; extraer hooks y subcomponentes de
  `chollo.$slug.tsx`, `RecommendedAlertsBlock`, `TelegramPanel`, `admin.chollos.tsx` y
  `ScheduledDealsCalendar`; un único patrón de carga de datos (TanStack Query) y
  `QueryClient` por petición en el Worker.
- **TD-58 — Accesibilidad (AUD-19).** Lightbox de la ficha y panel de Telegram con diálogos
  hechos a mano (sin foco ni Escape); ≈ 80 controles sin etiqueta asociada; textos de 10 px.
- **TD-59 — Huecos de test (AUD-22).** Tests de contrato con respuestas grabadas de Amazon y
  OmniRoute; tests propios de `notifications`; un E2E de humo contra la API real.
- **TD-60 — Versión desplegada visible y latido del scheduler (AUD-04, AUD-23).** `/health` no
  dice qué commit corre y nada avisa si el scheduler deja de ejecutar jobs (el monitor de
  GitHub Actions solo comprueba web y API).
- **TD-61 — Despliegue por imagen versionada (AUD-02).** Complementa TD-31: construir la imagen
  con el código dentro y una etiqueta por versión, para tener rollback real.

## 🟡 Baja — auditoría técnica 2026-11-18 (higiene)

- **TD-62 — Menores de la auditoría.** Utilidades repetidas (formato de precio, slug,
  paginación, `amazon.es/dp/…`); tres pilas HTTP (`requests`, `httpx`, `urllib`, relacionado
  con TD-25); `DealCreate`/`DealUpdate` con 28 campos duplicados; funciones de complejidad
  alta en afiliación y analítica; fugas de capas puntuales (router de Telegram con lógica de
  publicación); clientes con estado creados por petición; `selectinload` en relaciones
  muchos-a-uno; `avatar_url` sin lista de hosts; `X-Request-Id` sin límite; IDs no UUID que
  dan 500; `ilike` sin escapar; correo del destinatario en logs INFO; `cloudflared` recibe
  todo el `.env`; logos de marca enlazados desde Wikimedia; tipos de la API escritos a mano;
  componentes de `components/ui` sin uso. Detalle en el § 5.3 del informe de auditoría.

## 🟡 Baja — responsive (2026-11-21)

- **TD-63 — Cabecera desborda a 320 px con sesión iniciada.** En pantallas de 320 px
  (móviles muy estrechos) y con sesión iniciada, la fila derecha de la cabecera
  (`components/layout/Header.tsx`: publicar, notificaciones, avatar y menú) no cabe y
  produce unos 30 px de desplazamiento lateral en toda la web. A 360 px o más no ocurre.
  Detectado al corregir el desborde de la ficha del chollo (2026-11-21).
- **TD-64 — Icono de Samsung (dos emojis) y de WhatsApp sin usar en los posts.** Los
  `custom_emoji_id` están guardados (`SAMSUNG_LINK_ICON_PARTS`, `WHATSAPP_ICON` en
  `telegram/application/post_generator.py`). Samsung necesita que el post escriba dos
  emojis base en el enlace y que `build_entities` asigne las dos mitades; hasta entonces usa
  el genérico. WhatsApp espera a decidir cómo se enlaza el Canal desde los posts. Detalle en
  `docs/guides/TELEGRAM-EMOJIS.md` (2026-11-22).

## 🟡 Baja — dependencias (2026-11-18)

- **TD-50 — `picomatch` con aviso high sin versión corregida (GHSA-fc5q-39xc-vjpf).**
  ReDoS en extglobs repetidos; afecta a `<=4.0.7`, la última publicada. Llega vía
  `vite`, `@tanstack/react-start` (start-plugin-core, router-generator) y `unplugin`:
  solo herramientas de build con patrones de rutas del propio repo; no entra en el
  bundle del Worker ni procesa entrada de usuarios. Aceptado hasta 2027-01-31 en
  `buenchollo-web/audit-allowlist.json` (lo aplica `npm run audit:prod`, que usa el CI).
  Cerrar: actualizar cuando salga la versión corregida y quitar la excepción.
- **TD-51 — Motor «OmniRoute» (solo gratuitos) poco fiable para el copy de Telegram.**
  `OpenAICompatibleLLMClient` da 3,5 s a cada modelo gratuito antes de pasar al siguiente
  (ADR-013, pensado para fallar rápido). Escribir 2-3 líneas suele tardar más y, sin
  fallback a OpenAI en ese modo, `POST /v1/telegram/generate` acaba usando la descripción
  corta (el panel lo avisa). «Automático» y «OpenAI» funcionan. Opciones: un timeout por
  tipo de tarea en el cliente o recomendar «Automático» por defecto en ese botón.

## 🟠 Media — redes de afiliación (Awin / Tradedoubler, 2026-11-08)

- **TD-46 — Integración Awin/Tradedoubler sin validar en vivo.** En producción desde
  2026-11-08 (PR #78) con credenciales configuradas, pero sin ningún programa aprobado
  (Awin `pending`, Tradedoubler sin feeds). Parser probado solo con fixtures. Falta:
  aprobación de las tiendas y contrastar con datos reales las columnas del feed Awin, la
  respuesta de la Products API (`offers`, `priceHistory`, `productImage`) y la zona horaria
  de `last_updated`. Procedimiento: `docs/guides/AFFILIATE-ACTIVATION-RUNBOOK.md`.
  **2026-11-21: Awin validado en vivo con Coolmod** (feed CSV de 12.995 filas sin errores:
  título, precio, envío, stock, marca, EAN, imagen y categoría bien leídos; el feed no trae
  PVP). Queda Tradedoubler (MediaMarkt sigue sin feeds) para cerrarla.
- **TD-47 — Deeplink de Tradedoubler sin ficha no documentado públicamente.** Solo se usa
  si el propietario lo confirma por programa («Deeplink verificado»).
- **TD-48 — Programar publicaciones exige ASIN.** Los chollos de redes no se pueden
  programar todavía (`scheduled_deals`); se publican a mano tras revisar.
- **TD-49 — Catálogo local de feeds sin purga por desuso.** Una sincronización sustituye
  la generación anterior, pero un feed deseleccionado conserva sus filas hasta borrarlo.
  Añadir borrado al deseleccionar o a los N días según las condiciones de cada programa.

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
  contenedores montan `.:/app` y el NAS ve la misma carpeta que la unidad mapeada de desarrollo: la rama activa al
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
  cerrados (ver el histórico de `PROJECT_STATUS.md`). Este último requiere
  un toggle manual en el dashboard (Authentication → Policies): no hay
  migración ni tool del conector MCP que lo aplique. Detalle completo (por si
  se automatiza en el futuro vía Management API): la configuración vive en el
  panel de Supabase Auth, no en el repositorio.
  Impacto bajo (no expone datos; endurece cuentas de usuario contra
  credential stuffing).

---

> 🔁 **Cómo usar esta página:** revisar al empezar cada tanda de trabajo. Al cerrar un
> item, borrar su entrada y anotar el cierre (fecha + commit) en `PROJECT_STATUS.md`.
