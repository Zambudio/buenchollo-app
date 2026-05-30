<p align="center">
  <img src="buenchollo-web/src/assets/logo-bctech.png" alt="BuenCholloTech" height="140">
</p>

<h1 align="center">BuenCholloTech</h1>

<p align="center">
  <a href="https://github.com/Zambudio/buenchollo-app/actions/workflows/ci.yml">
    <img alt="CI" src="https://github.com/Zambudio/buenchollo-app/actions/workflows/ci.yml/badge.svg?branch=main">
  </a>
  <a href="https://github.com/Zambudio/buenchollo-app/releases/tag/v1.0.0-tfm">
    <img alt="release" src="https://img.shields.io/badge/release-v1.0.0--tfm-22d3ee">
  </a>
  <img alt="python" src="https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="typescript" src="https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white">
</p>

Plataforma para publicar, gestionar y automatizar chollos tecnológicos.
Proyecto dual: producto personal en evolución continua + Trabajo Final del
Máster en Desarrollo con IA 2025.

---

## Arquitectura

**Monolito Modular con Clean Architecture pragmática** ([ADR-001](docs/adr/ADR-001-monolito-modular-fastapi.md))
y **patrón API Gateway** ([ADR-002](docs/adr/ADR-002-migracion-baas-a-api-gateway.md)):
el frontend nunca llama a la BD directamente; toda la lógica de negocio vive
en FastAPI.

```mermaid
flowchart LR
    Browser["🌐 Browser<br/>(React + TS SPA)"]

    subgraph nas ["🏠 NAS Synology — Docker"]
        API["🐍 FastAPI<br/>buenchollo-api"]
    end

    subgraph supa ["☁️ Supabase"]
        Auth["🔑 Auth<br/>(Google OAuth + email)"]
        DB[("🐘 PostgreSQL<br/>vía PgBouncer :6543")]
        Storage["📦 Storage<br/>(deal-images)"]
    end

    Browser -- "JWT Bearer<br/>(HTTPS)" --> API
    Browser -. "login / refresh" .-> Auth
    Browser -. "upload imágenes<br/>(excepción ADR-002)" .-> Storage

    API -- "service_role key<br/>SQLAlchemy async" --> DB
    API -- "valida JWT<br/>supabase.auth.get_user" --> Auth
    API -- "scraping productos" --> Amazon["🛒 Amazon<br/>Creators API"]
    API -- "categorización + copy" --> OpenAI["🤖 OpenAI API"]
    API -- "publicación de chollos" --> Telegram["✈️ Telegram Bot API"]

    classDef ext fill:#1e293b,stroke:#0ea5e9,color:#e2e8f0
    classDef internal fill:#0f172a,stroke:#22d3ee,color:#e2e8f0
    class Auth,DB,Storage,Amazon,OpenAI,Telegram ext
    class API,Browser internal
```

### Filosofía arquitectónica (6 reglas inviolables)

1. **El router sólo habla HTTP** — recibe request, llama al caso de uso,
   devuelve respuesta. Sin SQL ni lógica de negocio.
2. **Casos de uso en `application/`** — toda la orquestación va ahí,
   independiente de FastAPI y de la BD.
3. **El repositorio es el único que toca la BD** — ningún `session.execute()`
   fuera de `infrastructure/`.
4. **Módulos sin acoplamiento cruzado** — lo compartido va a `core/`.
5. **Un proveedor externo = un adaptador en `infrastructure/`** — añadir
   AliExpress es crear `aliexpress_client.py` y registrarlo. Nada más cambia.
6. **El frontend nunca habla con la BD directamente** — excepción documentada
   para Supabase Auth y Storage ([ADR-002](docs/adr/ADR-002-migracion-baas-a-api-gateway.md)).

### Decisiones arquitectónicas (ADRs)

