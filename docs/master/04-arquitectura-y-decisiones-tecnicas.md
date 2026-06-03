# 04 — Arquitectura y decisiones técnicas

## Arquitectura elegida

**Monolito modular con Clean Architecture pragmática**, expuesto al
cliente como un **API Gateway** que centraliza autenticación,
autorización y lógica de negocio.

```
┌────────────────────────────┐
│   Browser (React + TS)     │
│   - SSR con TanStack       │
│   - JWT en Authorization   │
└──────────────┬─────────────┘
               │
               │  HTTPS · /v1/...
               ▼
┌────────────────────────────────────────────────────────────────┐
│  buenchollo-api (FastAPI, monolito modular)                    │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  core/   config · database · security · request_id ·     │  │
│  │          rate_limit · security_headers · sentry · audit  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  modules/                                                │  │
│  │   ├─ deals/         (4 capas: domain · application · …) │  │
│  │   ├─ comments/      (mismo patrón)                       │  │
│  │   ├─ alerts/                                             │  │
│  │   ├─ notifications/                                      │  │
│  │   ├─ categories/                                         │  │
│  │   ├─ stores/                                             │  │
│  │   ├─ users/                                              │  │
│  │   ├─ products/                                           │  │
│  │   └─ telegram/                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬───────────────────────────────┘
                                 │
              ┌──────────────────┼─────────────────┬─────────────┐
              ▼                  ▼                 ▼             ▼
       ┌────────────┐    ┌─────────────┐   ┌────────────┐  ┌──────────┐
       │  Supabase  │    │ Amazon API  │   │   OpenAI   │  │ Telegram │
       │  (DB+Auth+ │    │  (Creators) │   │  (GPT-4o)  │  │   Bot    │
       │   Storage) │    │             │   │            │  │          │
       └────────────┘    └─────────────┘   └────────────┘  └──────────┘
```

## Por qué encaja con el tamaño del proyecto

### Por qué NO microservicios

La industria pasa por una fase de over-engineering donde casi
cualquier proyecto académico se presenta con microservicios
"porque es lo moderno". Para BuenCholloTech sería **incorrecto**:

| Razón | Detalle |
|---|---|
| **Equipo de 1 persona** | Microservicios multiplican el coste operativo (deploy, monitoring, debugging distribuido) sin que ningún equipo independiente lo justifique. |
| **Dominio cohesionado** | Los módulos de BuenChollo comparten 60% del modelo de datos (un deal está en feed, en alertas, en notificaciones, en favoritos, en votos). Separarlos en servicios implica replicación o llamadas cross-service constantes. |
| **Volumen pequeño** | El NAS Synology con un único contenedor maneja la carga sin problemas. No hay razón de rendimiento. |
| **Despliegue simple** | `docker-compose up -d` vs. orquestador Kubernetes con un servicio Mesh. Para un proyecto que vive en un NAS, la decisión es obvia. |

### Por qué SÍ monolito modular

| Beneficio | Cómo se materializa |
|---|---|
| **Refactorización barata** | Mover una función entre módulos es un import, no un endpoint nuevo + cliente HTTP. |
| **Transacciones simples** | Una sesión SQLAlchemy por request cubre toda la lógica de negocio. Sin sagas ni eventual consistency. |
| **Testing eficiente** | Tests unitarios mockeando 1 repositorio, no 5 servicios. |
| **Migración futura abierta** | Si crece, se puede extraer un servicio cuando la frontera de un módulo sea estable. Nada bloquea. La Clean Architecture pragmática facilita la extracción. |

Detalle completo en **[ADR-001](../adr/ADR-001-monolito-modular-fastapi.md)**.

### Por qué API Gateway

El frontend habla **exclusivamente** con FastAPI. Nunca consulta
Supabase directamente.

| Beneficio | Cómo |
|---|---|
| **Punto único de validación** | Autenticación JWT + autorización por rol se aplican en la entrada del backend. Sin lagunas. |
| **Sin lógica de negocio en el cliente** | El frontend no decide si un usuario puede ver un chollo: lo pregunta a la API y la API responde 200 o 403. |
| **Capa de seguridad coherente** | Rate limiting, audit log, security headers, request_id viven en un único sitio. |
| **Excepción documentada**: Storage | Subir imágenes pasa por Supabase Storage directamente desde el cliente (la alternativa — pasar binarios por FastAPI — multiplica latencia y coste). Aceptado en ADR-002. |

