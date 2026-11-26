# PROJECT_STATUS — BuenCholloTech
*Actualización de producción: 2026-11-24 — `main` con Instagram activo en @buenchollotech (ADR-022), bus de eventos entre módulos (ADR-023), collage semanal en 1200×800 y el «Top de la semana» solo con chollos publicados por primera vez esa semana (#117). Alembic `20261124150000`.*

> Bitácora cronológica inversa. Estado operativo vigente: [`docs/project/11-current-state.md`](docs/project/11-current-state.md); pendientes abiertos: [`docs/project/10-technical-debt.md`](docs/project/10-technical-debt.md).

## 2026-11-26 · Canal de WhatsApp automático (pendiente de activar)

- **En `develop`**: publicación automática en el Canal de WhatsApp ([ADR-024](docs/adr/ADR-024-publicacion-canal-whatsapp.md), guía [`WHATSAPP.md`](docs/guides/WHATSAPP.md)). Copiar a mano imagen y texto desde el canal Admin era lento; WhatsApp no tiene API oficial para Canales.
- **Pasarela** `whatsapp-gateway/` (contenedor `buenchollo-whatsapp`, Node 22 + Baileys 7.0.0-rc14 fijada): se vincula a la cuenta del Canal como dispositivo, sin navegador ni puerto publicado; `/status`, `/channel` y `/send` con token. Sube las imágenes por la ruta propia de Canales (Baileys aún no lo hace bien, issue #2199).
- **Módulo `whatsapp`** en la API: suscriptor de `DealPostPublished` → cola `whatsapp_posts` (migración `20261126120000`) → job `publish_whatsapp_queue` cada minuto con ritmo de persona (≥ 20 min entre publicaciones, ≤ 15 al día, margen aleatorio). Avisos al canal Admin si se desvincula, si falla o si no confirma. El panel pasa a la cola la versión WhatsApp editada a mano.
- **Para activarlo**: variables `WHATSAPP_*` en el `.env` del NAS, levantar la pasarela, recrear API y scheduler y escanear el QR (`whatsapp-gateway/data/qr.png`). Pasos en la guía.

## 2026-11-24 · «Top de la semana» solo con chollos nuevos

- **En `main`** (PR #117, merge `e1e9ae6`). `published_at` se renueva al reactivar un chollo antiguo (revisión nocturna, alta del mismo producto, programada), así que el lateral «Top de la semana» y el resumen de los domingos colaban chollos de hace meses. Nueva columna `deals.first_published_at` (migración `20261124150000`): la rellena un trigger al pasar a `active` y el histórico toma la fecha más antigua conocida. `get_top_discount_active_since` filtra por ella.

## 2026-11-24 · Instagram activo, bus de eventos y revisión

- **Instagram en marcha** (guía [`INSTAGRAM.md`](docs/guides/INSTAGRAM.md), sección «Puesta en marcha»): app de Meta «BuenCholloTech Publicador», porfolio empresarial «Buenchollotech», @buenchollotech evaluadora y en el porfolio, y usuario del sistema `bct-publicador` cuyo token (sin caducidad) está en el `.env` del NAS. Primer post: OBSBOT Tiny 3.
- **Token de usuario del sistema** (PR #114): Meta ya no da el inicio de sesión de Instagram a apps nuevas; con tokens `EAA…` el cliente usa `graph.facebook.com`, sin renovación, y `INSTAGRAM_USER_ID` fija la cuenta.
- **`INSTAGRAM_CHANNELS`** (PR #115): las programadas salen en el canal Admin, no en el principal; en producción cuentan los dos (`main,admin`).
- **Revisión de código** ([ADR-023](docs/adr/ADR-023-bus-de-eventos-entre-modulos.md)): bus de eventos en `app/core/events.py` y raíz de composición en `app/core/bootstrap.py`. Telegram (panel y worker) emite `DealPostPublished` y no conoce a Instagram; Instagram avisa con `AdminAlert` y no importa nada de Telegram. Un post fallido ya no guarda su JPEG. `/notify` deja de devolver `instagram_queued`. Deuda nueva: TD-65 a TD-67.

## 2026-11-24 · Instagram automático y collage semanal en 3:2

- **En `main`** (PR #113, merge `dcb2919`). Migraciones `20261124120000` y `20261124130000`.
- **Instagram** ([ADR-022](docs/adr/ADR-022-publicacion-instagram.md), guía [`INSTAGRAM.md`](docs/guides/INSTAGRAM.md)): los chollos del canal principal de Telegram se publican también en el feed (misma tarjeta, texto sin enlaces con «enlace en la bio» y hashtags). Cola en BD (`instagram_posts`) y job del scheduler cada 2 min; la imagen la sirve la propia API mientras está pendiente; reintentos, aviso al canal Admin y renovación semanal del token. Apagado hasta configurar el token (`INSTAGRAM_ENABLED`). Migraciones `20261124120000` y `20261124130000`.
- **Medición**: `/instagram` redirige a la portada con `utm_source=instagram` (enlace de la bio) y la analítica tiene la fuente «Instagram».
- **Collage del resumen semanal**: 1200 × 800, el mismo formato que la tarjeta de cada chollo, para que todo el canal tenga el mismo ancho (5 columnas × 2 filas de tarjetas verticales).

## 2026-11-23 · Posts sin líneas de precio (van en la tarjeta)

- **En `main`** (PR #112, merge `63bbfae`). Sin migraciones.
- El texto de los posts deja de repetir «💶 Precio …» y «💰 Ahorro …», que ya muestra la tarjeta de oferta: la plantilla no las escribe si habrá tarjeta, y al enviar se quitan con tarjeta o se añaden si al final sale la foto original (ningún post sin precio). Republicar un texto sin precio solo corrige la fecha de fin. Limpieza de los textos de los chollos programados pendientes en la BD.
- Ajustes de la tarjeta: logo de la tienda más grande (hasta 260 × 56) y precio anterior legible (números más oscuros y raya roja fina semitransparente).

## 2026-11-23 · Tarjeta de oferta «Simple claro» en todas las publicaciones

- **Desplegado** (PR #111, merge `dac0931`): web y API; API y scheduler reiniciados en el NAS. Sin migraciones (Alembic `20261122120000`).
- **Imagen de cada chollo en Telegram** ([ADR-021](docs/adr/ADR-021-tarjeta-oferta-telegram.md), guía [`TELEGRAM-TARJETA-OFERTA.md`](docs/guides/TELEGRAM-TARJETA-OFERTA.md)): tarjeta 1200 × 800 generada con Pillow según el diseño de `_handoff/plantilla-telegram-oferta/` (foto, insignia de descuento, logo de la tienda, precio, anterior tachado, «Ahorras X €» y logo del canal). Cuadra con las referencias (~1 % de píxeles distintos). Ajustes pedidos: logo del canal a 340 px, ahorro más grande y logo de tienda en la pastilla (Amazon y Coolmod en `app/assets/images/stores/`).
- **Un punto único** (`deal_photo.py`) para todos los envíos: panel, programadas, republicación al canal Admin y copia de WhatsApp. El panel envía precio, descuento y tienda; si no, los del chollo guardado.
- **Nunca bloquea**: sin precio anterior, foto ilegible, fallo de composición o rechazo de Telegram → foto original. `DEAL_CARD_ENABLED=false` la apaga.
- **Revisión independiente** y correcciones: una conexión caída ya no da un post por publicado; un «antes» vacío en el panel no se completa con el del chollo; la insignia lleva el mismo % que el texto; la copia de WhatsApp no se duplica; cookies solo en el mismo host; claves de tienda sin acentos.
- **Descargador de imágenes**: conserva cookies entre redirecciones del mismo host (las fotos de Coolmod no bajaban).
- ⚠️ **Tiendas nuevas**: logo, color e icono del enlace antes del primer chollo (lista en la guía y en el runbook de afiliación).

## 2026-11-23 · Collage del resumen semanal más ancho

- **Desplegado** (PR #110, merge `ce22e74`).
- El resumen del domingo 22 salió en el chat del móvil con la imagen recortada arriba (cabecera) y abajo (fila 9-10): Telegram recorta la vertical 5:6 (1080×1296) cuando la publicación lleva pie de foto. Pasa a 1280×1152 (10:9, algo más ancha que alta), con el mismo diseño (`weekly_collage.py`).

## 2026-11-22 · Revisión independiente de los cambios del día y dos arreglos

- **Aviso del post**: lo decide el servidor. `/telegram/generate` recibe `affiliate_program_id` y lee el aviso de la BD; el `notice` que mande el navegador se ignora. Un post de Coolmod salió con el aviso ya retirado porque el panel llevaba abierto desde antes del cambio.
- **IA del autocompletado de redes**: si cae, ya no se aplican sus textos de rescate (título recortado y «Varios»). La API responde `copy_ok: false`; el panel solo resume la descripción del catálogo y no pone categoría. Si la llamada caduca (ahora 60 s) o falla, también resume. La respuesta se descarta si el formulario ya es otro chollo.
- **Revisión independiente** (PR #104 a #107) y correcciones:
  - `downgrade` de la migración del aviso sin vuelta atrás: rellenaba programas que nunca lo tuvieron.
  - Rollback si falla la lectura de la tienda en `/notify`, para que el registro de la publicación no se pierda.
  - Datos de la tienda delimitados en el prompt (inyección de instrucciones).
  - El resumen nunca pasa de 500 caracteres.
  - Una frase de esta bitácora que no cuadraba con el código.

## 2026-11-22 · Iconos premium de tiendas y WhatsApp registrados

- **En uso en el enlace de compra (🛒)**: Xiaomi, AliExpress y Steam, además de Amazon y el genérico.
- **Guardados para más adelante** (TD-64): Samsung, cuyo logo son dos emojis y el 🛒 es uno solo, y WhatsApp, para enlazar el Canal desde los posts.
- Registro completo de `custom_emoji_id` en [`docs/guides/TELEGRAM-EMOJIS.md`](docs/guides/TELEGRAM-EMOJIS.md).

## 2026-11-22 · Icono del enlace de compra según la tienda

- El 🛒 de los posts de Telegram era siempre el emoji premium de Amazon, también en Coolmod. Ahora `link_icon_for` (`post_generator.py`) elige por la tienda del chollo (publicación desde el panel con `deal_id`; el enlace de Awin no dice la tienda) o, si no se conoce, por el dominio del enlace de cada línea: Amazon conserva su logo y el resto usa el genérico (`5271604874419647061`) hasta tener icono propio en `STORE_LINK_ICONS`. En el resumen semanal cada línea se decide por el dominio de su enlace (Amazon, AliExpress y Steam con su logo; el resto, el genérico). Proceso para añadir iconos: [`docs/guides/TELEGRAM-EMOJIS.md`](docs/guides/TELEGRAM-EMOJIS.md).

## 2026-11-22 · Posts de redes sin aviso genérico y catálogo de Coolmod más limpio

- **Aviso de afiliación**: el post de Telegram de los chollos de Awin/Tradedoubler añadía «Enlace de afiliado: podemos recibir una comisión…», sembrado por defecto en todos los programas. La migración `20261122120000` lo vacía donde seguía el texto sembrado; el campo «Aviso adicional del programa» queda para la tienda que exija un texto propio.
- **Términos partidos del feed**: Coolmod entrega «PC Ie», «NV Me», «5600M Hz», «AS Rock», «G.S Kill», «H GiG»… (comprobado en el CSV original). `fix_split_terms` los recompone al leer el feed; la sincronización siguiente corrige el catálogo.
- **Descripción al importar**: si la IA no responde, la descripción larga es un resumen por frases (500 caracteres) en lugar de la ficha completa de la tienda. Con IA, se mantiene el resumen en viñetas (probado en producción con el Samsung M70H).
- **Enlace afiliado verificado**: `tidd.ly` (Link Builder de Awin) → `awin1.com` con el programa 124624 y nuestro ID de publisher → ficha exacta en coolmod.com con `awc` (atribución).

## 2026-11-21 · Coolmod activo en Awin y textos con IA para las redes

- **Coolmod (Awin) en marcha**: adhesión `joined`, programa habilitado (web y Telegram), feed «Predeterminado» (12.995 productos) sincronizado y contrastado con un producto real. Primera validación en vivo del parser de Awin (TD-46). Samsung ES también aceptado (sin habilitar); Fnac rechazado.
- **Autocompletar de Awin / Tradedoubler con IA**: tras importar del catálogo, el editor pide a `POST /v1/products/enrich` (solo admin, 10/min) la descripción corta, la larga, el post de Telegram y la categoría, con el mismo enriquecedor que Amazon (`EnrichProductUseCase`). No pisa lo escrito a mano. El precio anterior sigue siendo manual: el feed no trae una referencia válida.
- **Runbook**: la sincronización de feeds solo descubre los de programas habilitados (habilitar antes).

## 2026-11-21 · Ficha del chollo sin desplazamiento lateral en el móvil

- **Causa**: la rejilla móvil de la ficha (`.product-layout`, `src/styles.css`) usaba `grid-template-columns: 1fr`, que equivale a `minmax(auto, 1fr)`: la columna crecía hasta el ancho intrínseco de la galería (carrusel de miniaturas) y la página se desplazaba de lado. A 360 px la página medía 436 px para 345 px útiles; se cortaban el aviso «Termina» y el borde de la galería.
- **Corrección**: `minmax(0, 1fr)`, que limita la columna al ancho disponible. La cabecera de «Chollos relacionados» puede saltar de línea para que un nombre de categoría largo («VER MÁS DE …») no desborde.
- **Verificado** con la ficha real a 360, 390 y 414 px (ancho de página igual al de la pantalla) y en escritorio (2 columnas, sin cambios). Queda abierto el desborde de la cabecera a 320 px con sesión iniciada (TD-63).

## 2026-11-21 · Preguntas frecuentes en su página y ficha compacta en el móvil

- **Preguntas frecuentes**: fuera de la portada (quedaban mal al final del feed) y a `/preguntas-frecuentes`, enlazada en el pie (INFO), en el sitemap y en `/llms.txt`, con 6 preguntas nuevas: el resumen de la semana, las novedades desde la última visita, qué significa el descuento, cambios de precio, dónde se compra y el canal de WhatsApp. El `FAQPage` va con ellas; la portada ya no lo publica. «Sobre nosotros» enlaza a la página en lugar de repetirlas.
- **Ficha del chollo en el móvil**: los bloques de arriba estaban muy separados porque las utilidades de Tailwind (`gap-8`, `mb-3`…) sumaban huecos al «aplanar» el resumen. Ahora una regla fuera de las capas marca el espaciado: título, precio, tienda, fin de oferta y botón van juntos.

## 2026-11-21 · Más populares fuera, títulos limpios, novedades y resumen semanal

- **«Más populares» fuera** de la portada, el menú y `/explorar`: ordenaba por votos y, con todo a 0, mostraba chollos sin criterio. Un `?sort=popular` antiguo funciona como «más recientes».
- **Títulos**: normalización al publicar y editar (`deals/domain/titles.py`), conservadora con modelos, siglas y marcas, y probada con los 354 títulos reales. Limpieza de los ya publicados con `scripts/normalize_titles.py` (simula por defecto; `--apply` escribe y genera un informe antes/después). Los slugs no cambian.
- **Novedades desde tu última visita**: contador «N nuevos» junto a «Inicio» y separador en la portada, sin cuenta (`localStorage`). Endpoint `GET /v1/deals/new-count`.
- **«Los chollos de la semana»**: domingos a las 22:30 al canal Admin (Telegram + WhatsApp), top 10 por descuento de los activos de la semana. Vista previa y envío manual para admins en `/v1/telegram/weekly-digest`. `WEEKLY_DIGEST_ENABLED` (true por defecto).
- **«Top de la semana» en la portada**: el lateral muestra en vivo el mismo ranking que el resumen del domingo (10 activos con más descuento de la semana, con número, foto, precio, descuento y etiqueta «Nuevo» si es de las últimas 24 h). `GET /v1/deals/weekly-top`.
- **Collage del resumen**: una imagen vertical 1080×1296 (5:6: Telegram recorta en el chat las más altas que ~3:4) con el número, la foto, el precio y el descuento de cada chollo en grande (los títulos van en el texto, cada uno con su número en emoji 1️⃣–🔟). Va en el mismo mensaje que el texto, como pie de foto, igual que los chollos: el texto se recorta hasta caber en los 1024 caracteres de Telegram (primero se acortan los títulos para conservar el precio anterior, en el formato «34,99 € | -73 % | antes: 129,99 €»; los enlaces siempre enteros). La versión WhatsApp lleva el texto completo. La genera Pillow con la tipografía de la web (Space Grotesk, OFL, en `buenchollo-api/app/assets/fonts`). Si falla, el texto sale igual. Vista previa para admins en `GET /v1/telegram/weekly-digest/image`.
- Revisión de código antes del merge: visita mantenida al navegar, reglas de afiliación en el resumen, semana alineada entre etiqueta y consulta, siglas con guion y marcas en los títulos, y el contador visible en el móvil.

## 2026-11-21 · Rótulo de neón del Black Friday

- **Desplegado** (PR #91, que incluye la #92; merge `3fe1ee2`, 2026-11-21 00:04): CI de `main` en verde y Workers Builds en verde; solo cambia la web (Cloudflare Worker), sin tocar el NAS. Verificado: la portada y `/black-friday` sirven el rótulo (`neon-sign`) y `/black-friday` da 200.
- **Qué es**: el hero plano de campaña pasa a ser un rótulo de neón de escaparate sobre pared de ladrillo, siempre oscuro (también en tema claro). «BLACK FRIDAY» en tubo magenta con encendido parpadeante al cargar y zumbido ocasional; cuenta atrás en tubos cian (días, horas, min y seg, los segundos en magenta) y CTA de neón. Respeta `prefers-reduced-motion`.
- **Dónde**: portada (`h2`, enlace a la landing) y cabecera de `/black-friday` (`h1`, CTA de Telegram), ambos con `CampaignHero` (`src/features/campaigns/`), que acepta `headingLevel` y `cta`. Estilos `.neon-sign*` en `src/styles.css`.
- **Cuenta atrás**: `CampaignCountdown` avanza cada segundo (antes cada 30 s) con `role="timer"` y el texto accesible de `formatCountdown`. En el servidor pinta guiones con la misma caja: sin saltos de diseño ni desajuste de hidratación. `countdownTo` (`src/lib/campaigns.ts`) devuelve también `seconds`.
- **Dependencia nueva**: `@fontsource/monoton` 5.3.0 (fuente Monoton alojada en la propia web, solo el subconjunto latino, ~16 KB).
- **Más compacto** (`83bc07d`, PR #94): pasa de unos 450 px de alto a unos 200 px; «BLACK FRIDAY» en una línea y tubos de la cuenta atrás más pequeños.
- **Tests**: `campaigns.test.ts` cubre los segundos en `countdownTo`; tests, `tsc` y ESLint en verde; revisado en local en escritorio.

## 2026-11-20 · Versión WhatsApp de las publicaciones y fuente `whatsapp` en la analítica

- WhatsApp no tiene API oficial para publicar en Canales: la publicación es semiautomática, sin riesgo de baneo. **Cada publicación de Telegram genera dos envíos**: el post de Telegram y, a continuación, su versión WhatsApp al **canal Admin** (nunca al público), en texto plano y con la misma imagen, lista para copiarla al Canal de WhatsApp desde el móvil. Aplica al panel (chollos y propuestas), a las publicaciones programadas y a la republicación de los avisos de bajada. Si el segundo envío falla, la publicación de Telegram no se ve afectada.
- Plantilla WhatsApp (`telegram/application/whatsapp_formatter.py`): emojis estándar en lugar de los premium animados (🍄→🔥, 💶→🏷️, 💰→💸, 🛒→👉, ✏️→📝, ⚠️→⏰, 🔗→🌐), negritas `*...*` en título, precio y ahorro, sin hashtags y enlace visible a `https://buenchollotech.com/whatsapp`. Envío: `whatsapp_copy.send_whatsapp_copy` (si la foto falla reintenta solo con texto).
- API: `POST /v1/telegram/generate` devuelve `whatsapp_text`; `POST /v1/telegram/whatsapp-text` convierte el texto editado; `POST /v1/telegram/notify` acepta `whatsapp_text` (la versión editada en el panel) y responde `whatsapp_sent`.
- Web: botón «WhatsApp» con su logo junto a «Telegram» en la barra de navegación (que pierde la flecha) y «Canal de WhatsApp» en el menú lateral; enlace en `WHATSAPP_URL` (`src/lib/site.ts`).
- Panel: bloque «Versión WhatsApp» sincronizado con el texto de Telegram (deja de sincronizarse si se edita a mano), botones Copiar y Compartir (hoja de compartir del móvil con imagen y texto; si no, `wa.me`).
- Analítica: ruta `/whatsapp` → `/?utm_source=whatsapp&utm_medium=social&utm_campaign=canal`, nueva fuente `whatsapp` (también referentes `wa.me`/`whatsapp.com`) y fila propia en el panel de analítica. Alembic `20261120130000` (CHECK de `analytics_events.source`).

## 2026-11-20 · Retención: tarjetas limpias, Black Friday e histórico de precios

- **Desplegado** (PR #88, que incluye la #89; merge `e735ab5`): CI en verde (12/12), backup previo con `db-backup` (`bct-prod-20261120T223044Z.dump`, 1,7 MB, 72 tablas con datos), share en `main` por fast-forward y `docker restart buenchollo-api buenchollo-scheduler`, sin rebuild porque no cambian dependencias. Alembic aplicó `20261120120000` (`price_history`) y `20261120130000` (fuente `whatsapp`). Verificado: `/health` y `/health/ready` dan 200, la semilla cargó 354 puntos (uno por listing con precio), `GET /v1/catalog/products/{id}/price-history` responde, y la portada muestra el hero de Black Friday sin pestañas ni votos en las tarjetas. `/black-friday` da 200 y aparece en el sitemap.
- **Contexto**: un informe de retención detectó el efecto «web vacía» (todas las tarjetas con 0°, 0 comentarios y «Votar producto» sin votos), ninguna página para el Black Friday (27-nov) y ningún dato de precio propio.
- **Tarjetas**: sin temperatura, voto de producto ni comentarios; se mantienen en la ficha. Se elimina `useMyVotes` (una petición menos por listado). El CTA unificado es «Ir a la oferta».
- **Portada**: sin pestañas «Más populares / Nuevos / Mayor descuento» («popular» ordenaba por temperatura, con todo a 0); siempre los más nuevos. Un `?sort=` antiguo se ignora.
- **Black Friday**: landing `/black-friday` (≥ 20 % de descuento, cuenta atrás, Telegram, FAQ y JSON-LD, en el sitemap) y hero de campaña en portada hasta el final del Cyber Monday (30-nov). La fase se calcula con la hora del loader para que el servidor y el cliente coincidan.
- **Histórico de precios** ([ADR-020](docs/adr/ADR-020-historico-de-precios.md)): tabla `price_history` (Alembic `20261120120000`, aditiva y con semilla desde `product_listings`). La alimentan la revisión diaria (solo precios con stock) y las altas y ediciones de chollos de cualquier tienda. Endpoint `GET /v1/catalog/products/{id}/price-history`. Riesgo asumido por Pedro: la licencia de Amazon Afiliados limita guardar sus precios a 24 h.
- **Revisión de código** antes del merge: corregidos el falso mínimo por edición manual, los puntos con la tienda equivocada tras cambiar un chollo de tienda, los precios sin stock, la lógica en el router, la carga del histórico completo por petición, el upsert fila a fila del job, el desajuste de hidratación del hero, el texto «más de» frente a «al menos» y el código duplicado o sin uso.

## 2026-11-18 · SEO, documentación y correcciones de la auditoría

- **SEO y búsqueda con IA** (PR #85, desplegado y verificado en producción): 404 reales, módulo `src/lib/seo` con cabeceras y datos estructurados en todas las páginas, categorías con texto propio y fuera del índice si están vacías, paginación rastreable, sitemap con imágenes, `/llms.txt` dinámico, feed RSS de chollos, `robots.txt` con bots de IA, página «Sobre nosotros», logo de 588 KB a 7 KB y fuentes propias. Informe: [`docs/project/13-seo.md`](docs/project/13-seo.md).
- **Documentación**: eliminados `docs/archive`, `docs/superpowers`, `docs/reference` y notas de cambios (≈ 10 800 líneas), `PROJECT_STATUS.md` condensado, índices y enlaces verificados, y datos operativos y personales retirados del repositorio público (IP, usuario y clave del NAS, rutas, correos).
- **Auditoría**: corregidos AUD-01, 06, 07, 08, 09, 13, 14, 15, 16, 20, 21, 24, 25 y 26, más los bajos de seguridad, el código muerto y el scheduler (hora de Madrid; antes UTC, así que el resumen de alertas pasa a salir a las 21:00 españolas y la revisión de precios a la hora configurada en hora española); parciales AUD-02, 03, 04, 10, 17, 18 y 22. Estado por hallazgo en el § 9 del informe; pendientes en TD-52 a TD-62.
- **Operación nueva**: servicio `db-backup` (copia diaria validada), monitor de disponibilidad en GitHub Actions y protección de rama en `main`.

## 2026-11-18 · Auditoría técnica completa (enfoque comprador)

- Revisión de arquitectura backend y frontend, seguridad, calidad de código, testing, CI y operación, con verificación de todos los hallazgos altos contra el código y, en solo lectura, contra producción. Informe: [`docs/project/12-auditoria-tecnica-2026-11.md`](docs/project/12-auditoria-tecnica-2026-11.md).
- Métricas: backend 83 % de cobertura (812 unitarios + 59 de integración), frontend 38 % (492 tests), `pip-audit` y `npm audit` limpios (salvo TD-50), una sola cabeza de Alembic, bundle inicial de 776 kB.
- Veredicto: código sólido (arquitectura y seguridad altas); operación débil. Ocho hallazgos de prioridad alta: registro de modelos de Alembic sin seis tablas (AUD-01), despliegue sobre la copia de trabajo (AUD-02, TD-31), backups manuales (AUD-03), sin alertas de caída (AUD-04), token del túnel (AUD-05, TD-21), `main` sin protección de rama (AUD-06), *soft 404* en producción (AUD-07) y logo de 588 KB (AUD-08).

## 2026-11-18 · Aviso de bajadas al canal Admin solo para chollos de hace 10 días o más

- La revisión diaria seguía avisando de bajadas de chollos publicados hace 4 días, lo que llevaba a repetir contenido reciente en Telegram. Ahora `ReactivationNotifier` solo avisa al canal Admin si el chollo se publicó hace al menos 10 días (`REPOST_MIN_AGE`): cuenta la última publicación registrada en Telegram o, si no la hay, el alta en la web (`created_at`). El aviso incluye la línea «🗓️ Última publicación en Telegram: dd/mm/aaaa (hace N días)». Se mantiene el antispam de 7 días; las alertas de usuario y la actualización del precio en la web no cambian. Un chollo caducado que vuelve a estar en oferta ya pasaba a `active` (sin cambios). Ver ADR-017 § 4.
- **Corrección (PR #84): la última publicación cuenta en cualquier canal.** En producción las 119 publicaciones registradas son del canal Admin (se publica allí y se reenvía al oficial), pero el aviso de bajadas, el bloque «Último envío» de «Editar chollo» y el panel de Telegram solo buscaban envíos a canales públicos, así que nunca encontraban ninguno: el aviso usaba siempre el alta en la web y regeneraba la publicación. Ahora `TelegramPublicationRepository.latest_for_deal` y `telegramApi.latestPublication` toman el último envío de cualquier canal (los avisos de la revisión de precios no se registran). Ejemplo: el AOC Q27G42XE se dio de alta el 10/11 y se publicó por programación el 16/11; ahora cuenta el 16/11.

## 2026-11-18 · Borrador de Telegram en «Editar chollo», chollos antiguos y borrado desde la ficha

- **Desplegado** (PR #79, #80 y #81; merge final `325573f`): backup previo `pg_dump -Fc` validado con `pg_restore -l` (`~/backups/buenchollo/bct-prod-pre-telegram-draft-20261118T094553Z.dump`, 1,7 MB, 72 tablas con datos; SHA-256 `1d7ecc39…a7fd71fa7d0b8`), share en `main` por fast-forward y `docker restart buenchollo-api buenchollo-scheduler` (sin rebuild: sin dependencias nuevas). Alembic aplicó `20261118120000`. CI de las tres PR en verde (6/6).
- **Pruebas en producción**: `/health`, `/health/ready`, sitemap, portada y ficha 200; los endpoints admin nuevos sin sesión 401; el detalle público no expone `telegram_text`; los bundles publicados contienen la sección nueva y el botón ELIMINAR. Dentro del contenedor de producción (solo lectura): la DJI Osmo Pocket 3, fuera de los 200 más recientes de 271 chollos, se carga por id con `DealAdminResponse`; el copy con IA sale completo con Automático y OpenAI (~1–12 s, 227–350 caracteres).
- **Hallazgos de las pruebas, corregidos en #80/#81**: con `max_tokens=300` los modelos gratuitos que razonan devolvían la frase cortada, y sin `max_tokens` OmniRoute rechaza las peticiones de texto (400). Queda `COPY_MAX_TOKENS = 2000`. El motor «OmniRoute» solo con modelos gratuitos suele agotar su límite de 3,5 s por modelo al escribir el copy; el botón avisa y usa la descripción corta (TD-51). Para este botón, usar «Automático».

- **Contexto**: la revisión diaria de precios avisaba de bajadas de chollos que luego no se podían abrir en Admin → Chollos. Causas: el formulario se pinta encima de la tabla sin hacer scroll (desde una fila de abajo parecía que EDITAR no hacía nada) y `?edit=<id>` buscaba el chollo en el listado, que solo trae los 200 más recientes.
- **Editar**: `GET /v1/deals/admin/{id}` carga cualquier chollo por id, y el formulario se lleva a la vista al abrirlo. El conflicto de importación de Awin/Tradedoubler también abre el chollo existente por id.
- **Publicación Telegram en Editar chollo** (`DealTelegramDraftSection`): muestra el último envío registrado (con opción de reutilizarlo con el precio actual) y genera un borrador con el motor de IA elegido (`AiProviderSelect`, compartido con el autocompletado). El borrador se guarda en `deals.telegram_text` (migración aditiva `20261118120000`), que solo devuelven los endpoints admin (`DealAdminResponse`). «Publicar en Telegram» abre el panel con ese texto sin regenerarlo. `POST /v1/telegram/generate` acepta `ai_copy`, `provider` y `copy_context`: la IA reescribe solo la línea ✏️ (`TelegramPostGenerator.generate_copy`, 60 s máximo, con la descripción si falla) y la plantilla pone precio, ahorro, enlace y fecha de fin. Reglas del copy en un único sitio (`TELEGRAM_COPY_RULES`). Las programaciones copian su texto al chollo.
- **Ficha pública del chollo**: botón ELIMINAR para admins, con confirmación (mismo `DELETE /v1/deals/admin/{id}`; las FK borran en cascada votos, comentarios, favoritos, notificaciones, programaciones y publicaciones, y la propuesta de usuario queda desvinculada).
- **Documentación**: el proyecto deja de presentarse como Trabajo Fin de Máster. Eliminados `docs/master/` y `presentacion/`, y limpiadas las referencias en README, ADRs, `docs/project`, agentes y memoria. El workflow `documentar-decision-tecnica-pfmaster.md` pasa a `documentar-decision-tecnica.md`. Corregidos los enlaces relativos rotos de `docs/archive/`.
- **CI (auditoría de dependencias)**: el job de seguridad empezó a fallar por un aviso high nuevo de `picomatch` (GHSA-fc5q-39xc-vjpf) sin versión corregida, que llega solo por herramientas de build. `npm run audit:prod` (`buenchollo-web/scripts/audit-prod.mjs`) sustituye a `npm audit --omit=dev --audit-level=high`: sigue fallando con cualquier high/critical, salvo los aceptados en `audit-allowlist.json` con motivo y fecha de revisión, y falla también si una excepción vence. TD-50.

## 2026-11-08 · Awin y Tradedoubler en el editor de chollos (en producción, sin tiendas aprobadas)

- **Desplegado** (PR #78, merge `c47269c`): API y scheduler recreados, Alembic `20261108120000`, job `run_awin_feed_sync` activo. Credenciales de las dos redes en el `.env` del NAS. Todas las tiendas siguen `pending` (Awin) o sin feeds (Tradedoubler) y deshabilitadas. Para activarlas cuando aprueben: `docs/guides/AFFILIATE-ACTIVATION-RUNBOOK.md` (incluye `scripts/check_affiliate_status.py`, comprobación de solo lectura que se ejecuta en el contenedor de producción).

- Pegar una URL de una tienda de Awin/Tradedoubler en Admin → Chollos detecta tienda y programa, comprueba configuración y adhesión, busca el producto en una fuente autorizada (catálogo local de feeds Awin / Products API de Tradedoubler), obtiene el enlace afiliado oficial y rellena el editor como **borrador**, con procedencia, antigüedad, campos pendientes, candidatos y conflictos con lo editado a mano. «SOLO ENLACE» genera solo el enlace. Nada se publica al pegar. Nueva pantalla Admin → Afiliación (registro de programas, feeds, adhesión). Publicar exige precio anterior con evidencia (un PVP no vale), envío, imagen autorizada, programa `joined` y dato fresco (`PublicationGuard`, también en Telegram). Amazon sin cambios. ADR-019, guía `docs/guides/AFFILIATE-NETWORKS.md`.
- Migración `20261108120000` (aditiva: `affiliate_programs`, `affiliate_feed_products`, columnas de procedencia en `deals`; programas sembrados sin verificar y deshabilitados). Sin dependencias nuevas. Job diario `sync_awin_feeds` en el scheduler (no hace nada sin credenciales).
- Verificado: 788 tests unitarios + 59 de integración (Postgres local), migración arriba/abajo sobre el esquema real copiado, smoke en vivo contra la API local (estados reales sin credenciales, bloqueo de publicación, SSRF, Amazon Creators API real), 484 Vitest, TypeScript, ESLint, build SSR y E2E (5, móvil y escritorio). **Sin validar en vivo con Awin/Tradedoubler**: faltan credenciales y aprobaciones (TD-46).

## 2026-11-08 · Revisión de afiliación previa a producción

Awin y Tradedoubler revisados con regresiones para campos opcionales de API, envío cero, selección de feeds, hosts de seguimiento, importación deshabilitada, NaN y esquema CSV incompatible. Token de ambas redes validado; sin feeds de las tiendas objetivo accesibles. Se conserva el bloqueo por adhesión y los programas deshabilitados. Pendientes: TD-46 a TD-49 y validación real por tienda. Detalle y hallazgos: [`docs/guides/AFFILIATE-NETWORKS.md`](docs/guides/AFFILIATE-NETWORKS.md). Frontend: 484 Vitest, 37 E2E, typecheck/lint y build; integración PostgreSQL con esquema ORM: 59 correctos.

## 2026-11-08 · Tarjetas de chollo con la distribución de un listado de chollos

- Petición de Pedro (referencia: tarjetas de Chollómetro): las tarjetas se veían vacías. Nuevo orden en `DealCardView`: arriba votos del chollo y «Votar producto» con «Publicado hace X» a la derecha; título; línea de precio actual, anterior tachado y descuento en verde muy visible (`.deal-discount`, claro y oscuro), seguido de «Disponible en <tienda>» y «Compartido por <usuario>» si lo ha propuesto la comunidad; descripción en dos líneas; abajo comentarios, compartir y guardar a la izquierda e «Ir al chollo» a la derecha. El descuento sale de la foto (ya no se repite). En móvil (feed) la fila de votos y la de acciones ocupan todo el ancho y la foto queda junto a título y precio; separadores verticales solo en la tarjeta horizontal desde 900 px. Sin cambios de API.
- Verificado con Playwright en 320/375/390/640/1280 px y ambos temas (sin elementos fuera de la tarjeta ni scroll horizontal), tarjeta vertical a 290 px y tarjeta con autor. 475 Vitest, TypeScript, ESLint sin errores y build SSR.

## 2026-11-07 · Incidente: el autocompletado de Amazon no encontraba productos

- Tras desplegar la revisión general, el panel respondía «No se ha encontrado el producto de Amazon» con enlaces `link.amazon`. Causa: la nueva validación de cada salto de redirección (SSRF) no conocía `amzlinks.in`, el salto intermedio real de `link.amazon` (`link.amazon/<id>` → `amzlinks.in/<id>` → `www.amazon.es/dp/...`). Antes solo se validaba la URL final. Corregido añadiendo `amzlinks.in` a `_ALLOWED_HOSTS`, con test de regresión de la cadena real; comprobado contra el enlace real (resuelve `B0H7X5D6QN`). Lección: al endurecer una integración externa, probar con enlaces reales antes de desplegar, no solo con mocks.

## 2026-11-07 · Fotos cuadradas en las tarjetas de chollos

- Petición de Pedro: en la tarjeta horizontal (portada, categorías y explorar) la foto era una tira estrecha estirada a toda la altura. Ahora es un cuadrado blanco con esquinas redondeadas y borde suave, centrado en su columna: 114 px en móvil y 198 px desde 640 px (`.deal-feed-grid .deal-card > .deal-card-media` en `styles.css`, sin cambios de componente). Ajuste posterior: la regla `.deal-card > a:first-child { margin-bottom: 0 }` era más específica y anulaba el margen inferior, así que la foto quedaba ~13 px más baja; ahora el margen es igual arriba y abajo en todos los anchos. Verificado con Playwright en 320/375/390/640/1024/1280 px y ambos temas: imagen 1:1, dentro de la tarjeta y sin scroll horizontal.

## 2026-11-07 · Revisión general: seguridad, correcciones y coherencia (desplegado)

- **Seguridad.** (1) `POST /v1/products/preview-from-url` exige `require_admin` (cierra **TD-23**): era anónimo y cada llamada gastaba cupo de Amazon Creators y del motor de IA; solo lo usa el panel. (2) La resolución de acortadores de Amazon validaba la URL final, pero `urlopen` ya había seguido las redirecciones por su cuenta: ahora se valida host y destino **en cada salto** (`_AllowlistRedirectHandler`). (3) Las excepciones de `requests` contra la Bot API incluyen `…/bot<TOKEN>/…` y llegaban a logs, Sentry y `last_error` (visible en el panel) vía `logger.exception`/`raise_for_status`: `TelegramBot._redact` sustituye el token. (4) La pre-descarga de imágenes para Telegram no tenía control de destino ni de tamaño: ahora solo `http(s)` a IP pública, redirecciones revalidadas (máx. 3) y corte a 10 MB. (5) La validación remota del JWT (`supabase.auth.get_user`, síncrona) se ejecuta en un hilo y no bloquea el event loop.
- **Bug: el resumen nocturno de alertas por correo nunca funcionaba** (cierra **TD-26**, peor de lo documentado). La consulta usaba `Deal.is_active` (no existe) y fallaba antes de empezar; además leía `deal.price`/`original_price`/`discount`/`asin`, `branding.base_url` (es `site_url`) y hacía lazy-load de `deal.store` en async. Reescrito con los campos reales, `selectinload`, chollos `active` publicados en 24 h y el mismo `matches_alert` de las alertas in-app (antes duplicaba unas reglas incompletas: sin descripción, marca ni subcategoría). Logs solo con `user_id` (sin email). Tests con modelos ORM reales.
- **Robustez y modularidad.** **TD-19**: un fallo de cableado del worker de tareas programadas ya no se traga como «fallo global» y se propaga a APScheduler/Sentry. **TD-32** (parcial): la limpieza de la URL de Supabase vive en `Settings.supabase_base_url`. **TD-38 b**: hook `useRequireLogin` para las páginas privadas (alertas, nueva alerta, favoritos, notificaciones, perfil) y redirección del panel admin y del bloque de alertas con `?redirect=` a la página actual. Imports sin usar eliminados (ruff F401).
- **Despliegue:** PR #71 (merge `e35c950`) y #72 (`2a29d8b`, podio: números dentro del cajón, «Top <categoría>» entre las flechas, banner de ~267 a 209 px en escritorio y cabecera sin desbordamiento entre 640 y 767 px). CI de `main` verde en ambas; share en `main` por fast-forward; `docker restart buenchollo-api buenchollo-scheduler` (sin rebuild: sin dependencias ni migraciones). Tras el reinicio: `/health`, `/health/ready`, tops y sitemap 200; `preview-from-url` sin sesión 401 (antes 200); la web sirve el banner nuevo.
- **Banner de tops:** el loader de portada depende de `sort`/`page`, así que cada cambio de filtro o página repetía 7 peticiones; ahora el navegador reutiliza el resultado 60 s (el SSR sigue consultando en cada carga). Quitado un fragmento vacío del botón de pausa eliminado y el BOM de `bannerTops.ts`.
- **Verificación:** CI de `main` (PR #68–#70) en verde antes de empezar; el único fallo del día fue un fallo puntual de gitleaks ("stderr is not empty"), resuelto al relanzarlo. Tras los cambios: 707 tests backend sin integración + 58 de integración sobre PostgreSQL local (antes 689 + 58), 473 Vitest (antes 468), TypeScript, ESLint sin errores (9 avisos de shadcn, antes 10), build SSR, `npm audit --omit=dev` y `pip-audit` sin vulnerabilidades. Sin cambios de API pública (salvo el 401/403 de `preview-from-url` sin admin), base de datos ni dependencias.

## 2026-11-07 · Banner de tops comunitarios en portada (desplegado)

- Podio con productos reales de los tops por categoría, fondos de tema claro/oscuro, rotación cada 5 s con flechas y diseño compacto mobile-first. Fondo blanco completo en las imágenes de categoría. PR #68, #69 y #70; CI verde y verificado en producción. Descripción vigente en [`11-current-state.md`](docs/project/11-current-state.md).

## 2026-11-06 · Rediseño de descubrimiento y tops de productos (desplegado)

- Portada con banner de voto, feed de tarjetas horizontales y módulos laterales de chollos y blog; navegación y directorio visual de categorías renovados. Loaders SSR para portada y categorías. Diseño comprobado a 390 y 1440 px sin desbordamiento.
- ADR-018: todos los productos públicos de cada categoría/subcategoría compiten automáticamente; podio de tres y lista hasta diez. Voto positivo reversible por usuario autenticado en `product_top_votes`, migración `20261107120000`. Borradores excluidos. Tres endpoints nuevos en `/v1/catalog`.
- Voto de producto también en tarjeta y ficha de chollo, con estado compartido en el cliente. Revisión completa del lote: FK `product_top_votes.user_id → profiles` en cascada, índice redundante eliminado, lógica de voto unificada, CSS deduplicado y errores de loaders registrados.
- Validación local: 689 tests backend sin integración y 56 de integración sobre PostgreSQL 17, 463 Vitest, 33 Playwright, build SSR, TypeScript y lint sin errores. Migración aplicada únicamente a la base de `local-env`. Descripción vigente en [`11-current-state.md`](docs/project/11-current-state.md) y [ADR-018](docs/adr/ADR-018-tops-comunitarios-productos.md).
- **Despliegue:** CI de la PR verde (6/6); backup `pg_dump` validado en el NAS (`~/backups/buenchollo/bct-prod-pre-tops-20261106T173021Z.dump`); merge `477166f` en `main`; rebuild de `buenchollo-api` y `buenchollo-scheduler`; Alembic aplicó `20261107120000` (FK a `profiles` en cascada y RLS comprobados en la base). `/health`, `/health/ready`, `/v1/catalog/tops/monitores` y `/v1/deals/sitemap` responden 200; voto sin sesión 401; la web sirve el top y los chips de voto.
- **Siguiente desarrollo pendiente:** definir puntos por acciones, límites contra abuso y recompensas. Requiere diseño de producto independiente.

*Actualización de producción: 2026-11-06 — Catálogo permanente y registro de Telegram desplegados en web, API y scheduler (merge `3d9c1d9`). CI de `main` en verde; migraciones aplicadas hasta `20261106120000`.*

## 2026-11-06 · Despliegue del catálogo y Telegram en el NAS

- Con autorización de Pedro, backup previo `pg_dump -Fc` de producción realizado con cliente PostgreSQL 17 y validado con `pg_restore -l`: `<RUTA_BACKUPS>/bct-prod-pre-catalog-20261106T151117Z.dump` (1,3 MB; SHA-256 `f0ed54e242d07f860cdd713e649766f1a57cf5bf9296ad05d29c90472b75f8b4`). No se mostraron credenciales.
- Copia del share limpia en `main`, actualizada por avance rápido a `3d9c1d9`. `docker-compose build && docker-compose up -d` reconstruyó y reinició API y scheduler; el túnel volvió a arrancar. Alembic confirma `20261106120000 (head)`.
- Producción: `/health`, `/health/ready` y `/v1/deals/sitemap` responden 200; API `healthy`, scheduler y túnel activos. Backfill: 152 `products`, 152 `product_listings` y 152 `deals`; `telegram_publications` empieza en 0. `price_check` está habilitado y diario, con umbrales 5 % / 30 días / 5 %; `TELEGRAM_ENABLED=True`.
- [CI de la PR #65](https://github.com/Zambudio/buenchollo-app/actions/runs/42224606927) y [CI del merge a `main`](https://github.com/Zambudio/buenchollo-app/actions/runs/42225036896) correctas. Queda observar la primera ejecución diaria y sus posibles avisos reales al canal Admin.

## 2026-11-06 · Registro de publicaciones de Telegram y aviso con la publicación corregida (en `develop`)

- **Petición de Pedro tras ver los avisos en el canal Admin**: guardar cómo se publicó cada chollo en Telegram y, cuando vuelve a estar en oferta o baja de precio, mandar al canal Admin el aviso **y después la publicación anterior con el precio corregido**, lista para reenviar tras comprobar la oferta. La web actualiza el precio sola.
- Nueva tabla `telegram_publications` (migración `20261106120000`): texto exacto, imagen, canal, origen (`panel`/`scheduled`), `message_id` de Telegram y precios del chollo al publicar. La registran el panel (`POST /telegram/notify`, ahora con `deal_id`; si el formulario no está guardado, se asocia por ASIN) y el worker de chollos programados. `GET /v1/telegram/publications?deal_id=`; el panel muestra la última publicación y permite reutilizar su texto.
- El aviso al canal Admin son dos mensajes: «🔁 Vuelve a estar en oferta» / «📉 Ha bajado de precio» con el precio de antes y el actual, y la última publicación pública con precio, ahorro y fecha de fin corregidos (`telegram/application/reprice.py`, respeta el texto editado a mano) o una nueva si nunca se publicó. Nuevo: aviso de **bajada de precio** en ofertas activas (≥ `price_drop_percent`, 5 % por defecto; la bajada pasa a ser su precio de oferta).
- **Incidente corregido**: Telegram no estaba apagado en local ni en los tests. `bct-local` ponía `TELEGRAM_*=''` (PowerShell borra las variables vacías) y `Settings` leía el `.env` real, así que la prueba local del 05/11 y un test de integración enviaron 5 avisos reales al canal Admin (datos de la copia local; producción no estaba afectada). Nuevo interruptor `TELEGRAM_ENABLED` (false en `local-env` y `conftest.py`).
- Verificación: 677 pruebas backend unitarias, 57 de integración (esquema tipo CI) más las del catálogo y publicaciones sobre el esquema real, 454 de frontend; revisión real en local con Telegram apagado (`/telegram/channels` vacío; 20 cambios de oferta solo en el log) y vista de los dos mensajes con un bot falso sobre datos reales.

## 2026-11-06 · Catálogo permanente, Fase 1 (en `develop`, sin desplegar)

- **Los chollos ya no se borran.** Fuera el job de las 03:00 (`clean_expired_deals`) y el borrado de la revisión de precios. `price_check` pasa a **diaria y activa**: actualiza precio y stock de todo el catálogo de Amazon, termina la oferta (`expired` + motivo) si sube, se agota, deja de estar rebajada o desaparece, y la **reactiva** si vuelve (con histéresis por motivo). Al reactivar se avisa al **canal Admin** de Telegram (nunca al oficial; antispam de 7 días salvo precio menor); la web la muestra sin aprobación. Única eliminación automática: tienda sin disponibilidad confirmada durante 30 días (si el producto no tiene más tiendas, se eliminan producto y chollos). Volver a dar de alta un producto conocido reactiva su chollo de siempre. Decisión en **ADR-017**.
- Modelo: módulo `catalog` con `products` y `product_listings`; `deals` gana `product_id`, `listing_id`, `offer_end_reason`, `offer_price`, `last_price_check_at` y `admin_notified_*`. Migración `20261105120000` reversible con backfill por tienda + ASIN (local: 157 chollos → 157 productos, sin pérdida de votos). Amazon: solo precio vigente, sin histórico.
- Web: la ficha de un chollo sin oferta explica el motivo y solo da el precio actual si se comprobó en ≤ 24 h; las activas muestran cuándo se comprobó; schema.org según el motivo; el sitemap incluye los `expired`. Panel de tareas con vista previa de transiciones, sin «Restaurar» y con mínimo de descuento y días de purga.
- Hallazgos de la prueba real contra Amazon (corregidos con test): 429 por lotes sin pausa (ahora ~1 petición/s y un reintento), un `external_id` no-ASIN tumbaba su lote con un 400 (ya no se consultan), la regla de reactivación por descuento de la tienda convertía subidas en «vuelve a estar en oferta», y borrar un chollo a mano dejaba su producto huérfano. Además: `is_task_due` desplazaba una hora al día las tareas diarias y `conftest.py` (`override=True`) mandaba los tests de integración a producción aunque se exportase `DATABASE_URL` (ahora gana lo exportado).
- Revisión final independiente de toda la rama: 0 críticos, 6 importantes corregidos con test (reactivar arrastraba la fecha de fin pasada; reactivación de ofertas ya vencidas; worker y panel podían ejecutar la revisión a la vez → marca `running_since` y 409; transacción abierta durante la consulta a Amazon; `external_id` > 64 caracteres podía tumbar la migración al arrancar; una respuesta vacía de Amazon terminaba el lote entero) y además productos huérfanos y el aviso tras «Aplicar» protegido. Menores aplazados en TD-44.
- **Sitemap de producción sin chollos ni categorías** (previo a este trabajo): el Worker los leía con `supabaseAdmin` y el fallo se silenciaba. Ahora salen de la API (`GET /v1/deals/sitemap`, `/v1/categories`): en local 99 chollos (73 activos + 26 sin oferta) y 91 categorías, antes 0.
- Verificación: 653 pruebas backend unitarias, 56 de integración en un esquema tipo CI (Postgres 17 local) y las del catálogo sobre el esquema real, 450 de frontend, typecheck y lint sin errores; batería en vivo `local-env/qa` **164/164**; capturas a 375 y 1280 px sin desbordamiento; ejecución real de la revisión contra la Creators API sobre la copia local (156 productos en ~19 s; una segunda ejecución simultánea recibe 409).
- Deuda nueva: TD-39 a TD-44. **Para desplegar**: `pg_dump` previo, merge `develop`→`main`, rebuild en el NAS (la migración corre sola en `alembic upgrade head`); no hay dependencias nuevas.

## 2026-11-04 · Despliegue a producción

- Merge `develop`→`main` (`9772ddd`), copia de trabajo del share en `main`, rebuild en el NAS (`docker-compose build && up -d`: Pillow 13.0.0, `alembic upgrade head` sin cambios), web por Workers Builds en ~6 min, CI de `main` en verde. Comprobado: `/health` y `/health/ready` OK, `check-link` sin sesión → 401, `/publicar` 200, botón "Publicar chollo" en la home, JSON-LD de las fichas escapado. Backfill de `canonical_url`: 0 pendientes. Pendiente de confirmar: Redirect URL `https://buenchollotech.com/**` en Supabase Auth.
- Incidencia menor: el primer `git merge` falló con *Permission denied* porque el Vite del entorno local tenía abierto un directorio del share; se paró el entorno local y el segundo intento fue limpio. Lección en `docs/guides/LOCAL-ENV.md`: parar el entorno local antes de cambiar de rama o mergear en el share.

## 2026-11-04 · Entorno local de pruebas y prueba exhaustiva de `develop`

- Nuevo `local-env/` (guía `docs/guides/LOCAL-ENV.md`): `bct-local.cmd setup|start|stop|status|reset-db|logs|users|qa|stress`. Web + API + PostgreSQL 17 portable + capturador de correo en `localhost`, sin Docker y **aislado de la BD de producción**: esquema = `pg_dump --schema-only` del esquema real + `alembic upgrade head`; datos = copia de solo lectura del catálogo (tiendas, categorías, 157 chollos, blog, 152 programados). Auth, Storage y Amazon siguen siendo reales; scheduler y Telegram apagados. Reproducible en cualquier PC Windows (Python 3.11 + Node 20).
- Batería en vivo `local-env/qa` (pytest, 164 casos contra la API real local con 6 usuarios reales de prueba) y estrés `local-env/qa/stress.py` (8 escenarios).
- **Fallos encontrados y corregidos**: (1) **XSS almacenado** en las fichas públicas: el JSON-LD (`<script type="application/ld+json">`) se serializaba con `JSON.stringify` y un título o descripción con `</script>` rompía el bloque (afecta también a `main`; nuevo `src/lib/json-ld.ts` en chollo, inicio, categoría y blog); (2) un ASIN en minúsculas (`/dp/b09b8x9rgm`) no se reconocía: enlace **sin tag de afiliado**, sin autorrelleno y saltándose la detección de duplicados; (3) el admin podía guardar un chollo con cualquier `status` de texto libre (quedaba invisible); ahora `active|expired|scheduled|draft`; (4) `check-link` aceptaba IPs, `localhost`, hosts internos, credenciales en la URL y puertos raros como "tienda"; (5) test `test_preview_sin_candidatos_devuelve_lista_vacia` con un mock obsoleto que en local llamaba a Amazon de verdad.
- Deuda nueva: TD-36 (las migraciones SQL de `supabase/` no describen producción), TD-37 (clientes REST de Supabase que ignoran `DATABASE_URL`), TD-38 (menores).

## 2026-11-04 · Chollos de usuarios (cierre en `develop`)

- Los usuarios registrados pueden proponer chollos (`/publicar`, botón "+ Publicar chollo") y seguirlos en `/mis-chollos`; el admin los modera en `/admin/propuestas` (editar, aprobar como publicado/programado/borrador, rechazar con motivo). El autor recibe correo y notificación; el admin recibe aviso por correo (`ADMIN_NOTIFICATION_EMAIL`). La ficha pública muestra "Compartido por" y el cupón. Decisiones en ADR-015 (ingesta de imágenes) y ADR-016 (tabla separada, reescritores de afiliado, acortadores rechazados).
- Rango `a6feac7..HEAD` de `develop` (sin tocar `main`). Backend: módulos `submissions` y `affiliates`, `core/ssrf.py`, `core/body_limit.py`, rate limit por usuario, migración aditiva `20261103140000` (aplicada en la BD compartida; backfill de 178 chollos), dependencias `Pillow` y `limits`. Frontend: `features/submissions`, rutas `/publicar`, `/mis-chollos`, `/admin/propuestas`.
- Ronda final de correcciones tras la revisión de toda la rama: rate limit ya no falsificable con `X-Forwarded-For` (clave `CF-Connecting-IP`; por usuario en los endpoints de propuestas); conexión de BD liberada antes de E/S lenta; acortadores genéricos rechazados; aprobaciones programadas/borrador con texto propio; `asin` en `SubmissionResponse`; `AMAZON_AFFILIATE_TAG` obligatorio en producción; JWT con 30 s de margen de reloj; precios con separador de miles español.
- Verificación: 537 pruebas backend unitarias; 42 de integración en un Postgres 16 desechable (equivalente al job de CI; contra Supabase se salta el test que hace commit); 433 de frontend; typecheck, build y `pip-audit` limpios; lint sin errores. E2E Playwright de los dos specs nuevos: 16/16, dos veces seguidas. E2E real (2026-11-04) contra Supabase, Amazon y Zoho con usuarios de prueba creados y borrados después: check-link, subida/pegado/importación de imágenes, creación, duplicado 409, retirada, aprobar y rechazar con correos recibidos, navegador real sin respuestas distintas de 2xx; sin datos residuales. Estrés (`buenchollo-api/scripts/stress_submissions.py`, 5 usuarios): 50 check-link concurrentes → 20×200 y 30×429 sin 5xx; 20 creaciones del mismo producto → 1 pending, resto 409/429; 30 subidas de PNG sin 5xx y memoria estable (pico ~273 MB); ráfagas con `Retry-After`. Prueba de concurrencia local: 12 check-link con Amazon lento en 1,2 s (3,2 s sin liberar la conexión).
- Incidencias del proceso: un subagente ejecutó `taskkill /IM python.exe` (puede haber matado procesos Python locales; ya prohibido en las instrucciones); aprobar el chollo de la prueba real disparó 2 notificaciones de alerta a usuarios reales (se borraron con el chollo, ~11 min visibles).
- **Pendiente de despliegue** (checklist en `docs/project/08-deployment.md`): merge `develop`→`main`, `ADMIN_NOTIFICATION_EMAIL` y `AMAZON_AFFILIATE_TAG` no vacío en el `.env` del NAS, rebuild por `Pillow`/`limits`, Redirect URLs de Supabase Auth con `https://buenchollotech.com/**` y re-ejecutar `scripts/backfill_canonical_urls.py --apply`.
- Deuda nueva: TD-23 a TD-35 en `docs/project/10-technical-debt.md`.

## 2026-11-03 · Programación Telegram y web

- Telegram puede guardarse aunque falten datos para la web. El chollo enlazado queda en borrador y se marca `web_ready=false` hasta corregirlo desde Planificación.
- El título ya no exige tres caracteres: solo que no esté vacío. Planificación muestra un aviso visible para las fichas pendientes.
- El publicador envía Telegram sin activar la web incompleta. Con ASIN y precio mantiene la comprobación de stock y variación de precio; sin ellos conserva el texto aprobado por el administrador.
- El contexto Docker de API/scheduler excluye `.env`, entornos virtuales y cachés. Imagen reconstruida y comprobada sin `/app/.env`; la configuración de producción sigue entrando mediante `env_file` y el volumen montado.
- Merge funcional `cc9c827` y merge documental `3e6c1aa` en `main`. Migración `20261103120000_telegram_web_readiness.py` aplicada en producción y confirmada como head en el contenedor API. API y scheduler reconstruidos y reiniciados; API saludable y `/health` público responde 200. Los cinco trabajos de CI de ambos merges pasaron, incluida integración con PostgreSQL, E2E de Playwright y auditoría de seguridad. En local: 282 pruebas backend, 202 frontend con cobertura, TypeScript, ESLint y build SSR correctos. El E2E usa `PLAYWRIGHT_PORT` y sondeo de archivos en unidades de red.
- Comprobación web de producción (2026-11-03): portada y `/admin/chollos` responden 200; el HTML público carga `admin.chollos-6oze5U6N.js` y ese archivo contiene el nuevo aviso `WEB PENDIENTE`. El Worker actualizado está publicado. No se ha creado una programación real ni enviado contenido de prueba al canal Telegram; esa prueba funcional queda pendiente.

---

## 2026-11-01 · Sistema de correos Zoho y suite CI en verde

- **CI verde absoluto**: Run de GitHub Actions `41331100253` completado con éxito en los 5 jobs:
  - `Backend (pytest)`: 278 pruebas unitarias pasando en 19s (7 tareas en scheduler).
  - `Backend (integración + Postgres)`: 37 pruebas pasando en 43s.
  - `Security audit`: 0 vulnerabilidades en `pip-audit`, `npm audit` y `gitleaks`.
  - `Frontend (typecheck + lint + unit/integration)`: 187 pruebas Vitest con cobertura CORE ≥90%, ESLint y TypeScript sin errores.
  - `E2E (Playwright)`: 17 pruebas E2E pasando en 39s sobre Chromium.
  - Total: **519 pruebas automatizadas**.
- **Estabilidad de testing**:
  - Resuelto edge-case en `scheduled-deal-edit.spec.ts` (desbordamiento de semana/mes en FullCalendar en domingos) mediante `page.clock.setFixedTime`.
  - Cobertura total de `translateAuthError` en `src/lib/errors.test.ts` (100% branches/lines).
  - Mocks defensivos en `WelcomeProfileDialog.test.tsx` (`sendWelcomeEmail`).
- **Ruta dedicada de restablecimiento**: Creada `/restablecer-password` con formulario aislado
  (nueva clave + confirmación) y listener global ante eventos `PASSWORD_RECOVERY` de Supabase Auth.
- **Flujo de confirmación de email**: `Confirm email` configurado en Supabase Auth (`User Signups`);
  los registros con contraseña requieren verificación previa vía correo, retornando a `/login?confirmed=1`
  con confirmación explícita, mientras que los accesos con Google OAuth entran de inmediato.
- **Localización de errores Supabase**: `translateAuthError` traduce a español amigable todos los
  mensajes de error de autenticación (rate limit con contador de segundos, credenciales, caducidad OTP).
- **Correos transaccionales**: Integración completa de Zoho Mail (`smtp.zoho.eu:465` SSL)
  con `info@buenchollotech.com` como remitente oficial y `contacto@buenchollotech.com`
  como dirección de respuesta.
- **Flujos de negocio**:
  - Correo oficial de bienvenida al registrarse / completar el perfil (`POST /v1/auth/welcome`),
    con control de idempotencia vía `welcome_email_sent_at` en metadatos de Supabase Auth.
  - Resumen nocturno de alertas a las 21:00 en el scheduler para usuarios con aviso activo,
    cumpliendo con cabecera `List-Unsubscribe` y disclaimer de Amazon Afiliados.

## 2026-10-27 · Limpieza de advisories de dependencias y cabeceras web

- `zod` 3.25.76 → ^4.6.7 (GHSA-mrhx-c7xc-m3w5); único cambio de código:
  `z.ZodIssueCode.custom` → `"custom"` en `lib/validation/`.
- Overrides temporales en `buenchollo-web/package.json`: `miniflare.undici`
  = 7.30.1 y `@tailwindcss/typography.postcss-selector-parser` = 6.1.5
  (retirada condicionada, ver TD-22 en `docs/project/10-technical-debt.md`).
- `vitest`/`@vitest/coverage-v8` ^4.1.12, PyJWT 2.15.1, parches TanStack Start
  y Tiptap. `npm audit` (incl. dev) y `pip-audit` → 0; umbral CI de
  `npm audit` pasa de `critical` a `high`.
- Cabeceras de seguridad en las respuestas SSR del Worker (`src/start.ts`),
  cubiertas por `e2e/security-headers.spec.ts`.
- PR #62 mergeado a `main` (`90764cf`): CI completo y Workers Builds en verde;
  cabeceras comprobadas con `curl -sI https://buenchollotech.com`.

---

## Histórico resumido (hasta 2026-09)

La bitácora detallada anterior a octubre de 2026 se retiró de este fichero; sigue en el historial de Git (`git log -p -- PROJECT_STATUS.md`). Una línea por hito, con la fecha de cierre. Las cifras de pruebas de esas fechas están superadas: las vigentes están en [`docs/project/06-testing-and-quality.md`](docs/project/06-testing-and-quality.md).

**Arquitectura y calidad**
- 2026-05-26 · Refactor de buenas prácticas previo a v1.0.0 (SOLID/DRY/KISS): errores internos sanitizados, `DealService`, favoritos y estadísticas solo por API. ADR-002 cumplido al 100 %.
- 2026-05-27 · Hardening de seguridad: RLS activado en las 12 tablas tras el aviso crítico `rls_disabled_in_public` de Supabase ([ADR-006](docs/adr/ADR-006-rls-service-role.md)); ADR-003 a ADR-007.
- 2026-05-30 · Hardening arquitectónico F1–F7 (30 tareas) y release v1.0.0: `request_id`, logging estructurado, rate limiting, audit log, health checks, API `/v1`, frontend por features con TanStack Query y CI/CD.
- 2026-05-30 · Módulo de calidad: Vitest + Testing Library y estrategia 100/80/0 ([ADR-008](docs/adr/ADR-008-estrategia-calidad-testing.md)).
- 2026-06-02 · Módulo de seguridad: auditoría OWASP Top 10 con 6 hallazgos medios resueltos (SEC-01 a SEC-10, resumidos en [`07-security.md`](docs/project/07-security.md)); uso supervisado de IA ([ADR-009](docs/adr/ADR-009-uso-de-ia-en-desarrollo.md)).
- 2026-07-16 · Estabilización tras la auditoría técnica de julio; validación local de JWT con JWKS ([ADR-010](docs/adr/ADR-010-validacion-jwt-local.md)).
- 2026-07-17/18 · Cierre de la deuda técnica de la auditoría: `__init__.py` en todos los módulos, Dockerfile con usuario no root, scheduler en contenedor dedicado con `--workers 2` en la API, pool SQLAlchemy acotado y regla de caché de Cloudflare (la primera versión se retiró el mismo día por servir contadores obsoletos; detalle en [`Cloudflare.md`](docs/guides/Cloudflare.md)).
- 2026-07-22 · Blog con editor Tiptap ([ADR-011](docs/adr/ADR-011-blog-tiptap-editor.md)).

**Funcionalidad**
- 2026-08-09 · Notificaciones in-app en popover y alertas recomendadas.
- 2026-08-10 · Motor genérico de tareas programadas con la revisión de precios de Amazon como primera tarea ([ADR-012](docs/adr/ADR-012-motor-tareas-programadas.md)).
- 2026-08-12 · Motor de IA unificado con OmniRoute y fallback de modelos gratuitos ([ADR-013](docs/adr/ADR-013-motor-ia-unificado-omniroute-modelos-gratuitos.md)); 2026-08-29: failover a OpenAI oficial ante respuestas vacías o caídas.
- 2026-08-29 · Sugerencia de etiquetas de Telegram: comparación sin distinguir mayúsculas y blindaje en tres capas (timeout rápido con fallback a OpenAI, heurística de sinónimos en backend y coincidencias locales en el cliente).
- 2026-08-30 · Selector de motor de IA (OmniRoute / OpenAI / Auto) en el autocompletado de Amazon; la revisión de precios conserva el chollo si Amazon omite los campos de descuento pero el precio sigue en rango.
- 2026-09-05 · Recorte persistente de imágenes para Telegram (subida al bucket `deal-images`, migración idempotente que lo crea).
- 2026-09-25 · Fotos a Telegram como `multipart` (descarga previa) para evitar «failed to get HTTP URL content»; categoría de rescate «Varios» si la IA no clasifica.
- 2026-09-26 · Analítica first-party con atribución por sesión ([ADR-014](docs/adr/ADR-014-analitica-first-party-atribucion-sesiones.md)), enlaces `link.amazon`, ruta `/telegram` y edición integral de publicaciones programadas.

**Rendimiento (completado)**
- 2026-07-18 · Fase 1 (TD-11): API con 2 workers y `buenchollo-scheduler` aparte, pool de conexiones acotado a 10 como máximo contra el pooler de Supabase y caché de borde para GET públicos.
- 2026-08-29 · Fase 2: índice GIN trigram `ix_deals_title_trgm` (migración `20260829140000`) para las búsquedas `ILIKE`; `TelegramPanel` cargado con `React.lazy`; `GZipMiddleware(minimum_size=500)` (reduce un 70–80 % el tráfico de los listados grandes).

**Incidentes y lecciones**
- 2026-08-10 · 126 artículos de blog de prueba llegaron a producción porque `pytest -m integration` se ejecutó contra la base real y dos suites no limpiaban sus datos. Se restauró el estado correcto y se añadieron fixtures de limpieza por ID (TD-15, cerrado el 2026-08-29). Los tests de integración nunca deben apuntar a la base de producción.
- 2026-08-15 · El `.env` del NAS tenía `APP_ENV=local`: la API aceptaba CORS desde `localhost` y no enviaba HSTS. Se corrigió a `production`; tras tocar el `.env`, comprobar que `/health` devuelve `"environment":"production"`.
- 2026-09-02 · `scheduled_deals` se creó sin RLS (aviso crítico de Supabase). Se activó y se añadió `test_migrations_rls.py`, que falla si una migración crea una tabla pública sin RLS. 2026-09-05: hardening del Advisor (política `user_roles` con `(select auth.uid())`, `REVOKE EXECUTE` en funciones `SECURITY DEFINER`, `pg_trgm` movida al esquema `extensions`).
- 2026-09-02 · La revisión automática de precios fallaba en silencio por un `NameError` tras un refactor (el botón manual sí funcionaba). Corregido; ahora los fallos de cableado del worker deben llegar a la observabilidad (TD-19, cerrado el 2026-11-07).