| # | Decisión | Estado |
|---|---|---|
| [ADR-001](docs/adr/ADR-001-monolito-modular-fastapi.md) | Monolito Modular con FastAPI y Clean Architecture pragmática | Aceptado (refinado por ADR-002) |
| [ADR-002](docs/adr/ADR-002-migracion-baas-a-api-gateway.md) | Migración de BaaS directo a API Gateway | Aceptado · cumplido al 100% |
| [ADR-003](docs/adr/ADR-003-autenticacion-supabase-jwt.md) | Autenticación con Supabase Auth + validación de JWT en backend | Aceptado |
| [ADR-004](docs/adr/ADR-004-persistencia-sqlalchemy-pgbouncer.md) | Persistencia con SQLAlchemy async + asyncpg + PgBouncer | Aceptado |
| [ADR-005](docs/adr/ADR-005-validacion-doble-frontera.md) | Validación en doble frontera con Zod y Pydantic | Aceptado |
| [ADR-006](docs/adr/ADR-006-rls-service-role.md) | Hardening de RLS y separación `anon` / `service_role` | Aceptado |
| [ADR-007](docs/adr/ADR-007-di-fastapi-depends.md) | Inyección de dependencias con `Depends` de FastAPI | Aceptado |

---

## Estructura del monorepo

```
buenchollo-app/
├── buenchollo-api/             # Backend FastAPI
│   ├── app/
│   │   ├── core/               # config, database, security, logging
│   │   ├── modules/            # 1 carpeta por dominio (deals, products, …)
│   │   │   └── <modulo>/
│   │   │       ├── domain/         # modelos SQLAlchemy + reglas puras
│   │   │       ├── application/    # casos de uso (services)
│   │   │       ├── infrastructure/ # repositorios + adaptadores externos
│   │   │       └── api/            # router FastAPI + schemas Pydantic
│   │   └── tests/              # unitarios + integración
│   ├── alembic/                # migraciones versionadas
│   └── supabase/migrations/    # histórico SQL pre-Alembic
│
├── buenchollo-web/             # Frontend React + TS
│   └── src/
│       ├── routes/             # TanStack Router file-based
│       ├── components/
│       │   ├── layout/         # Header, Footer, Logo, CategoriesDrawer
│       │   └── ui/             # shadcn primitives
│       ├── features/           # 1 carpeta por dominio (deals, admin, notifications, telegram)
│       │   └── <dominio>/
│       │       ├── components/ # componentes específicos del dominio
│       │       └── hooks/      # hooks con TanStack Query
│       ├── services/api/       # apiClient + servicios por dominio
│       ├── lib/                # query-client, format, errors, constants, validation
│       ├── hooks/              # useAuth y similares
│       └── integrations/       # supabase client + lovable
│
├── .github/
│   ├── workflows/ci.yml        # pytest + tsc + eslint en cada push/PR
│   └── dependabot.yml          # updates semanales agrupados
│
└── docs/                       # ADRs + planes + diagramas
    ├── adr/                    # 7 ADRs (arriba)
    ├── PLAN_ARQUITECTURA.md    # plan vivo de hardening
    ├── SMOKE_TEST.md           # checklist manual pre-release
    ├── SUPABASE_SETUP.md       # esquema BD + configuración
    └── LAUNCH_CHECKLIST.md     # pre-flight para producción
```

| Subrepo | Stack | Rol |
|---|---|---|
| `buenchollo-api/` | Python 3.11 · FastAPI · SQLAlchemy 2.x · asyncpg · Pydantic v2 | API Gateway — toda la lógica de negocio |
| `buenchollo-web/` | React 18 · TypeScript · Vite · TanStack Router · Zod · shadcn/Tailwind | Frontend — sólo habla con buenchollo-api |
| `docs/` | Markdown | ADRs, planes y documentación técnica |

---

## Prerequisitos

| Herramienta | Versión | Necesario para |
|---|---|---|
| Git | cualquiera | clonar el repo |
| Python | **3.11+** | backend |
| Node.js | 18+ | frontend |
| pnpm | 8+ | gestión de paquetes frontend (`npm install -g pnpm`) |
| Docker + Docker Compose | cualquiera | despliegue en NAS / producción |

---

## Setup desde cero

### 1. Clonar el repositorio

