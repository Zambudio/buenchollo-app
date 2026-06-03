# 📐 04 · Arquitectura y decisiones técnicas

> **TL;DR** · Monolito modular con Clean Architecture pragmática expuesto
> como API Gateway. **No microservicios** porque sería over-engineering
> para una persona, un dominio cohesionado y un NAS doméstico. Cada
> decisión clave vive en un ADR firmado.

---

## 🧭 Arquitectura de un vistazo

```
┌─────────────────────────────────┐
│  🌐 Browser (React 19 + TS)    │
│  - SSR con TanStack             │
│  - JWT en Authorization header  │
└──────────────┬──────────────────┘
               │
               │  🔒 HTTPS · /v1/...
               ▼
┌──────────────────────────────────────────────────────────┐
│  🐍 buenchollo-api  (FastAPI, monolito modular)         │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ core/                                              │ │
│  │  config · database · security · request_id        │ │
│  │  rate_limit · security_headers · sentry · audit   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ modules/  (1 carpeta por dominio · 4 capas)        │ │
│  │  ├─ deals/         🛒                              │ │
│  │  ├─ comments/      💬                              │ │
│  │  ├─ alerts/        🔔                              │ │
│  │  ├─ notifications/ 📬                              │ │
│  │  ├─ categories/    🏷️                              │ │
│  │  ├─ stores/        🏪                              │ │
│  │  ├─ users/         👤                              │ │
│  │  ├─ products/      📦                              │ │
│  │  └─ telegram/      ✈️                              │ │
│  └────────────────────────────────────────────────────┘ │
└────┬─────────────┬─────────────┬─────────────┬──────────┘
     │             │             │             │
     ▼             ▼             ▼             ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Supabase│  │  Amazon  │  │  OpenAI  │  │ Telegram │
│ DB+Auth+│  │  API     │  │  GPT-4o  │  │   Bot    │
│ Storage │  │          │  │          │  │          │
└─────────┘  └──────────┘  └──────────┘  └──────────┘
```

---

## 🤔 Por qué encaja este tamaño

### ❌ Por qué NO microservicios

> _Microservicios es una opción de escala, no un patrón de calidad._

<table>
<thead>
<tr><th>Razón</th><th>Detalle</th></tr>
</thead>
<tbody>
<tr>
  <td>👤 <strong>Equipo de 1 persona</strong></td>
  <td>Microservicios multiplican el coste operativo (deploy, monitoring, debugging distribuido) sin que ningún equipo independiente lo justifique.</td>
</tr>
<tr>
  <td>🔗 <strong>Dominio cohesionado</strong></td>
  <td>Los módulos de BuenChollo comparten ~60% del modelo de datos. Separarlos en servicios implica replicación o llamadas cross-service constantes.</td>
</tr>
<tr>
  <td>📊 <strong>Volumen pequeño</strong></td>
  <td>Un NAS Synology con un único contenedor maneja la carga sin problemas. No hay justificación de rendimiento.</td>
</tr>
<tr>
  <td>⚙️ <strong>Despliegue simple</strong></td>
  <td><code>docker-compose up -d</code> vs. Kubernetes con service mesh. Para un NAS doméstico, la decisión es obvia.</td>
</tr>
</tbody>
</table>

### ✅ Por qué SÍ monolito modular

| Beneficio | Cómo se materializa |
|---|---|
| 🔧 **Refactor barato** | Mover una función entre módulos es un `import`, no un endpoint nuevo + cliente HTTP. |
| 💾 **Transacciones simples** | Una sesión SQLAlchemy por request cubre toda la lógica. Sin sagas ni eventual consistency. |
| 🧪 **Testing eficiente** | Tests mockean 1 repositorio, no 5 servicios. |
| 🚪 **Migración futura abierta** | Si crece, se puede extraer un servicio cuando la frontera de un módulo sea estable. Nada bloquea. |

📚 Detalle completo: [**ADR-001**](../adr/ADR-001-monolito-modular-fastapi.md).

---

## 🚪 Por qué API Gateway

El frontend habla **exclusivamente** con FastAPI. Nunca consulta
Supabase directamente.

```
   ❌ ANTES (BaaS directo desde el cliente)
   ┌─────────┐                   ┌──────────┐
   │ Browser │ ─────fetch───────▶│ Supabase │
   └─────────┘                   └──────────┘
   ↑ lógica en cliente, sin validación uniforme

   ✅ AHORA (API Gateway)
   ┌─────────┐    ┌─────────┐    ┌──────────┐
   │ Browser │───▶│ FastAPI │───▶│ Supabase │
   └─────────┘    └─────────┘    └──────────┘
   ↑ punto único de auth + autorización + rate limit
```

