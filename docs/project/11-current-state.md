# ✅ 11 · Estado actual verificado

> Fotografía del estado funcional y operativo de BuenCholloTech.
> Última revisión: **2026-11-25** (`main` con las PR #104 a #117: Coolmod activo, tarjeta de oferta, posts sin líneas de precio, Instagram activo con token de usuario del sistema e `INSTAGRAM_CHANNELS`, bus de eventos entre módulos y «Top de la semana» solo con chollos publicados por primera vez; Alembic `20261124150000`).
> La cronología completa está en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md);
> los pendientes, en [`10-technical-debt.md`](10-technical-debt.md); la auditoría
> más reciente, en [`12-auditoria-tecnica-2026-11.md`](12-auditoria-tecnica-2026-11.md).

---

## 🌐 Producción

| Pieza | Estado actual |
|---|---|
| Web | `https://buenchollotech.com`: React 19 + TanStack Start SSR en Cloudflare Workers. Se despliega sola al hacer merge a `main` (Workers Builds). |
| API | `https://api.buenchollotech.com`: FastAPI en Docker sobre el NAS Synology, publicada con Cloudflare Tunnel (sin puertos abiertos ni DDNS). |
| Base de datos | PostgreSQL de Supabase por PgBouncer (puerto 6543). |
| Autenticación | Supabase Auth (email/contraseña y Google OAuth); la API valida el JWT en local con JWKS ([ADR-010](../adr/ADR-010-validacion-jwt-local.md)). |
| Correo | Zoho Mail (`smtp.zoho.eu:465`): remitente `info@`, respuesta a `contacto@buenchollotech.com`. |
| Contenedores NAS | `buenchollo-api`, `buenchollo-scheduler` y `cloudflared`. |
| Despliegue de la API | El NAS ejecuta el código del share montado: se actualiza el share a `main` y se reinicia (`docker restart`) o se reconstruye si cambian dependencias. Las migraciones Alembic corren al arrancar. Procedimiento: [`08-deployment.md`](08-deployment.md). |

---

## 🧩 Funcionalidad

### Web pública

