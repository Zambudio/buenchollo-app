# 11 · Estado actual verificado

> Fuente de verdad resumida del estado operativo y funcional de BuenCholloTech.
> Última auditoría: **2026-09-26**. La versión funcional auditada y desplegada
> corresponde al merge `eee0a97`; el historial detallado permanece en
> `PROJECT_STATUS.md`.

## Producción

| Pieza | Estado actual |
|---|---|
| Web | `https://buenchollotech.com`, React 19 + TanStack Start SSR desplegado como Cloudflare Worker |
| API | `https://api.buenchollotech.com`, FastAPI en Docker sobre NAS Synology y publicada mediante Cloudflare Tunnel |
| Base de datos | PostgreSQL de Supabase mediante PgBouncer en puerto 6543 |
| Autenticación | Google OAuth con Supabase Auth; la API valida JWT localmente mediante JWKS |
| Procesos NAS | `buenchollo-api`, `buenchollo-scheduler` y `cloudflared` |
| Despliegue web | Automático al hacer push a `main` mediante Cloudflare Workers Builds |
| Despliegue API | Volumen del proyecto montado en Docker; migraciones Alembic al arrancar y reinicio controlado de API/scheduler |

No se abren puertos del router, no se usa DDNS para publicar la API y el NAS no
sirve el frontend. Las instrucciones antiguas de reverse proxy, Let's Encrypt y
DDNS se conservan solo como histórico dentro de la guía de despliegue.

## Superficie funcional

### Web pública

- Feed, detalle, búsqueda, categorías, favoritos y votación de chollos.
- Comentarios y votos en comentarios.
- Alertas personalizadas y notificaciones dentro de la aplicación.
- Blog público con categorías, comentarios, votos, RSS y sitemap.
- Contador público de lecturas de artículos validado por navegador y día.
- Entrada `/telegram`, que atribuye el origen a Telegram y redirige a la portada.
- Perfil de usuario, autenticación con Google y páginas legales.

### Administración

- CRUD de chollos, categorías, tiendas, usuarios y contenido del blog.
- Autocompletado seguro desde enlaces oficiales de Amazon, incluidos
  `https://link.amazon/...`, `amzn.*` y dominios Amazon admitidos.
- Enriquecimiento con Amazon Creators API, Keepa y el motor de IA unificado.
- Preparación, previsualización, envío inmediato y programación de Telegram.
- Calendario de publicaciones programadas con edición integral de los datos web:
  ASIN, título, resumen, descripción, precios, tienda, categoría, subcategoría,
  marca, envío, enlaces, imágenes, caducidad y gráfica Keepa. El texto/canal de
  Telegram mantiene su edición independiente.
- Motor genérico de tareas programadas y revisión periódica de precios.
- Panel de analítica con visitas, visitantes únicos, sesiones, lecturas de blog,
  evolución, procedencia, páginas y conversión Telegram → blog.
- Exclusión del dispositivo del administrador para no contaminar las métricas.

### Atribución de tráfico

- La analítica es first-party y conserva el primer origen de la sesión.
- `/telegram` establece `utm_source=telegram`; el enlace general incluido en las
  publicaciones de Telegram usa `https://buenchollotech.com/telegram`.
- El enlace de compra de cada publicación sigue siendo el enlace afiliado.
- Las búsquedas se clasifican por referer de buscadores conocidos; el tráfico sin
  una señal fiable permanece como directo, no se inventa una procedencia.
- Los identificadores se seudonimizan con HMAC y `ANALYTICS_HASH_SECRET`; la
  retención máxima configurable es de 25 meses.

## Módulos de backend activos

`ai`, `alerts`, `analytics`, `blog`, `blog_comments`, `categories`, `comments`,
`deals`, `notifications`, `products`, `scheduled_deals`, `scheduled_tasks`,
`stores`, `telegram` y `users`.

Todos los routers de negocio se publican bajo `/v1`; `/health` y
`/health/ready` quedan fuera de esa versión. El frontend accede a datos de negocio
solo mediante la API; las excepciones deliberadas son Supabase Auth y Storage.

## Integraciones y configuración crítica

| Integración | Configuración relevante |
|---|---|
| Supabase | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET` |
| Analítica | `ANALYTICS_HASH_SECRET`, `ANALYTICS_RETENTION_MONTHS` |
| Amazon | `AMAZON_CLIENT_ID`, `AMAZON_CLIENT_SECRET`, `AMAZON_AFFILIATE_TAG` y configuración Creators API |
| IA | `AI_PROVIDER`, `AI_BASE_URL`, `AI_MODEL`, fallbacks y fallback opcional a OpenAI |
| Telegram | token del bot y canales principal/admin |
| Frontend | `VITE_API_URL`, credenciales públicas de Supabase y `VITE_SENTRY_DSN` opcional |

Los valores reales viven fuera de Git. `buenchollo-api/.env.example` y
`buenchollo-web/.env.example` son las plantillas; la explicación completa está en
`04-configuration.md`.

## Calidad verificada

La última ejecución completa de `main` terminó en verde en GitHub Actions tras el
commit de producción `eee0a97`:

- 272 pruebas backend sin BD y 37 pruebas backend de integración con PostgreSQL.
- 186 pruebas Vitest de frontend.
- 16 pruebas E2E Playwright en Chromium.
- Total verificado: **511 pruebas automatizadas**.
- TypeScript, ESLint, coverage, `pip-audit`, `npm audit` y gitleaks forman parte
  de los gates del CI.

Las cifras son una fotografía fechada, no un contrato. El workflow
`.github/workflows/ci.yml` es la autoridad sobre qué se ejecuta actualmente.

## Datos y migraciones

- Alembic contiene la cadena incremental actual hasta
  `20260926120000_add_first_party_analytics.py`.
- Las tablas nuevas activan RLS en su propia migración; existe una prueba de
  regresión que detecta nuevas tablas públicas sin RLS.
- La API usa la conexión de servicio y las credenciales privilegiadas nunca se
  exponen al navegador.
- Los buckets de Storage para avatares, imágenes de chollos y blog conservan sus
  políticas específicas.

## Pendientes abiertos

La lista canónica está en `10-technical-debt.md`. A 2026-09-26 quedan tres puntos
operativos conocidos:

1. Rotar y verificar el token de Cloudflare Tunnel que la guía registra como
   expuesto en una conversación (TD-21).
2. Activar manualmente la protección de contraseñas filtradas en Supabase Auth.
3. Hacer que los fallos de cableado del worker de tareas programadas propaguen a
   la observabilidad en lugar de terminar como una ejecución aparentemente válida.

No se consideran pendientes las funciones ya desplegadas de analítica,
`link.amazon`, atribución `/telegram` ni edición integral de publicaciones.

## Dónde mantener cada cambio

| Cambio | Documento que debe actualizarse |
|---|---|
| Estado operativo o release | `PROJECT_STATUS.md` y esta página |
| Nueva variable | `.env.example` y `04-configuration.md` |
| Decisión difícil de revertir | Nuevo ADR y `docs/adr/00-index.md` |
| Funcionalidad o flujo | `docs/master/03-analisis-funcional.md` |
| Arquitectura/despliegue | `docs/master/04-arquitectura-y-decisiones-tecnicas.md` y guía correspondiente |
| Deuda abierta | `10-technical-debt.md` |
| Conocimiento reutilizable | Ficha relacionada en `OBSIDIAN VAULT` siguiendo su `SCHEMA.md` |

---

[← Deuda técnica](10-technical-debt.md) · [Índice operativo](00-index.md)
