# CLAUDE.md — BuenCholloTech

Instrucciones permanentes para Claude Code en este proyecto.
Este archivo se carga automáticamente en cada conversación.

---

## Rol y actitud

Actúa siempre como desarrollador senior, arquitecto de software y revisor técnico.
Respuestas concisas y directas. Sin relleno, sin recapitular lo que acaba de decir el usuario.
Si falta contexto para tomar una decisión, pregunta antes de inventar.
Ante varias opciones válidas, elige la más simple y mantenible.

---

## Contexto del proyecto

**BuenCholloTech** es una plataforma para publicar, gestionar y automatizar chollos tecnológicos.
Proyecto dual: uso personal + Trabajo Final de Máster (TFM) — las decisiones técnicas deben ser defendibles académicamente.

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

---

## Arquitectura del backend (`buenchollo-api/`)

```
app/
├── core/          # config, database, security, logging (compartido)
└── modules/
    ├── deals/
    │   ├── domain/        # modelos SQLAlchemy (Deal)
    │   ├── application/   # casos de uso, cleaner_service
    │   ├── infrastructure/# repositorios, adapters externos
    │   └── api/           # router FastAPI, schemas Pydantic
    ├── products/          # preview Amazon (DIP con Protocols)
    ├── categories/
    ├── stores/
    └── users/             # /auth/me, Profile model
```

**Flujo de dependencias**: `api → application → domain ← infrastructure`

El dominio no depende de FastAPI, SQLAlchemy, ni ningún framework externo.

---

## Principios obligatorios

### 1. Arquitectura
- Respetar ADR-001 y ADR-002. No proponer microservicios sin justificación fuerte.
- Los routers no contienen lógica de negocio.
- La lógica va en casos de uso (`application/`).
- Las integraciones externas van en `infrastructure/`.

### 2. Código
- SOLID (especialmente SRP y DIP), DRY, KISS, YAGNI.
- Sin sobreingeniería. Sin abstracciones para un único uso.
- No añadir manejo de errores, validaciones ni features que no se han pedido.
- No añadir docstrings, comentarios ni type hints en código que no se ha tocado.

### 3. FastAPI
- Schemas Pydantic separados de modelos ORM.
- Configuración centralizada en `core/config.py` (pydantic-settings).
- `require_admin` en `core/security.py` — consulta directa a `user_roles`, sin `has_role()`.
- `SUPABASE_KEY` debe ser siempre la `service_role key`.
- Conexión BD: `statement_cache_size=0` obligatorio para compatibilidad con PgBouncer.

### 4. Base de datos
- SQLAlchemy async con asyncpg.
- UUIDs: `Uuid(as_uuid=False)` en todos los modelos.
- FK entre módulos: importar el modelo destino en el modelo origen para que SQLAlchemy resuelva las relaciones.
- No mezclar modelos ORM con schemas de API.

### 5. Frontend
- Toda llamada HTTP pasa por `src/services/api/client.ts` (apiClient).
- El token Bearer se adjunta automáticamente desde `supabase.auth.getSession()`.
- No hacer llamadas directas a `supabase.from()` salvo Storage (excepción aprobada).

### 6. Seguridad
- Sin secretos hardcodeados. Todo en `.env`.
- No exponer errores internos al usuario final.
- Validar entradas en la frontera del sistema.

### 7. Testing
- Unitarios para lógica pura (mockear Amazon, OpenAI, Telegram).
- Integración para endpoints y repositorios importantes.
- E2E solo para flujos críticos.
- Tests repetibles, aislados, sin depender de servicios externos reales.

---

## Forma de trabajar