- **Chollos**: portada con banner de tops, feed de tarjetas horizontales, detalle, búsqueda, categorías y subcategorías, favoritos, votos y comentarios.
- **Catálogo permanente** ([ADR-017](../adr/ADR-017-catalogo-permanente.md)): los chollos caducados no se borran. Conservan ficha, URL, votos y comentarios; salen de los listados activos y la ficha indica que la oferta terminó. Si el producto vuelve a cumplir las reglas, se reactiva el mismo chollo.
- **Tops comunitarios** ([ADR-018](../adr/ADR-018-tops-comunitarios-productos.md)): cada categoría y subcategoría muestra podio (1 a 3) y lista hasta el puesto 10. Compiten automáticamente todos los productos con alguna oferta pública (`active` o `expired`); los vinculados solo a borradores quedan fuera. Un voto por usuario y producto, que se retira repitiéndolo; en empate, primero la oferta activa y luego fecha e ID. El voto se da en el top, en la tarjeta y en la ficha («Votar producto», distinto del pulgar de la oferta) y comparte un único estado en el cliente (`features/catalog/productVotes.ts`). `GET /v1/catalog/tops/{slug}`, `GET /v1/catalog/my-votes` y `POST /v1/catalog/products/{id}/vote` (30 por minuto).
- **Banner de portada**: podio con fotos reales de las seis primeras categorías con ofertas. Rota cada 5 s con flechas, respeta el movimiento reducido, no avanza con la pestaña oculta y reutiliza 60 s el resultado en el navegador (el SSR consulta siempre). Si falla una imagen muestra un icono y, sin tops, conserva el CTA.
- **Descubrimiento y SEO**: navegación Inicio, Chollos, Tops, categorías y Blog; categorías y tops se cargan en los loaders, así que el HTML inicial ya lleva enlaces y contenido. Detalle en [`13-seo.md`](13-seo.md).
- **Comunidad**: alertas personalizadas, notificaciones in-app y resumen diario por correo (21:00), comentarios y votos, proponer chollos (`/publicar`, `/mis-chollos`) con comprobación de enlace, prefill de Amazon e imágenes subidas, pegadas o por URL ([ADR-015](../adr/ADR-015-ingesta-imagenes-backend.md), [ADR-016](../adr/ADR-016-propuestas-comunidad-y-afiliados.md)).
- **Blog** con categorías, comentarios, votos, RSS, sitemap y contador público de lecturas.
- **Cuenta**: confirmación por correo en el registro, recuperación de contraseña, correo de bienvenida idempotente, perfil, Google OAuth y páginas legales.
- **Atribución**: las rutas `/telegram` y `/whatsapp` fijan `utm_source=telegram` / `utm_source=whatsapp` y redirigen a la portada; cada canal sale como fuente propia en la analítica. El enlace afiliado de compra no cambia.
- **Versión WhatsApp**: cada publicación de Telegram (panel, programadas y avisos de bajada) envía un segundo mensaje al canal Admin con la versión para el Canal de WhatsApp (emojis estándar, enlace `/whatsapp`), lista para copiarla a mano: WhatsApp no tiene API oficial para Canales. Con `WHATSAPP_ENABLED=true` (producción desde el 2026-11-26) esa copia solo se envía para lo que no sale solo en el Canal (canales fuera de `WHATSAPP_CHANNELS`): los chollos y el resumen semanal van solos; las republicaciones por bajada de precio solo salen en Telegram (requieren revisión).
- **Canal de WhatsApp automático** (2026-11-26, [ADR-024](../adr/ADR-024-publicacion-canal-whatsapp.md), **activo** en el Canal «Buenchollo Tech»): los chollos de los canales de Telegram de `WHATSAPP_CHANNELS` se encolan en `whatsapp_posts` por el bus de eventos y el job `publish_whatsapp_queue` (cada minuto) los publica en el Canal con la tarjeta y la versión WhatsApp a través del contenedor `buenchollo-whatsapp` (`whatsapp-gateway/`, Baileys vinculado como dispositivo). Ritmo: una por paso, ≥ 20 min entre dos y ≤ 15 al día; margen aleatorio de 45-180 s; sin repetir un chollo en 24 h; si la imagen falla dos veces sale solo el texto; solo cuenta como publicado lo que WhatsApp acusa. Estado en `GET /v1/whatsapp/status`. Guía: [`WHATSAPP.md`](../guides/WHATSAPP.md).

### Administración