Detalle completo en **[ADR-002](../adr/ADR-002-migracion-baas-a-api-gateway.md)**.

## Organización de carpetas

```
buenchollo-app/                Monorepo (npm raíz con Husky)
├── buenchollo-api/            Backend FastAPI
│   └── app/
│       ├── core/              Infraestructura compartida
│       └── modules/<dominio>/ 4 capas: domain · application · infrastructure · api
├── buenchollo-web/            Frontend React + TS
│   └── src/
│       ├── routes/            file-based routing
│       ├── features/          features de dominio
│       ├── components/layout/ chrome compartido
│       ├── components/ui/     primitivos shadcn
│       ├── services/api/      cliente único hacia FastAPI
│       └── lib/               lógica pura CORE
├── docs/                      Esta documentación
└── .github/workflows/         CI con 4 jobs
```

Justificación detallada en [`docs/project/03-project-structure.md`](../project/03-project-structure.md).

## Separación de responsabilidades

### Backend: Clean Architecture pragmática por módulo

Cada módulo de dominio sigue el mismo patrón:

```
modules/deals/
├── domain/                  Modelos SQLAlchemy + excepciones de dominio
│   ├── models.py            Deal, DealVote, Favorite
│   ├── exceptions.py        DealNotFound, DuplicateDealError
│   └── utils.py             auto_slug
│
├── application/             Casos de uso · sin FastAPI ni SQLAlchemy
│   ├── deal_service.py      DealService (create, update, delete,
│   │                        process_vote, _check_external_id_unique)
│   └── cleaner_service.py   DealCleanerService (scheduler)
│
├── infrastructure/          Repositorio + adaptadores externos
│   └── repository.py        DealRepository (SQL real)
│
└── api/                     Router + schemas (sólo HTTP)
    ├── router.py            Endpoints con Depends(get_current_user)
    └── schemas.py           Pydantic in/out con max_length
```

**Reglas inviolables**:

1. **El dominio no depende de FastAPI ni de SQLAlchemy**. Las
   excepciones del dominio extienden `DomainError`, no
   `HTTPException`. El handler global las traduce.
2. **Los routers no contienen lógica**. Reciben HTTP, llaman al
   caso de uso, devuelven respuesta. El audit_log es la única cosa
   "extra" que hacen.
3. **El acceso a BD vive sólo en el repositorio**. Si un caso de
   uso necesita una query, la añade al repositorio.
4. **Composition root con `Depends`** ([ADR-007](../adr/ADR-007-di-fastapi-depends.md)):
   los servicios se construyen con su grafo de dependencias en una
   única función `get_deal_service(db)` que el router inyecta.

### Frontend: organización por features

Históricamente el frontend tenía estructura plana (`components/`,
`hooks/`, `services/`). En el sprint F5.1 se reorganizó por
features:

- `components/layout/` para el chrome compartido (Header, Footer,
  Logo, CategoriesDrawer).
- `components/ui/` para los primitivos shadcn (no se modifican).
- `features/<dominio>/components/` para los componentes específicos
  de cada feature.
- `features/<dominio>/hooks/` para los hooks de TanStack Query.

La regla: si un componente sirve sólo a una feature, vive con esa
feature.

## Dependencias externas

| Servicio | Para qué | Cómo se aísla |
|---|---|---|
| **Supabase Auth** | Google OAuth + JWT | `get_current_user` valida cada request; no se duplica lógica de auth |
| **Supabase Postgres** | Persistencia | SQLAlchemy async + asyncpg, pooler PgBouncer puerto 6543 ([ADR-004](../adr/ADR-004-persistencia-sqlalchemy-pgbouncer.md)) |
| **Supabase Storage** | Imágenes admin | Excepción a ADR-002, documentada |
| **Amazon Creators API** | Preview de productos | `AmazonProductClient` implementa el `Protocol ProductPreviewProvider` (DIP) |
| **OpenAI GPT-4o** | Copy + categorización | `OpenAIAssistant` implementa `Protocol AIEnricher` (DIP) |
| **Telegram Bot API** | Publicación al canal | `TelegramPostGenerator` con un cliente HTTP estricto |
| **Sentry SaaS** | Error tracking | `LoggingIntegration` + `before_send` con `request_id`. Sin `SENTRY_DSN` la app funciona igual |

