# 02 — Objetivos y alcance

## Objetivo general

Construir una plataforma web completa de comunidad de ofertas
tecnológicas que sirva simultáneamente como **producto personal en
producción** y como **soporte para demostrar la aplicación de los
contenidos del Máster en Desarrollo con IA 2025**.

El objetivo no es entregar un prototipo desechable, sino un sistema
**defendible técnicamente**, con decisiones explicadas, niveles de
calidad y seguridad medibles, y un código que se pueda mantener y
evolucionar.

## Objetivos específicos

### Académicos

1. **Aplicar una arquitectura de software razonada y documentada.**
   No microservicios por moda; un monolito modular con Clean
   Architecture pragmática es lo que encaja con el tamaño del
   proyecto. Cada decisión queda en un ADR firmado.

2. **Implementar una estrategia de calidad medible.** Pirámide de
   testing (unit + integration + E2E), coverage estratégico
   100/80/0 y quality gates automáticos con métricas accionables.

3. **Aplicar Security by Design y Security by Default.** Auditoría
   OWASP Top 10 con hallazgos priorizados y mitigaciones efectivas,
   no decorativas.

4. **Usar IA como apoyo supervisado al desarrollo.** Claude Code
   como asistente arquitectónico, de calidad y de seguridad, con
   prompts dedicados a auditorías por módulo y validación obligatoria
   por tests + revisión humana antes de cada commit.

5. **Defender públicamente las decisiones tomadas.** Toda la
   documentación está orientada a que un tribunal pueda entender qué
   se hizo, por qué y con qué resultado.

### De producto

6. **Tener una plataforma en producción** que sirva chollos reales a
   usuarios reales (canal Telegram existente + dominio futuro).

7. **Automatizar el flujo manual** que el autor ya hacía con
   mensajes: pegar URL Amazon → publicación enriquecida en web y
   Telegram en menos de 30 segundos.

8. **Permitir crecimiento futuro** sin reescribir el núcleo:
   funcionalidades cumplen Single Responsibility, los servicios
   externos están detrás de adaptadores (Protocols), añadir un nuevo
   proveedor (Aliexpress, PCComponentes) implica crear un adaptador,
   no tocar el resto.

## Alcance funcional

### Lo que incluye el MVP

**Para usuarios anónimos**:
- Navegación pública de chollos (home con feed infinito, más
  populares, búsqueda, detalle).
- Acceso al canal de Telegram desde la propia web.
- Click en el enlace afiliado (Amazon Associates).
- Gráfica de precios histórica (Keepa) en el detalle del chollo.

**Para usuarios registrados** (Google OAuth):
- Todo lo anterior, más:
- Votar chollos (sistema de temperatura con `up`/`down` y toggle).
- Comentar chollos con anidamiento.
- Marcar como favorito.
- Crear alertas personalizadas por palabra clave, categoría, tienda,
  marca, precio máximo o descuento mínimo.
- Recibir notificaciones in-app cuando se publique un chollo que
  coincida con alguna alerta activa.

**Para administradores**:
- Panel `/admin` con CRUD completo de chollos, categorías y tiendas.
- Autocomplete a partir de una URL de Amazon: el sistema extrae ASIN,
  título, precio actual y anterior, descripción técnica, imágenes,
  marca y categoría sugerida (Amazon Creators API + OpenAI).
- Detector de duplicados por ASIN: si el admin intenta publicar un
  producto ya existente, la plataforma lo avisa y ofrece sobrescribir o
  ir al chollo existente para editarlo.
- Publicación al canal de Telegram con copy adaptado (generado por IA y
  editable antes de enviar).
- Audit log de todas las acciones críticas correlacionado con
  `request_id` y Sentry.
- Vista de usuarios registrados con sus roles.
- Recuperación masiva de ASINs para chollos publicados antes del
  campo (one-shot endpoint temporal documentado).

### Lo que NO incluye el MVP

Documentado en [`09-limitaciones-y-mejoras-futuras.md`](09-limitaciones-y-mejoras-futuras.md):

- Notificaciones por email (modelo `notify_email` preparado, pero el
  primer canal funcional es la campana in-app).
- Búsqueda semántica con embeddings.
- App móvil nativa.
- Internacionalización (web en español únicamente).
- 2FA TOTP en código (queda como configuración externa en Supabase
  para el admin).
- Múltiples administradores.

## Alcance técnico

| Capa | Tecnología | Justificación rápida |
|---|---|---|
| Frontend | React 19 + TypeScript strict + Vite + TanStack Router/Query + Tailwind + shadcn/ui | Stack maduro, ecosistema activo, TS strict para detección temprana de errores, TanStack Router para file-based routing y type-safe navigation |
| Backend | Python 3.11 + FastAPI 0.136 + SQLAlchemy 2 async + asyncpg + Pydantic v2 | Async-first, OpenAPI auto-generado, Pydantic v2 para validación con tipos, ecosistema maduro |
| BD | PostgreSQL via Supabase (managed) + RLS activado en 12 tablas | Managed Postgres con Auth y Storage integrados, RLS como red de seguridad, gratis hasta cierto tamaño |
| Auth | Supabase Auth (Google OAuth + email) | OAuth listo en 2 días, recovery + rate limit gestionados por Supabase, JWT estándar |
| Storage | Supabase Storage (subida directa desde admin) | Excepción al patrón API Gateway documentada en ADR-002 |
| External | Amazon Creators API + OpenAI GPT-4o + Telegram Bot API + Sentry SaaS | Necesarios para el copy automático y la publicación |
| Deploy | NAS Synology DSM 7.2+ + Docker Compose + reverse proxy DSM + Let's Encrypt | Coste cero, control total, suficiente para audiencia inicial |
| CI/CD | GitHub Actions (4 jobs: backend pytest, frontend Vitest, E2E Playwright, security-audit) + Dependabot semanal | Pipeline mínimo defendible, gates automáticos |
| Quality | Husky pre-commit + pre-push, ESLint estricto, TypeScript strict, Pydantic constraints, coverage 100/80/0 | Defensa en profundidad antes del CI |

## Qué se considera "terminado"

El proyecto se considera completable cuando se cumplen estas
condiciones, todas presentes en el repositorio en el momento de la
entrega:

1. ✅ **CI verde en `main`** con los 4 jobs (backend, frontend, E2E,
   security-audit).
2. ✅ **167 tests automatizados verdes**: 87 pytest (78 unit + 9
   integración local), 72 Vitest (59 unit + 13 integration), 8
   Playwright.
3. ✅ **Coverage threshold** automatizado en `src/lib/**` ≥ 90%.
4. ✅ **0 CVEs conocidas** en dependencias de producción (`pip-audit`
   + `npm audit --omit=dev`).
5. ✅ **9 ADRs firmados** cubriendo las decisiones clave.
6. ✅ **Documentación dual** (operativa + defensa académica)
   organizada y coherente.
7. ✅ **Plataforma desplegada y accesible** en el NAS (DDNS Synology).
8. ✅ **Tag de release `v1.0.0-tfm`** publicado.

Todos estos puntos están cumplidos en el momento de redactar este
documento.