```bash
git clone https://github.com/Zambudio/buenchollo-app.git
cd buenchollo-app
```

### 2. Backend (`buenchollo-api`)

```bash
cd buenchollo-api

# Crear entorno virtual
python -m venv .venv

# Activar (Linux/Mac)
source .venv/bin/activate
# Activar (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt   # tests

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales (ver buenchollo-api/README.md)

# Arrancar en modo desarrollo
uvicorn app.main:app --reload
```

API disponible en `http://localhost:8000` · OpenAPI en `http://localhost:8000/docs`.

### 3. Frontend (`buenchollo-web`)

En una terminal nueva:

```bash
cd buenchollo-web

# Instalar dependencias
pnpm install

# Configurar variables de entorno
cp .env.example .env.local
# Editar con la URL pública del backend y las keys de Supabase (anon)

# Arrancar en modo desarrollo
pnpm dev
```

Web disponible en `http://localhost:8080` (o el puerto que indique Vite).

---

## Despliegue en producción (NAS Synology)

Ver instrucciones detalladas en
[`buenchollo-api/DEPLOY_NAS.md`](buenchollo-api/DEPLOY_NAS.md).

Flujo resumido:

1. `git pull` en el NAS (o esperar a que SynologyDrive sincronice).
2. `docker-compose build --no-cache && docker-compose up -d`.
3. Verificar: `https://[tu-ddns]:8000/health`.
4. Revisar checklist completa en [`docs/LAUNCH_CHECKLIST.md`](docs/LAUNCH_CHECKLIST.md).

---

## Tests

**Suite backend: 87 tests** (78 unitarios + 9 de integración).

```bash
cd buenchollo-api
python -m pytest                          # toda la suite (requiere Postgres real para los de integración)
python -m pytest -m "not integration"     # sólo unitarios (lo que corre el CI)
python -m pytest app/tests/test_deal_service.py -v   # un fichero concreto
```

Los unitarios mockean Supabase, Amazon y la BD; los de integración usan
una BD Postgres real (marcador `@pytest.mark.integration`). El workflow
de GitHub Actions ejecuta únicamente los unitarios; los de integración
se validan en local antes de cada release (ver
[`docs/SMOKE_TEST.md`](docs/SMOKE_TEST.md)).

**Frontend**:

```bash
cd buenchollo-web
npm run typecheck       # tsc --noEmit con strict mode
npm run lint            # eslint con reglas estrictas
```

---

## Documentación técnica

| Documento | Contenido |
|---|---|
| [`buenchollo-api/README.md`](buenchollo-api/README.md) | Setup detallado del backend, API reference, variables de entorno |
| [`buenchollo-web/README.md`](buenchollo-web/README.md) | Setup detallado del frontend, variables de entorno |
| [`buenchollo-api/DEPLOY_NAS.md`](buenchollo-api/DEPLOY_NAS.md) | Despliegue en NAS Synology con Docker |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Estado vivo del proyecto, deuda técnica y métricas |
| [`docs/PLAN_ARQUITECTURA.md`](docs/PLAN_ARQUITECTURA.md) | Plan vivo de hardening arquitectónico (F1–F7 completado) |
| [`docs/QUALITY.md`](docs/QUALITY.md) | Estrategia de testing, coverage estratégico, métricas y defensa TFM |
| [`docs/SMOKE_TEST.md`](docs/SMOKE_TEST.md) | Checklist manual exhaustivo pre-release |
| [`docs/adr/`](docs/adr/) | Decisiones arquitectónicas (ADRs) firmadas y datadas |
| [`docs/SUPABASE_SETUP.md`](docs/SUPABASE_SETUP.md) | Esquema de BD y configuración de Supabase |
| [`docs/LAUNCH_CHECKLIST.md`](docs/LAUNCH_CHECKLIST.md) | Checklist pre-despliegue de producción |
| [`CLAUDE.md`](CLAUDE.md) | Instrucciones permanentes para asistentes de IA en este repo |

---

*Desarrollado por Pedro Zambudio · Máster en Desarrollo con IA 2025*