| Beneficio | Cómo |
|---|---|
| 🔒 **Punto único de validación** | Auth JWT + autorización por rol aplicados en la entrada. Sin lagunas. |
| 🧠 **Sin lógica de negocio en el cliente** | El frontend no decide si un usuario puede ver un chollo: pregunta a la API y responde 200/403. |
| 🛡️ **Capa de seguridad coherente** | Rate limiting, audit log, security headers, request_id en un único sitio. |
| ⚠️ **Excepción documentada**: Storage | Subir imágenes va directo a Supabase Storage desde el cliente — aceptado en [ADR-002](../adr/ADR-002-migracion-baas-a-api-gateway.md). |

📚 Detalle completo: [**ADR-002**](../adr/ADR-002-migracion-baas-a-api-gateway.md).

---

## 🏗️ Separación de responsabilidades

### 🐍 Backend: Clean Architecture pragmática por módulo

```
modules/deals/
├── 📦 domain/                  ← Modelos SQLAlchemy + excepciones
│   ├── models.py               Deal, DealVote, Favorite
│   ├── exceptions.py           DealNotFound, DuplicateDealError
│   └── utils.py                auto_slug
│
├── 🧠 application/             ← Casos de uso, sin FastAPI ni SQL
│   ├── deal_service.py         DealService (create, update, delete,
│   │                            process_vote, _check_external_id_unique)
│   └── cleaner_service.py      DealCleanerService (scheduler)
│
├── 🔌 infrastructure/          ← Repositorios + adaptadores externos
│   └── repository.py           DealRepository (queries SQL)
│
└── 🌐 api/                     ← Routers + schemas — sólo HTTP
    ├── router.py               Endpoints con Depends(get_current_user)
    └── schemas.py              Pydantic in/out con max_length
```

#### 📜 Reglas inviolables

> 🔴 **1.** El **dominio no depende** de FastAPI ni de SQLAlchemy.
> Las excepciones extienden `DomainError`, no `HTTPException`.
> El handler global las traduce.

> 🔴 **2.** Los **routers no contienen lógica**. Reciben HTTP, llaman
> al caso de uso, devuelven respuesta.

> 🔴 **3.** El **acceso a BD vive sólo en el repositorio**. Si un caso
> de uso necesita una query, la añade al repositorio.

> 🔴 **4.** **Composition root con `Depends`** ([ADR-007](../adr/ADR-007-di-fastapi-depends.md)):
> los servicios se construyen con su grafo de dependencias en una
> única función `get_deal_service(db)`.

---

### ⚛️ Frontend: organización por features

Históricamente el frontend tenía estructura plana
(`components/`, `hooks/`, `services/`). En el sprint **F5.1** se
reorganizó por features:

```
src/
├── components/
│   ├── layout/          ← Chrome compartido (Header, Footer, Logo, Drawer)
│   └── ui/              ← Primitivos shadcn (no se modifican)
│
├── features/
│   ├── deals/
│   │   └── components/  ← DealCard, Comments, ShareBox
│   ├── admin/
│   │   └── hooks/       ← useAdminStats
│   ├── notifications/
│   │   └── hooks/       ← useUnreadNotifications, useNotificationsList
│   └── telegram/
│       └── components/  ← TelegramPanel
│
├── routes/              ← File-based routing
├── services/api/        ← Único cliente HTTP
├── lib/                 ← Lógica pura (CORE)
└── hooks/               ← useAuth global
```

📜 **Regla**: si un componente sirve sólo a una feature, vive con esa feature.

---

## 🔌 Dependencias externas

Todas las dependencias externas viven en `infrastructure/` detrás de un
**Protocol** (en `domain/entities.py`). El caso de uso depende del
Protocol, no del cliente concreto.

```python
# domain/entities.py
class ProductPreviewProvider(Protocol):
    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None: ...

# application/preview_product_from_url.py
class PreviewProductFromUrlUseCase:
    def __init__(self, provider: ProductPreviewProvider, enricher: AIEnricher):
        ...
```

Cambiar de proveedor (p.ej. Aliexpress en vez de Amazon) implica
**crear un nuevo adapter**, no tocar el caso de uso.

| Servicio | Para qué | Aislamiento |
|---|---|---|
| **Supabase Auth** | Google OAuth + JWT | `get_current_user` valida cada request |
| **Supabase Postgres** | Persistencia | SQLAlchemy async + asyncpg, pooler PgBouncer ([ADR-004](../adr/ADR-004-persistencia-sqlalchemy-pgbouncer.md)) |
| **Supabase Storage** | Imágenes admin | Excepción documentada a ADR-002 |
| **Amazon Creators API** | Preview de productos | `AmazonProductClient` implementa `ProductPreviewProvider` |
| **OpenAI GPT-4o** | Copy + categorización | `OpenAIAssistant` implementa `AIEnricher` |
| **Telegram Bot API** | Publicación al canal | `TelegramPostGenerator` |
| **Sentry SaaS** | Error tracking | `LoggingIntegration` + `before_send` con `request_id` |