- CRUD de chollos, categorías, tiendas, usuarios y blog; moderación de propuestas en `/admin/propuestas` (editar, aprobar como publicado, programado o borrador, o rechazar con motivo; el autor recibe correo y notificación).
- Autocompletado desde enlaces oficiales de Amazon (`amazon.*`, `amzn.*`, `link.amazon`) con Creators API, Keepa y el motor de IA unificado ([ADR-013](../adr/ADR-013-motor-ia-unificado-omniroute-modelos-gratuitos.md)).
- **Autocompletado de Awin / Tradedoubler con IA** (2026-11-21): tras importar del catálogo (`POST /v1/affiliates/import`), el editor pide a `POST /v1/products/enrich` (solo admin, 10/min, timeout de 60 s en el cliente) la descripción corta, la larga, el post de Telegram y la categoría, con el mismo `EnrichProductUseCase` que Amazon. Solo rellena lo vacío y descarta la respuesta si el formulario ya es otro. Si la IA cae, el enriquecedor marca sus textos de rescate (`copy_fallback`), la API responde `copy_ok: false` y el panel solo resume la descripción del catálogo (frases completas, 500 caracteres) sin poner categoría; si la llamada falla o caduca, también resume. Los datos de la tienda van delimitados en el prompt. El precio anterior sigue siendo manual. Detalle: [`AFFILIATE-NETWORKS.md`](../guides/AFFILIATE-NETWORKS.md).
- **Editar chollo** carga cualquier chollo por id y guarda un borrador de Telegram (`deals.telegram_text`) que reutiliza el último envío o genera la línea de copy con IA; la ficha pública permite a los admins eliminar el chollo.
- **Tarjeta de oferta** (2026-11-23, [ADR-021](../adr/ADR-021-tarjeta-oferta-telegram.md)): la imagen de cada chollo en Telegram (panel, programadas, republicación al canal Admin y copia de WhatsApp) es una tarjeta 1200 × 800 generada con Pillow (`deal_card.py`, `deal_photo.py`): foto, descuento, logo de la tienda, precio, anterior tachado, ahorro y logo del canal. Si no se puede (sin precio anterior, foto ilegible, fallo), sale la foto original. Se apaga con `DEAL_CARD_ENABLED=false`. Guía: [`TELEGRAM-TARJETA-OFERTA.md`](../guides/TELEGRAM-TARJETA-OFERTA.md).
- **Instagram** (activo desde 2026-11-24 en @buenchollotech, [ADR-022](../adr/ADR-022-publicacion-instagram.md)): cada chollo publicado en los canales de Telegram de `INSTAGRAM_CHANNELS` (prod: principal y Admin, donde salen las programadas) llega por el bus de eventos ([ADR-023](../adr/ADR-023-bus-de-eventos-entre-modulos.md)) y se encola en `instagram_posts` y un job del scheduler (cada 2 min) lo publica en el feed con la API oficial: la misma tarjeta 1200 × 800 y el texto adaptado (sin enlaces, «🔗 Enlace al chollo en nuestra bio» y hashtags). Instagram descarga la imagen de `/v1/instagram/media/{id}.jpg` mientras está pendiente. Reintentos y aviso al administrador (`AdminAlert`); token de usuario del sistema de Meta Business sin caducidad. La bio enlaza a `/instagram` (fuente «Instagram» en la analítica). Se activa con `INSTAGRAM_ENABLED` + `INSTAGRAM_ACCESS_TOKEN`; estado en `GET /v1/instagram/status`. Guía: [`INSTAGRAM.md`](../guides/INSTAGRAM.md).
- **Telegram**: el icono premium del enlace de compra (🛒) depende de la tienda (`link_icon_for` en `telegram/application/post_generator.py`): por la tienda del chollo o, si no se conoce, por el dominio del enlace. Tienen logo propio Amazon, Xiaomi, AliExpress y Steam (`STORE_LINK_ICONS`); el resto usa el genérico. Samsung (dos emojis) y WhatsApp están guardados sin usar (TD-64). Registro y proceso: [`TELEGRAM-EMOJIS.md`](../guides/TELEGRAM-EMOJIS.md). El aviso de afiliación del post lo decide el servidor: `/telegram/generate` recibe `affiliate_program_id` y lee el «Aviso adicional del programa» de la BD; el `notice` que mande el cliente se ignora. Desde el 2026-11-23 (#112) el texto del post no repite «💶 Precio» ni «💰 Ahorro», que ya muestra la tarjeta: la plantilla no los escribe si habrá tarjeta y, al enviar, se quitan con tarjeta o se añaden si sale la foto original. Previsualización, envío inmediato y programación; cada publicación queda registrada (`telegram_publications`). Se puede programar con la ficha web incompleta (queda en borrador y el calendario avisa).
- **Revisión diaria de precios** (`price_check`, [ADR-012](../adr/ADR-012-motor-tareas-programadas.md) y ADR-017): actualiza precio y stock de los listings de Amazon, termina o reactiva ofertas y avisa de bajadas al canal Admin solo si el chollo se publicó hace 10 días o más (antispam de 7 días). La purga solo afecta a listings sin disponibilidad confirmada durante 30 días.
- **Portada y tarjetas** (2026-11-20): las tarjetas ya no muestran temperatura, voto de producto ni contador de comentarios (siguen en la ficha), y el botón a la tienda dice «Ir a la oferta» en todas partes. La portada no tiene pestañas de orden: lista siempre los chollos más nuevos. Desde el 2026-11-21 tampoco hay «Más populares» (ni en el lateral, ni en el menú, ni en `/explorar`): ordenaba por votos, todos a 0. Desde el 2026-11-21 las preguntas frecuentes no están en la portada: tienen su página, `/preguntas-frecuentes` (12 preguntas, enlazada en el pie). La ficha del chollo en el móvil es más compacta (título, precio, tienda, fin de oferta y botón juntos, sin el hueco de la rejilla).
- **«Top de la semana»** (2026-11-21): en el lateral de la portada, donde estaba «Más populares». Los 10 activos con más descuento publicados **por primera vez** en los 7 días naturales anteriores (hora de Madrid, `deals/domain/week.py`; desde el 2026-11-24, #117, filtra por `deals.first_published_at`, así que un chollo antiguo reactivado no entra): el mismo ranking que el resumen de los domingos. Se calcula en cada visita (`GET /v1/deals/weekly-top`), así que entra lo nuevo y cambia de orden solo; «Nuevo» marca lo dado de alta en las últimas 24 h. Como el resumen, deja fuera los chollos de Awin/Tradedoubler que no cumplen las reglas de publicación (`deals/application/weekly_top.py`, común a ambos).
- **Novedades desde tu última visita** (2026-11-21): sin cuenta, el navegador recuerda la última visita (`lib/lastVisit.ts`, `localStorage`; una visita termina tras 30 min sin actividad). «Inicio» muestra «N nuevos» (`GET /v1/deals/new-count?since=`, como mucho 30 días) y la portada separa lo nuevo con «Hasta aquí, lo nuevo desde tu última visita».
- **Títulos normalizados** (2026-11-21): `deals/domain/titles.py` limpia caracteres raros («，», comillas y guiones tipográficos, ™ ®), espacios y comas pegadas, y pasa a formato normal los títulos enteros en mayúsculas, respetando modelos, siglas y marcas. Se aplica al publicar o editar (todas las vías pasan por `DealService`); los ya publicados se limpiaron con `scripts/normalize_titles.py`. Los slugs no cambian.
- **«Los chollos de la semana»** (2026-11-21): job del scheduler los domingos a las 22:30 (Madrid). Los 10 chollos activos con más descuento publicados **por primera vez** en los 7 días naturales anteriores (desde el 2026-11-24 se usa `deals.first_published_at`, que no cambia al reactivar un chollo antiguo; antes se colaban reactivados de hace meses), al canal **Admin** en dos mensajes: la publicación de Telegram, en un solo mensaje como los chollos (collage 1200×800 (3:2, el mismo formato que la tarjeta de cada chollo, para que todo el canal tenga el mismo ancho; 5 columnas × 2 filas) con número, foto, precio y descuento de cada chollo en grande, sin títulos —`weekly_collage.py`, tipografía Space Grotesk de `app/assets/fonts`— y el texto —cada chollo con su número en emoji, 1️⃣ a 🔟— con los enlaces como pie de foto, recortado hasta caber en los 1024 caracteres de Telegram: primero se acortan los títulos (hasta 16 caracteres) para conservar la línea «💶 precio | -descuento | antes: precio anterior», luego se quita el «antes»; los enlaces siempre enteros). Cabecera del collage: solo «LOS CHOLLOS DE LA SEMANA», centrada, y la versión WhatsApp con el texto completo. Si el collage falla, sale el texto completo sin imagen. Los de Awin/Tradedoubler pasan las reglas de publicación. Se apaga con `WEEKLY_DIGEST_ENABLED=false`. Admin: `GET /v1/telegram/weekly-digest` (vista previa del texto), `GET /v1/telegram/weekly-digest/image` (collage en JPEG) y `POST /v1/telegram/weekly-digest/send` (enviar ahora).
- **Campañas estacionales** (2026-11-20): landing `/black-friday` y hero de campaña en portada desde `promoteFrom` hasta el final del evento (Cyber Monday). Desde el 2026-11-21 ambos usan el mismo rótulo de neón (`CampaignHero`, fuente Monoton) con cuenta atrás por segundos. Fuera de campaña vuelve el banner de tops. Configuración en `buenchollo-web/src/lib/campaigns.ts`.
- **Histórico de precios** ([ADR-020](../adr/ADR-020-historico-de-precios.md)): `price_history` guarda un punto por listing y día, alimentado por la revisión diaria y por las altas y ediciones de chollos de cualquier tienda. API: `GET /v1/catalog/products/{id}/price-history`. Todavía sin interfaz.
- **Redes de afiliación** ([ADR-019](../adr/ADR-019-redes-afiliacion-awin-tradedoubler.md)): **Coolmod (Awin, 124624) activo** desde el 2026-11-21: programa habilitado (web y Telegram), feed 114170 sincronizado (12.995 productos) y enlace afiliado verificado hasta la ficha con atribución. Samsung ES aceptado pero sin habilitar; Fnac ES rechazado; PcComponentes y Miravia pendientes; Tradedoubler (MediaMarkt) sin feeds. Estado por tienda y cómo activar otra: [`AFFILIATE-ACTIVATION-RUNBOOK.md`](../guides/AFFILIATE-ACTIVATION-RUNBOOK.md).
  - **Aviso genérico retirado** (2026-11-22): la migración `20261122120000` vacía el «Enlace de afiliado: podemos recibir una comisión…» sembrado en todos los programas. El campo «Aviso adicional del programa» queda solo para la tienda cuyas condiciones exijan un texto propio.
  - **Términos partidos del feed**: Coolmod entrega «PC Ie», «NV Me», «5600M Hz», «AS Rock»…; `fix_split_terms` (`affiliates/domain/offers.py`) los recompone al leer el feed.
- Analítica first-party ([ADR-014](../adr/ADR-014-analitica-first-party-atribucion-sesiones.md)): visitas, visitantes únicos, sesiones, procedencia, lecturas del blog y conversión Telegram a blog (fuentes propias para Telegram, WhatsApp e Instagram); exclusión del dispositivo del administrador. Los identificadores se seudonimizan con HMAC (`ANALYTICS_HASH_SECRET`) y la retención máxima configurable es de 25 meses.

### Módulos del backend

`affiliates`, `ai`, `alerts`, `analytics`, `blog`, `blog_comments`, `catalog`, `categories`, `comments`, `deals`, `emails`, `instagram`, `notifications`, `products`, `scheduled_deals`, `scheduled_tasks`, `stores`, `submissions`, `telegram`, `users` y `whatsapp`.

Los módulos no se importan entre sí para reaccionar a lo que hace otro: bus de eventos en `app/core/events.py`, suscriptores en `app/core/bootstrap.py` ([ADR-023](../adr/ADR-023-bus-de-eventos-entre-modulos.md)). Los routers de negocio cuelgan de `/v1`; `/health` y `/health/ready` quedan fuera. El frontend solo accede a datos de negocio por la API; las excepciones deliberadas son Supabase Auth y Storage.

---

## 🔌 Integraciones y configuración crítica

| Integración | Variables relevantes |
|---|---|
| Supabase | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET` |
| Analítica | `ANALYTICS_HASH_SECRET`, `ANALYTICS_RETENTION_MONTHS` |
| Amazon | `AMAZON_CLIENT_ID`, `AMAZON_CLIENT_SECRET`, `AMAZON_AFFILIATE_TAG` |
| IA | `AI_PROVIDER`, `AI_BASE_URL`, `AI_MODEL`, fallbacks y OpenAI opcional |
| Telegram | token del bot, canales principal y Admin, `TELEGRAM_ENABLED` |
| Instagram | `INSTAGRAM_ENABLED`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID`, `INSTAGRAM_CHANNELS`, `PUBLIC_API_URL` ([`INSTAGRAM.md`](../guides/INSTAGRAM.md)) |
| Afiliación | credenciales de Awin y Tradedoubler ([`AFFILIATE-NETWORKS.md`](../guides/AFFILIATE-NETWORKS.md)) |
| Frontend | `VITE_API_URL`, credenciales públicas de Supabase, `VITE_SENTRY_DSN` opcional |

Los valores reales viven fuera de Git; `.env.example` de cada paquete es la plantilla y [`04-configuration.md`](04-configuration.md) lo explica.

---

## 🧪 Calidad

Cifras vigentes en [`06-testing-and-quality.md`](06-testing-and-quality.md): backend 812 unitarios + 59 de integración (cobertura 83 %), frontend 532 tests Vitest y 12 specs E2E (37 tests). El CI (`.github/workflows/ci.yml`) es la autoridad sobre qué se ejecuta y exige `pip-audit`, `npm run audit:prod`, gitleaks, TypeScript, ESLint y Prettier.

## 🗄️ Datos y migraciones

- Alembic tiene una única cabeza (`20261124150000`, columna `deals.first_published_at` con trigger que la rellena al pasar a `active` y relleno del histórico). Las anteriores: `20261124130000` (tablas de Instagram `instagram_posts` e `instagram_account`) y `20261124120000` (fuente `instagram` en la analítica). Detalle: [`MIGRATIONS.md`](../guides/MIGRATIONS.md).
- Cada tabla nueva de `public` activa RLS en su propia migración; `test_migrations_rls.py` lo comprueba.
- La API usa la conexión de servicio y las credenciales privilegiadas nunca llegan al navegador.
- Los buckets de Storage (avatares, imágenes de chollos y blog) tienen políticas propias.

## 🚧 Pendientes abiertos

El registro canónico es [`10-technical-debt.md`](10-technical-debt.md). Lo más relevante hoy:

1. Rotar y verificar el token de Cloudflare Tunnel (TD-21).
2. El NAS ejecuta la copia de trabajo del share: mantenerla siempre en `main` (TD-31).
3. Operación débil según la auditoría de 2026-11: backups manuales, sin alertas de caída y `main` sin protección de rama (AUD-03, AUD-04, AUD-06).
4. Redes de afiliación: Awin ya validado en vivo con Coolmod; falta Tradedoubler para cerrar TD-46. Siguen TD-47 a TD-49 (deeplink de Tradedoubler, programar chollos de redes, purga del catálogo de feeds).
5. Iconos de Samsung y WhatsApp guardados sin usar en los posts (TD-64) y cabecera que desborda a 320 px con sesión iniciada (TD-63).
6. Instagram: sin historias (TD-65), app de Meta en modo desarrollo y porfolio sin verificar (TD-66); los tests leen el `.env` real (TD-67).
7. Pendiente de producto: puntos y recompensas para usuarios (fuentes de puntos, límites contra abuso, historial auditable y niveles); requiere decisión y modelo propios.

---

## 🗺️ Dónde mantener cada cambio

| Cambio | Documento que debe actualizarse |
|---|---|
| Estado operativo o release | `PROJECT_STATUS.md` y esta página |
| Nueva variable | `.env.example` y `04-configuration.md` |
| Decisión difícil de revertir | Nuevo ADR y `docs/adr/00-index.md` |
| Funcionalidad o flujo | `01-overview.md` y esta página |
| Arquitectura o despliegue | `03-project-structure.md`, `08-deployment.md` y la guía correspondiente |
| Deuda abierta | `10-technical-debt.md` |
| Conocimiento reutilizable | Ficha relacionada en la base de conocimiento privada del propietario (OBSIDIAN VAULT, `SCHEMA.md`) |

---

[← Deuda técnica](10-technical-debt.md) · [Índice operativo](00-index.md)