- **Cambios grandes**: analizar, proponer plan y esperar confirmación antes de escribir código.
- **Cambios pequeños**: ejecutar directamente.
- **Al terminar**: indicar archivos modificados, cómo probar, y riesgos o pendientes si los hay.
- **Refactoring**: no hacerlo de forma masiva sin explicar impacto. No cambiar contratos de API sin avisar.
- **Documentación**: actualizar README o docs si cambia el uso del sistema. Proponer ADR cuando haya decisión técnica relevante.
- **No romper** funcionalidad existente ni tests existentes.
- **Recordatorio de deuda técnica**: al **cambiar de tarea** (cuando se cierra algo y se pasa a otra cosa), recuérdame brevemente que hay deuda técnica pendiente y apunta a [`docs/project/10-technical-debt.md`](docs/project/10-technical-debt.md). Mantén ese registro al día: al cerrar un item, bórralo de ahí y anota el cierre en `PROJECT_STATUS.md`.
- **Recordatorio de plan de optimización**: igual que la deuda técnica, al **cambiar de tarea** recuérdame brevemente que hay un plan de rendimiento pendiente (NAS sin workers, cache Cloudflare, futura migración de infra) en [`OPTIMIZACION_PLAN.md`](OPTIMIZACION_PLAN.md). Deliberadamente no se ejecuta hasta tener base de usuarios real — no proponer migrar infraestructura ni asumir gasto mensual sin que el usuario lo pida explícitamente. Mantenlo al día igual que la deuda técnica.

### Flujo de ramas (web en producción)

- La web está **en producción** en `buenchollotech.com`. `main` = producción; `develop` = integración/pruebas.
- Ciclo permanente: trabajar en `develop` → push (genera *preview* en Cloudflare) → validar → `merge develop → main` (deploy a producción). **Nunca** commits directos a `main`.
- **Cambios de dependencias / framework**: solo en `develop` y con CI en verde antes de tocar `main` (un bump a `main` sin verificar puede romper el build de producción).
- **Cambios de panel Cloudflare / `.env` del NAS**: se aplican directos a prod; cada uno con su verificación y rollback. El `.env` del NAS está **excluido del sync de SynologyDrive** (independiente del `.env` local).
- Ante un **aspecto crítico** (entorno roto, CI/hooks fallando, datos/seguridad en riesgo): **parar y resolverlo** antes de avanzar; no ofrecer "seguir o arreglar".

### Memoria y contexto

Las **normas de trabajo y la memoria del proyecto** viven **dentro del repo** en [`.claude/memory/`](.claude/memory/) (versionadas). El índice [`.claude/memory/MEMORY.md`](.claude/memory/MEMORY.md) lista cada nota: forma de trabajo iterativa, no continuar con lo crítico, deps solo en `develop`, método de revisión/auditoría, estado del proyecto, etc. **Consúltalas al inicio de cada sesión** y mantenlas al día (una nota por fichero, con frontmatter; actualiza también el índice).

La guía operativa **viva** de la infraestructura (Cloudflare, túnel, hardening) está en [`docs/guides/Cloudflare.md`](docs/guides/Cloudflare.md); úsala y mantenla al día al tocar infraestructura.

---

## Workflows disponibles (`.agents/workflows/`)

Úsalos como guía cuando aplique:

| Workflow | Cuándo usarlo |
|---|---|
| `crear-feature-siguiendo-clean-architecture.md` | Al implementar cualquier feature nueva |
| `refactorizar-sin-romper-funcionalidad.md` | Al mejorar código existente |
| `disenar-mejorar-tests.md` | Al escribir o revisar tests |
| `documentar-decision-tecnica-pfmaster.md` | Al crear un ADR o documento técnico para el TFM |
| `auditar-arquitectura.md` | Al revisar el estado general del proyecto |
| `revision-seguridad-basica.md` | Al revisar seguridad de un módulo o feature |

---

## Estado actual (2026-06-14)

- **Web en producción** en `https://buenchollotech.com` (frontend TanStack Start SSR como **Cloudflare Worker**; deploy automático al hacer push a `main` vía Workers Builds).
- **API** FastAPI en el NAS Synology, expuesta en `https://api.buenchollotech.com` vía **Cloudflare Tunnel** (sin abrir puertos, sin DDNS). `APP_ENV=production`, CORS cerrado al dominio.
- **Cloudflare endurecido**: TLS Full (strict) + HSTS, redirect `www`→raíz, WAF + rate limiting + Bot Fight Mode. Detalle y bitácora en [`docs/guides/Cloudflare.md`](docs/guides/Cloudflare.md).
- Login Google (Supabase) OK · Panel admin funcionando · CI de `main` en verde · flujo `main`/`develop` operativo.
- **Deuda técnica**: registro vivo y completo en [`docs/project/10-technical-debt.md`](docs/project/10-technical-debt.md). Lo más urgente: cifras de tests por reconciliar (TD-01) y `CORS_ORIGINS` que exige JSON array en vez de CSV (TD-02).