---

## 📋 Decisiones técnicas relevantes — los 9 ADRs

<table>
<thead>
<tr><th>#</th><th>Decisión</th><th>Estado</th></tr>
</thead>
<tbody>
<tr><td><a href="../adr/ADR-001-monolito-modular-fastapi.md">001</a></td><td>📐 Monolito Modular con FastAPI y Clean Architecture pragmática</td><td>✅ Aceptado</td></tr>
<tr><td><a href="../adr/ADR-002-migracion-baas-a-api-gateway.md">002</a></td><td>🚪 Migración de BaaS directo a API Gateway</td><td>✅ Cumplido 100%</td></tr>
<tr><td><a href="../adr/ADR-003-autenticacion-supabase-jwt.md">003</a></td><td>🔐 Autenticación con Supabase Auth + validación JWT en backend</td><td>✅ Aceptado</td></tr>
<tr><td><a href="../adr/ADR-004-persistencia-sqlalchemy-pgbouncer.md">004</a></td><td>💾 Persistencia con SQLAlchemy async + asyncpg + PgBouncer</td><td>✅ Aceptado</td></tr>
<tr><td><a href="../adr/ADR-005-validacion-doble-frontera.md">005</a></td><td>🛡️ Validación en doble frontera con Zod y Pydantic</td><td>✅ Aceptado</td></tr>
<tr><td><a href="../adr/ADR-006-rls-service-role.md">006</a></td><td>🔒 Hardening de RLS y separación anon / service_role</td><td>✅ Aceptado</td></tr>
<tr><td><a href="../adr/ADR-007-di-fastapi-depends.md">007</a></td><td>🧬 Inyección de dependencias con Depends de FastAPI</td><td>✅ Aceptado</td></tr>
<tr><td><a href="../adr/ADR-008-estrategia-calidad-testing.md">008</a></td><td>🧪 Estrategia de calidad y testing 100/80/0</td><td>✅ Aceptado</td></tr>
<tr><td><a href="../adr/ADR-009-uso-de-ia-en-desarrollo.md">009</a></td><td>🤖 Uso de IA como apoyo supervisado al desarrollo</td><td>✅ Aceptado</td></tr>
</tbody>
</table>

---

## 🚀 Diagrama de despliegue

```
┌─────────────────────────────────────────────────┐
│  🌐  Internet                                   │
└────────────────┬────────────────────────────────┘
                 │  🔒 HTTPS (TCP 443)
                 ▼
┌─────────────────────────────────────────────────┐
│  🏠  Router doméstico (port forward)            │
└────────────────┬────────────────────────────────┘
                 │  HTTPS interno
                 ▼
┌─────────────────────────────────────────────────┐
│  💾  NAS Synology DSM                           │
│                                                 │
│  ┌─ 🔄 Reverse Proxy (HTTPS termina aquí)      │
│  │  └─ 🔐 Let's Encrypt cert renovado auto    │
│  │                                              │
│  └─ 📦 Container Manager                       │
│      └─ 🐳 Docker (buenchollo-api)            │
│           python:3.11-slim                     │
│           ⚙️ Auto `alembic upgrade head`       │
└────────────────┬────────────────────────────────┘
                 │  Outbound HTTPS
                 ▼
┌─────────────────────────────────────────────────┐
│  ☁️  Servicios externos                         │
│  - Supabase                                     │
│  - Amazon Creators API                          │
│  - OpenAI                                       │
│  - Telegram Bot API                             │
│  - Sentry                                       │
└─────────────────────────────────────────────────┘
```

📚 Operativa de despliegue: [`docs/project/08-deployment.md`](../project/08-deployment.md).

---

## 🎯 Filosofía de fondo

> _"Que el código resista uso real, no que parezca complejo."_

Cada decisión se ha tomado optimizando por:

| Prioridad | Significa |
|---|---|
| 🥇 **Mantenibilidad** | Código que se entiende, se cambia, se prueba |
| 🥈 **Reversibilidad** | Decisiones que no atan a un proveedor o stack sin necesidad |
| 🥉 **Simplicidad** | KISS y YAGNI antes que "preparación para escala futura" especulativa |

Esto se traduce en decisiones explícitas que parecen "menos sofisticadas"
que las habituales en presentaciones académicas — y precisamente por
eso son **las correctas** para el contexto real del proyecto.

---

<p align="center">
  <a href="03-analisis-funcional.md">← Anterior: Análisis funcional</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="05-buenas-practicas-y-principios-de-diseno.md">Siguiente: Buenas prácticas →</a>
</p>
