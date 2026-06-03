# 03 — Análisis funcional

## Usuarios previstos

El proyecto distingue tres perfiles, con permisos crecientes y casos
de uso diferenciados.

### Usuario anónimo

Acceso público sin necesidad de cuenta. Representa al consumidor
casual: alguien que llega a la web por buscador, por enlace
compartido en Telegram, o por curiosidad.

**Lo que puede hacer**:

- Navegar la home con el feed de chollos recientes y la sección de
  más populares.
- Buscar y filtrar chollos por categoría, tienda y término libre.
- Ver el detalle de un chollo: descripción técnica, gráfica de
  precios Keepa, comentarios, votos.
- Abrir el enlace afiliado para ir a Amazon.
- Acceder al canal de Telegram desde el footer.
- Iniciar sesión con Google si quiere pasar a usuario registrado.

**Lo que NO puede hacer**:

- Votar, comentar, marcar favoritos, crear alertas. Cualquier intento
  muestra un mensaje de "Inicia sesión para…".

### Usuario registrado

Acceso autenticado mediante Google OAuth (gestionado por Supabase
Auth). Representa al miembro activo de la comunidad.

**Lo que puede hacer (además de lo anterior)**:

- Votar chollos con `up`/`down`. El voto es toggle: votar lo mismo
  dos veces lo retira. La temperatura del chollo se recalcula en cada
  voto.
- Comentar chollos en hilos. Anidamiento por `parent_id`. Cada usuario
  sólo puede borrar sus propios comentarios (ownership check
  server-side).
- Votar comentarios.
- Marcar y desmarcar favoritos. Lista accesible en `/favoritos`.
- Crear alertas personalizadas en `/alertas/nueva` con uno o varios
  criterios: palabra clave, categoría, tienda, marca, precio máximo,
  descuento mínimo.
- Gestionar sus alertas en `/alertas` (listar, activar/desactivar,
  borrar).
- Ver la bandeja de notificaciones en `/notificaciones` y el badge en
  el header.
- Editar su perfil (nombre público, bio) en `/perfil`.
- Cerrar sesión.

### Administrador

Mismos permisos que un usuario registrado, más el panel
administrativo. En el proyecto actual hay un único administrador (el
autor). Documentado como decisión y como mejora futura en
[`09-limitaciones-y-mejoras-futuras.md`](09-limitaciones-y-mejoras-futuras.md).

**Lo que puede hacer (además)**:

- Acceder al panel `/admin` con dashboard de estadísticas (chollos
  totales, activos, usuarios, favoritos, alertas, comentarios).
- Gestionar chollos (`/admin/chollos`): crear, editar, programar,
  publicar inmediatamente, marcar como expirado, eliminar.
- Usar el **autocompletado desde URL de Amazon**: pega una URL
  (incluso acortada `amzn.to/xxx`), el sistema extrae el ASIN, llama
  a Amazon Creators API para obtener título, precio, imágenes y
  metadatos, y a OpenAI para generar copy técnico y copy para
  Telegram. El admin revisa y guarda.
- Recibir el diálogo de **chollo duplicado**: si intenta publicar un
  producto cuyo ASIN ya existe en otro chollo, la plataforma lo avisa
  con dos opciones: ir al chollo existente para editarlo, o
  sobrescribirlo con los datos del nuevo (conservando id, slug,
  comentarios y votos).
- Gestionar el **catálogo maestro** (`/admin/categorias`,
  `/admin/tiendas`) con CRUD.
- Ver el **listado de usuarios** registrados con sus roles
  (`/admin/usuarios`).
- Publicar manualmente en Telegram con copy adaptado (panel
  integrado en el form de chollos).

## Funcionalidades principales

### Feed y navegación

- **Home** (`/`): hero + sección "MÁS POPULARES" (4 chollos por
  temperatura) + sección "TRANSMISIÓN EN VIVO" (feed infinito por
  `published_at desc` con paginación offset/limit por bloques de
  16).
- **Explorar** (`/explorar?q=...`): vista de búsqueda con filtros por
  categoría/tienda/término.
- **Detalle** (`/chollo/{slug}`): título, precio actual y anterior
  con descuento, imagen, descripción Markdown, gráfica Keepa
  (cuando hay ASIN), comentarios, votos, botón compartir.
- **Categorías** (`/categorias`): vista de todas las categorías con
  iconografía Lucide dinámica desde la BD.

### Sistema de alertas

- Modelo `Alert` con campos `keyword`, `category_id`, `store_id`,
  `brand`, `max_price`, `min_discount_percentage`, `notify_email`
  (preparado), `notify_in_app` (activo por defecto), `is_active`,
  `last_triggered_at`.
- **`AlertMatcher`** en `alerts/application/`: recibe un `Deal`,
  busca alertas activas que coincidan según los criterios del modelo,
  crea una `Notification` por cada usuario con alerta compatible,
  actualiza `last_triggered_at`.
- **Anti-spam**: si ya existe una notificación para el par
  `(alert_id, deal_id)`, no se crea duplicada (aunque el chollo se
  actualice múltiples veces).
- **Keyword matching tolerante**: si la frase exacta aparece en
  `title`, `short_description` o `description`, hay match. Si no,
  se exige que todos los tokens aparezcan. Se normaliza el texto
  para tolerar mayúsculas/minúsculas y acentos.

### Notificaciones in-app

- Modelo `Notification` con `type`, `title`, `body`, `link_url`,
  `deal_id`, `alert_id`, `is_read`.
