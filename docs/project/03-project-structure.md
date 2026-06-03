# 🗂️ 03 · Estructura del proyecto

> **TL;DR** · Monorepo con backend FastAPI + frontend React + carpeta
> `docs/` dual (operativa + académica). Backend con Clean Architecture
> pragmática por módulo. Frontend organizado por features. Reglas
> claras de **dónde añadir cada cosa**.

---

## 🌳 Monorepo

```
buenchollo-app/
│
├── 🐍 buenchollo-api/         Backend FastAPI · Python
├── ⚛️ buenchollo-web/         Frontend React · TypeScript · Vite
│
├── 📚 docs/                   Documentación
│   ├── project/               ← Operativa del repo (este árbol)
│   ├── master/                ← Bloque académico
│   ├── adr/                   ← Decisiones arquitectónicas
│   ├── reference/             ← Referencia técnica densa
│   └── archive/               ← Histórico preservado
│
├── ⚙️ .github/
│   ├── workflows/ci.yml       ← CI (backend + frontend + e2e + security-audit)
│   └── dependabot.yml         ← Updates semanales agrupados
│
├── 🪝 .husky/                 Quality gates locales (pre-commit, pre-push)
│
├── 📄 package.json            Root: sólo Husky devDependency
├── 📄 README.md
├── 📄 CLAUDE.md               Instrucciones para asistentes IA
├── 📄 PROJECT_STATUS.md       Bitácora viva (CHANGELOG en prosa)
└── 📄 SECURITY.md             Política de divulgación responsable
```

---

## 🐍 Backend — `buenchollo-api/`

> **Estilo**: Clean Architecture **pragmática**, no purista.
> Una carpeta por módulo de dominio con **4 capas dentro**.

```
app/
├── 🧠 core/                       Infraestructura compartida
│   ├── config.py                  Settings (pydantic-settings)
│   ├── database.py                Engine SQLAlchemy async + get_db
│   ├── security.py                get_current_user, require_admin
│   ├── exceptions.py              Jerarquía DomainError
│   ├── request_id.py              ContextVar + middleware
│   ├── rate_limit.py              SlowAPI con X-Forwarded-For
│   ├── security_headers.py        CSP, X-Frame, HSTS en prod
│   ├── sentry.py                  LoggingIntegration + before_send
│   ├── audit.py                   Audit log para acciones admin
│   ├── health.py                  /health y /health/ready
│   └── logging.py                 JSON con request_id
│
├── 🧱 modules/                    1 carpeta por dominio
│   └── <dominio>/
│       ├── 📦 domain/             Modelos SQLAlchemy + excepciones
│       ├── 🎯 application/        Servicios / casos de uso
│       ├── 🔌 infrastructure/     Repositorios + clientes externos
│       └── 🌐 api/                Router FastAPI + schemas Pydantic
│
├── 🛠️ alembic/                    Migraciones versionadas
├── 📜 supabase/migrations/        Histórico SQL pre-Alembic
└── 🧪 tests/                      Unitarios + integración (marker)
```

### 🧱 Módulos de dominio

```
deals · comments · alerts · notifications · categories ·
stores · users · products · telegram
```

### 🔄 Flujo de dependencias

```
       ┌───────┐
       │  api  │
       └───┬───┘
           ▼
     ┌────────────┐
     │application │
     └─────┬──────┘
           ▼
     ┌──────────┐         ┌────────────────┐
     │  domain  │ ◀────── │ infrastructure │
     └──────────┘         └────────────────┘
```

> 🔴 **Regla**: el dominio **no depende** de FastAPI ni SQLAlchemy.

### 📜 Reglas de los routers

> Los routers **sólo hablan HTTP**. Toda la lógica vive en `application/`.

📚 Justificación completa: [ADR-001](../adr/ADR-001-monolito-modular-fastapi.md).

---

## ⚛️ Frontend — `buenchollo-web/`

> **Estilo**: organización **por features** (no por tipos de archivo).

