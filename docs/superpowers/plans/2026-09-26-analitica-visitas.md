# Plan de implementación — Analítica de visitas y atribución

**Fecha:** 2026-09-26
**Estado:** En implementación

## Objetivo

Medir tráfico real de la web y del blog, distinguir visitas, sesiones y
visitantes únicos, conservar el origen inicial durante toda la sesión y mostrar
los resultados dentro del panel de administración. Los artículos publican un
contador de visualizaciones validado y el enlace `/telegram` atribuye a Telegram
la navegación posterior hacia cualquier sección, incluido el blog.

## Definiciones

- **Visita:** carga visible de una ruta pública registrada por el navegador.
- **Sesión:** navegación del mismo dispositivo con menos de 30 minutos de
  inactividad.
- **Visitante único:** identificador aleatorio propio, pseudonimizado por el
  backend y válido un máximo de 13 meses. Representa un navegador/dispositivo,
  no una persona física demostrable.
- **Visualización pública de artículo:** primera visita del mismo visitante a un
  artículo durante un día natural UTC. Las recargas adicionales se conservan
  como visitas internas, pero no incrementan el contador público.
- **Origen de sesión:** primera atribución externa de la sesión; se conserva al
  navegar internamente. Prioridad: UTM explícita, referente de buscador,
  referente externo y directo/desconocido.

## Decisiones

1. Crear un módulo backend `analytics` dentro del monolito modular.
2. Persistir únicamente hashes HMAC de visitante y sesión; nunca IP ni el UUID
   enviado por el navegador en claro.
3. Usar PostgreSQL como fuente de verdad para que el panel admin y el contador
   compartan una definición estable, sin depender de un proveedor externo.
4. Añadir `blog_posts.view_count` como contador desnormalizado y una tabla de
   unicidad diaria para incrementos atómicos e idempotentes.
5. Registrar eventos tras hidratación, con la pestaña visible y una espera breve
   para evitar SSR, precargas y rastreadores que no ejecutan la aplicación.
6. Excluir rutas administrativas, administradores autenticados, user agents de
   bots conocidos y dispositivos marcados localmente.
7. Conservar eventos un máximo de 25 meses y ejecutar limpieza periódica desde
   el servicio de aplicación.
8. Mantener la medición estrictamente limitada a estadísticas propias de
   audiencia; actualizar las políticas legales y el aviso informativo.

## Esquema de datos

### `analytics_events`

- `id bigint identity` PK.
- `occurred_at timestamptz`.
- `visitor_hash char(64)` y `session_hash char(64)`.
- `path text`.
- `blog_post_id uuid null` con FK e índice.
- `source`, `source_detail`, `medium`, `campaign`, `referrer_host`.
- Índices por fecha, origen+fecha, visitante+fecha, sesión+fecha y
  artículo+fecha.

### `analytics_blog_daily_views`

- PK compuesta: `blog_post_id`, `visitor_hash`, `view_date`.
- Permite `INSERT ... ON CONFLICT DO NOTHING` y actualizar el contador solo si
  la visualización diaria es nueva.

### `blog_posts`

- `view_count bigint not null default 0`.

Las tablas de analítica tendrán RLS activo sin políticas para `anon` y
`authenticated`, igual que el resto de tablas internas del API Gateway.

## API

- `POST /v1/analytics/events`: endpoint público limitado, valida payload,
  filtra bots, pseudonimiza identificadores y registra el evento.
- `GET /v1/analytics/admin/overview?days=7|30|90`: resumen protegido por
  `require_admin`, con serie temporal, fuentes, páginas y artículos principales.
- `BlogPostDetailResponse.view_count`: contador público del artículo.

## Frontend

1. Servicio `analyticsApi` y utilidades puras para origen/sesión.
2. `AnalyticsTracker` global dentro de `AuthProvider`:
   - espera a conocer el rol;
   - no registra administradores ni `/admin`;
   - renueva sesión tras 30 minutos;
   - mantiene la atribución inicial al cambiar de ruta.
3. Ruta `/telegram` que redirige a `/?utm_source=telegram&utm_medium=social&utm_campaign=canal`.
4. Contador con icono `Eye` al pie del artículo.
5. Nueva ruta `/admin/analitica` con:
   - visitas, visitantes, sesiones y visitas al blog;
   - recorrido Telegram/buscador hacia blog;
   - serie temporal;
   - desglose por fuentes;
   - páginas y artículos más vistos;
   - selector 7/30/90 días;
   - control para excluir/incluir el dispositivo.

## Estrategia TDD y verificación

1. Tests unitarios de clasificación de origen, renovación de sesión y
   persistencia limitada del identificador.
2. Tests unitarios backend de HMAC, filtro de bots y orquestación idempotente.
3. Tests de repositorio/API PostgreSQL para inserción, deduplicación diaria,
   autorización y agregados.
4. Tests de componentes para contador, estados de carga y dashboard.
5. Ejecutar `pytest`, `npm run test:run`, `npm run typecheck`, `npm run lint` y
   `npm run build`.
6. Verificación visual responsive del panel y del pie de artículo.

## Despliegue

1. Configurar `ANALYTICS_HASH_SECRET` aleatorio y privado en el NAS.
2. Aplicar la migración Alembic antes de arrancar la nueva versión.
3. Validar `/telegram`, tráfico orgánico y exclusión de admin en `develop`.
4. Publicar en `main` tras comprobar el panel con tráfico real de prueba.

## Documentación obligatoria

- ADR-014 con la decisión de analítica propia y atribución first-touch.
- Actualización del índice de ADRs, configuración y políticas web.
- Nota conceptual y relaciones en `OBSIDIAN VAULT`, actualización de
  `index.md` y entrada append-only en `log.md`.