- **Bandeja** en `/notificaciones` que marca como leídas al cargar.
- **Badge** en el header que muestra el conteo de no leídas (`9+`
  cuando supera 9). Refrescado con TanStack Query
  (`useUnreadNotifications`) y `refetchOnWindowFocus: true`.

### Publicación a Telegram

- El módulo `telegram/` tiene su `TelegramPostGenerator` que combina:
  - Título, precio, descuento, imagen.
  - Copy técnico generado por OpenAI a partir de la descripción
    Amazon (limpiado y adaptado a tono comercial).
  - Footer con el enlace de afiliado.
  - Emojis Premium si el chat lo soporta.
- Botón "Enviar a Telegram" en el panel admin con preview editable
  antes de publicar. Rate limit 5/min para evitar dobles envíos
  accidentales.

### Scheduler

- `DealCleanerService` registrado en el `lifespan` de FastAPI:
  - `mark_expired_deals`: cada 5 min, marca como `expired` los
    chollos cuyo `expires_at` ha pasado.
  - `activate_scheduled_deals`: cada 5 min, pasa a `active` los
    chollos `scheduled` cuya fecha `scheduled_for` ha llegado.
  - `clean_expired_deals`: 03:00 diariamente, limpia recursos
    asociados a chollos antiguos.
- Cada job está aislado: si uno revienta, los otros siguen
  ejecutándose (patrón `_safe_run`).

## Flujos de uso clave

### F1 — Usuario anónimo descubre un chollo

1. Llega a `/` → ve el feed.
2. Click en una card → `/chollo/{slug}`.
3. Ve precio, descuento, gráfica Keepa.
4. Click en "Ir a la oferta" → abre Amazon con el tag de afiliado.

### F2 — Usuario se registra y crea una alerta

1. Click en `[ ACCEDER ]` en el header → `/login`.
2. Click en "Continuar con Google" → flujo OAuth de Supabase →
   redirección de vuelta a `/`.
3. Va a `/alertas/nueva` → escribe "monitor 4k" + descuento mínimo
   30 → "Crear alerta".
4. Cuando el admin publica un monitor 4K con ≥30% descuento, el
   `AlertMatcher` crea una notificación, el badge sube a 1.
5. El usuario va a `/notificaciones`, ve el aviso, lo clicka y aterriza
   en el detalle del chollo.

### F3 — Admin publica un chollo desde URL de Amazon

1. Login admin → `/admin/chollos` → "NUEVO".
2. Pega `https://amzn.to/3xyz` → "AUTOCOMPLETAR".
3. El backend:
   - Sigue el redirect (con allowlist Amazon + bloqueo IPs privadas
     — defensa SSRF).
   - Extrae el ASIN.
   - Llama a Amazon Creators API → título, precio, imágenes,
     descripción técnica.
   - Llama a OpenAI → copy adaptado + categorización sugerida.
   - Devuelve todo al frontend.
4. El admin revisa el formulario ya rellenado, ajusta categoría si
   procede, click "Guardar".
5. Si el ASIN ya existía en otro chollo → diálogo "Chollo duplicado"
   con tres opciones (sobrescribir / ir al existente / cancelar).
6. Si no → se crea el deal, se dispara `AlertMatcher` y se actualiza
   `admin_audit_log`.
7. Opcionalmente, el admin pulsa "Enviar a Telegram" con el copy
   generado.

### F4 — Usuario vota un chollo

1. Estando logueado, en el detalle → click en `↑` o `↓`.
2. `POST /v1/deals/{id}/vote` (rate limit 30/min):
   - Si era el mismo voto: lo retira (toggle).
   - Si era distinto o ninguno: lo registra.
3. El backend recalcula la temperatura del chollo (`votes_up -
   votes_down + offset`) y devuelve los contadores actualizados.
4. El frontend muestra inmediatamente la nueva temperatura sin
   refresco completo.

## Casos de uso secundarios

- **Recuperación de ASINs históricos**: el endpoint one-shot
  `POST /v1/deals/admin/backfill-external-ids` (eliminado en producción
  tras uso) permitió rellenar `external_id` de chollos publicados
  antes de que existiera el campo. Documentado en
  `PROJECT_STATUS.md`.

- **Compartir un chollo**: cada detalle tiene un `ShareBox` con la URL
  canónica + botones de copy/share.

- **Detección de duplicados a futuro**: el índice único parcial
  `uq_deals_external_id ON deals(external_id) WHERE external_id IS
  NOT NULL` garantiza a nivel de BD que dos chollos no compartan
  ASIN.

## Limitaciones funcionales actuales

- **Sin notificaciones por email**: el modelo `notify_email` está
  preparado pero no se ha integrado proveedor SMTP. Decisión:
  priorizar primer canal (in-app) y dejar la elección de proveedor
  (Resend / Sendgrid / Supabase Edge Function) para después de
  validar la audiencia.
- **Sin filtrado por usuario en la bandeja**: las notificaciones se
  ordenan por fecha sin opción de filtro avanzado.
- **Sin tracking de "leído" granular**: marcar como leído opera sobre
  todas las pendientes al cargar `/notificaciones`. No hay marcado
  individual.
- **Matching de alertas básico**: el algoritmo soporta substring y
  tokens, pero no sinónimos, stemming ni búsqueda semántica.
  Documentado como mejora futura.
- **Sin API pública**: la API es de uso interno del frontend, no
  pensada para integraciones de terceros (CORS restringido, sin
  documentación pública del endpoint).

Estas limitaciones se han mantenido **a sabiendas** como deuda
asumida y conscientemente documentada, no como omisiones.