```
src/
├── 📁 routes/                     TanStack Router file-based
│   ├── __root.tsx                 Providers (QueryClient, Auth, Toaster)
│   ├── index.tsx                  🏠 Home (feed infinito + populares)
│   ├── chollo.$slug.tsx           📄 Detalle
│   ├── explorar.tsx               🔍 Búsqueda
│   ├── alertas.tsx                🔔 Lista
│   ├── alertas_.nueva.tsx         🆕 Crear alerta
│   ├── admin.tsx                  🛠️ Layout del panel
│   ├── admin.chollos.tsx          📦 CRUD chollos
│   ├── admin.categorias.tsx       🏷️ CRUD categorías
│   └── admin.tiendas.tsx          🏪 CRUD tiendas
│
├── 🎨 features/                   Dominios funcionales
│   ├── deals/components/          DealCard · Comments · ShareBox
│   ├── admin/hooks/               useAdminStats
│   ├── notifications/hooks/       useUnreadNotifications · …
│   └── telegram/components/       TelegramPanel
│
├── 🧩 components/
│   ├── layout/                    Chrome compartido
│   └── ui/                        Primitivos shadcn (no modificar)
│
├── 📡 services/api/               Único cliente HTTP
│   ├── client.ts                  fetchWithAuth + ApiError class
│   ├── deals.ts                   + isDuplicateDealError
│   ├── comments.ts · alerts.ts · notifications.ts · …
│
├── 🧠 lib/                        Lógica pura — CORE (90%+ cov)
│   ├── format.ts                  formatPrice · calculateDiscount · …
│   ├── errors.ts                  errorMessage(unknown → string)
│   ├── constants.ts               DEAL_STATUS_OPTIONS · …
│   ├── query-client.ts            Config TanStack Query
│   └── validation/                Zod schemas
│
├── 🪝 hooks/
│   └── useAuth.tsx                AuthProvider
│
├── 🔌 integrations/
│   └── supabase/                  Cliente lazy + tipos generados
│
└── 🧪 test/utils.tsx               renderWithProviders compartido
```

### 📜 Reglas de oro frontend

> 🔴 **1.** Toda llamada HTTP pasa por `services/api/`.
> Nunca `fetch` directo, nunca `supabase.from()`.

> 🔴 **2.** Supabase sólo para Auth y Storage desde el cliente.
> Documentado en [ADR-002](../adr/ADR-002-migracion-baas-a-api-gateway.md).

> 🔴 **3.** Validación con Zod en cliente + Pydantic en servidor.
> Doble frontera ([ADR-005](../adr/ADR-005-validacion-doble-frontera.md)).

> 🔴 **4.** TanStack Query para fetching. Hooks por feature. No
> `useEffect + setState` manual.

---

## 🎨 Sistema de UI / iconografía dinámica

Las **categorías llevan icono dinámico desde la BD** usando
**Lucide React** y un **Icon Mapper**.

### 🔄 Flujo

```
1. Tabla `categories` guarda un string `icon` (p.ej. "laptop")
        │
        ▼
2. routes/index.tsx mapea string → componente:
        │
        ▼
   const ICONS: Record<string, LucideIcon> = {
     laptop: Laptop,
     energy: Zap,
     cpu: Cpu,
     // ...
   };
        │
        ▼
3. Render:
        │
        ▼
   const Icon = ICONS[cat.icon] ?? Sparkles;  // fallback
   return <Icon className="size-6 text-cyan-glow" />;
```

### 💡 Por qué SVG (Lucide)

- 📐 Escalan sin pérdida
- 🪶 Peso mínimo
- 🎨 Se estilizan con clases Tailwind directamente
- 🚫 Evita CDN externo de imágenes

### ✏️ Para añadir categoría con icono nuevo

```
1. Elegir nombre en lucide.dev
2. Importar componente en index.tsx
3. Añadir entrada en ICONS
4. Actualizar BD con la clave
```

---

## 📋 Dónde añadir nuevas funcionalidades

> 💡 **Regla**: una funcionalidad → como mucho un módulo backend +
> una feature frontend.

| Tipo de cambio | Dónde |
|---|---|
| 🧱 Nueva entidad de dominio | Nuevo módulo en `buenchollo-api/app/modules/<dominio>/` con las 4 capas |
| 🛠️ Nuevo endpoint admin | `<dominio>/api/router.py` con `Depends(require_admin)` + audit_log |
| 🎨 Nuevo componente UI compartido | `components/` si es chrome; `features/<dominio>/components/` si es de un dominio |
| 📁 Nueva ruta pública | `routes/` (file-based) |
| 🪝 Hook que consume API | `features/<dominio>/hooks/` con TanStack Query |
| 🧠 Función pura reutilizable | `lib/` con test al lado |

---

<p align="center">
  <a href="02-installation-and-setup.md">← Anterior: Instalación</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="04-configuration.md">Siguiente: Configuración →</a>
</p>