**Patrón común**: cada dependencia externa vive en
`infrastructure/` detrás de un Protocol (en `domain/entities.py`). El
caso de uso depende del Protocol, no del cliente concreto. Cambiar
de proveedor (p.ej. Aliexpress en vez de Amazon) implica crear un
nuevo adapter, no tocar el caso de uso.

## Decisiones técnicas relevantes (ADRs)

| ADR | Decisión | Estado |
|---|---|---|
| [001](../adr/ADR-001-monolito-modular-fastapi.md) | Monolito Modular con FastAPI y Clean Architecture pragmática | Aceptado |
| [002](../adr/ADR-002-migracion-baas-a-api-gateway.md) | Migración de BaaS directo a API Gateway | Aceptado, cumplido 100% |
| [003](../adr/ADR-003-autenticacion-supabase-jwt.md) | Autenticación con Supabase Auth + validación JWT en backend | Aceptado |
| [004](../adr/ADR-004-persistencia-sqlalchemy-pgbouncer.md) | Persistencia con SQLAlchemy async + asyncpg + PgBouncer | Aceptado |
| [005](../adr/ADR-005-validacion-doble-frontera.md) | Validación en doble frontera con Zod y Pydantic | Aceptado |
| [006](../adr/ADR-006-rls-service-role.md) | Hardening de RLS y separación `anon` / `service_role` | Aceptado |
| [007](../adr/ADR-007-di-fastapi-depends.md) | Inyección de dependencias con `Depends` de FastAPI | Aceptado |
| [008](../adr/ADR-008-estrategia-calidad-testing.md) | Estrategia de calidad y testing 100/80/0 | Aceptado |
| [009](../adr/ADR-009-uso-de-ia-en-desarrollo.md) | Uso de IA como apoyo supervisado al desarrollo | Aceptado |

Cada ADR documenta el contexto del problema, las alternativas
consideradas, la decisión tomada y las consecuencias.

## Diagrama de despliegue

```
┌─────────────────────────────────────────────────┐
│   Internet                                      │
└────────────┬────────────────────────────────────┘
             │  HTTPS (TCP 443)
             ▼
┌─────────────────────────────────────────────────┐
│   Router doméstico (port forward)               │
└────────────┬────────────────────────────────────┘
             │  HTTPS interno
             ▼
┌─────────────────────────────────────────────────┐
│   NAS Synology DSM                              │
│   ├─ Reverse Proxy (HTTPS termina aquí)         │
│   │   └─ Let's Encrypt cert renovado auto       │
│   │                                             │
│   └─ Container Manager                          │
│       └─ Docker (buenchollo-api)                │
│           Python 3.11-slim                      │
│           Auto alembic upgrade head al arrancar │
└────────────┬────────────────────────────────────┘
             │
             │  Outbound HTTPS
             ▼
┌─────────────────────────────────────────────────┐
│  Servicios externos                             │
│  - Supabase                                     │
│  - Amazon Creators API                          │
│  - OpenAI                                       │
│  - Telegram Bot API                             │
│  - Sentry                                       │
└─────────────────────────────────────────────────┘
```

Detalle operativo en [`docs/project/08-deployment.md`](../project/08-deployment.md).

## Filosofía de fondo

> "Que el código resista uso real, no que parezca complejo."

Cada decisión se ha tomado optimizando por:

1. **Mantenibilidad** primero. Código que se entiende, se cambia, se
   prueba.
2. **Reversibilidad** segundo. Decisiones que no atan al proyecto a
   un proveedor o stack concreto sin necesidad.
3. **Simplicidad** tercero. KISS y YAGNI antes que cualquier
   "preparación para escala futura" especulativa.

Esto se traduce en decisiones explícitas que parecen "menos
sofisticadas" que las habituales en presentaciones académicas
(monolito vs microservicios; offset/limit vs cursor-based pagination;
Clean Architecture pragmática vs hexagonal puro), pero que son las
correctas para el contexto real del proyecto.
