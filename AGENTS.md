# AGENTS.md — BuenCholloTech

Instrucciones permanentes para agentes de IA (Antigravity, Claude Code, Cursor, Codex) en este proyecto.

---

## Rol y actitud

Actúa siempre como desarrollador senior, arquitecto de software y revisor técnico.
Respuestas concisas y directas. Sin relleno, sin recapitular lo que acaba de decir el usuario.
Si falta contexto para tomar una decisión, pregunta antes de inventar.
Ante varias opciones válidas, elige la más simple y mantenible.

---

## Contexto del proyecto

**BuenCholloTech** es una plataforma para publicar, gestionar y automatizar chollos tecnológicos.
Proyecto personal en producción — las decisiones técnicas deben ser defendibles profesionalmente.

### Componentes

| Directorio | Stack | Rol |
|---|---|---|
| `buenchollo-api/` | Python 3.11 · FastAPI · SQLAlchemy · asyncpg | API Gateway — toda la lógica de negocio |
| `buenchollo-web/` | React · TypeScript · TanStack Router · Vite | Frontend — solo habla con buenchollo-api |

### Infraestructura

- **Base de datos**: PostgreSQL via Supabase (pooler PgBouncer puerto 6543)
- **Auth**: Supabase Auth (Google OAuth) — el backend valida JWT con `service_role key`
- **Storage**: Supabase Storage — subida directa desde el frontend (excepción deliberada al patrón API Gateway)
- **Despliegue**: NAS Synology — Docker container con volumen montado en `buenchollo-api/`
- **CORS**: configurado via `CORS_ORIGINS` en `.env` — actualmente `["*"]` en desarrollo

### Decisiones de arquitectura vigentes

- **ADR-001**: Monolito Modular con FastAPI y Clean Architecture pragmática
- **ADR-002**: Migración de BaaS directo a API Gateway — el frontend nunca llama a Supabase DB directamente
- **ADR-013**: Motor de IA unificado con OmniRoute / OpenCode, fallback de modelos gratuitos y base para Chatbot

---

## Arquitectura del backend (`buenchollo-api/`)

```
app/
├── core/          # config, database, security, logging (compartido)
└── modules/
    ├── ai/            # motor unificado LLM, fallback multi-modelo, copywriting, categorización, chatbot
    ├── deals/
    │   ├── domain/        # modelos SQLAlchemy (Deal)
    │   ├── application/   # casos de uso, cleaner_service
    │   ├── infrastructure/# repositorios, adapters externos
    │   └── api/           # router FastAPI, schemas Pydantic
    ├── products/          # preview Amazon (DIP con Protocols e integración ProductAIEnricher)
    ├── telegram/          # publicación al canal, formato emoji premium, hashtags IA
    ├── categories/
    ├── stores/
    └── users/
```

---

## Estado actual

- **Web en producción** en `https://buenchollotech.com` (frontend TanStack Start SSR como **Cloudflare Worker**; deploy automático al hacer push a `main` vía Workers Builds).
- **API** FastAPI en el NAS Synology, expuesta en `https://api.buenchollotech.com` vía **Cloudflare Tunnel** (sin abrir puertos, sin DDNS). `APP_ENV=production`, CORS cerrado al dominio.
- **Cloudflare endurecido**: TLS Full (strict) + HSTS, redirect `www`→raíz, WAF + rate limiting + Bot Fight Mode. Detalle y bitácora en [`docs/guides/Cloudflare.md`](docs/guides/Cloudflare.md).
- Login Google (Supabase) OK · Panel admin funcionando · CI de `main` en verde · flujo `main`/`develop` operativo.

---

## 🧠 Base de Conocimiento Global (OBSIDIAN VAULT)

Este proyecto está formalmente integrado con nuestra base de conocimiento general para todos los proyectos:
📁 **`z:\IA\02_Proyectos\OBSIDIAN VAULT`**

### Reglas Obligatorias para Cualquier Agente de IA:
1. **Consulta Previa Obligatoria al Desarrollar**: Siempre que estemos desarrollando, buscando arquitecturas, configurando endpoints, ajustando Cloudflare o resolviendo errores, **el agente DEBE buscar y consultar información primero en `OBSIDIAN VAULT`** (`OBSIDIAN VAULT/index.md`).
   - Ficha de entidad: `Entities/Proyecto-BuenCholloTech.md`.
   - Conceptos arquitectónicos clave: `Concepts/Despliegue-Edge-Cloudflare-Workers-TanStack.md`, `Concepts/Exposicion-Segura-Cloudflare-Tunnel.md`, `Concepts/Integracion-Supabase-PgBouncer-FastAPI.md`, `Concepts/Flujo-Ramas-CI-CD-Produccion-Develop.md`, `Concepts/Patron-Monolito-Modular-FastAPI.md` y la pasarela `Entities/Servicio-OmniRoute-Gateway.md`.
2. **Referencias cruzadas**: Si el usuario indica *"Hazlo como en el proyecto X"*, consulta las fichas correspondientes en `OBSIDIAN VAULT/Entities/` y `OBSIDIAN VAULT/Concepts/` para respetar las decisiones de diseño adoptadas en otros desarrollos.
3. **Reutilización**: Reutiliza patrones existentes antes de inventar soluciones dispares.
4. **Documentar y Relacionar Obligatoriamente Nuevos Desarrollos e Implementaciones**:
   - Si se añade una nueva funcionalidad relevante, se toma una decisión arquitectónica (ADR), se agrega una integración cloud o se refactoriza un componente:
   - **DEBE documentarse e interrelacionarse de inmediato en `OBSIDIAN VAULT`**.
   - Seguir estrictamente la metodología Wiki-Base (`OBSIDIAN VAULT/SCHEMA.md`):
     - Conservar fuentes inmutables en `RAW/` si aplica.
     - Crear/actualizar fichas en `Entities/` o `Concepts/` con frontmatter YAML (`tags`, `updated: YYYY-MM-DD`, `fuentes`).
     - Sección `## Cross-references` con Wikilinks nativos `[[...]]`, enlazando a las notas conceptuales y SIEMPRE a `[[index]]`, `[[SCHEMA]]` y `[[log]]`.
     - Sección `## Fuentes`.
     - Regla del Vault Cerrado (enlaces de navegación markdown estrictamente internos al Vault; rutas del proyecto como texto plano en backticks).
     - Actualizar obligatoriamente `OBSIDIAN VAULT/index.md` y registrar la entrada en `OBSIDIAN VAULT/log.md`.
5. **Criterio de Síntesis**: No documentes cambios de código menores ni datos efímeros; enfócate en patrones transferibles y lecciones aprendidas.
