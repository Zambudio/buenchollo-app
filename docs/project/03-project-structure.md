# 03 — Estructura del proyecto

## Monorepo

```
buenchollo-app/
├── buenchollo-api/         Backend FastAPI · Python
├── buenchollo-web/         Frontend React · TypeScript · Vite
├── docs/                   Documentación (este árbol)
│   ├── project/            Operativa del repo
│   ├── master/             Defensa del TFM
│   ├── adr/                Decisiones arquitectónicas
│   ├── reference/          Referencia técnica densa
│   └── archive/            Histórico preservado
├── .github/
│   ├── workflows/ci.yml    CI (backend + frontend + e2e + security-audit)
│   └── dependabot.yml      Updates semanales agrupados
├── .husky/                 Quality gates locales (pre-commit, pre-push)
├── package.json            Root: sólo Husky devDependency
├── README.md
├── CLAUDE.md               Instrucciones para asistentes IA
├── PROJECT_STATUS.md       Bitácora viva (CHANGELOG en prosa)
└── SECURITY.md             Política de divulgación responsable (convención GitHub)
```

## Backend — `buenchollo-api/`

**Estilo**: Clean Architecture pragmática, no purista. Una carpeta por
módulo de dominio, con 4 capas dentro:

```
app/
├── core/                       Infraestructura compartida
│   ├── config.py               Settings (pydantic-settings)
│   ├── database.py             Engine SQLAlchemy async + get_db
│   ├── security.py             get_current_user, require_admin
│   ├── exceptions.py           Jerarquía DomainError (NotFound, Conflict, …)
│   ├── request_id.py           ContextVar + middleware
│   ├── rate_limit.py           SlowAPI con X-Forwarded-For
│   ├── security_headers.py     CSP, X-Frame-Options, HSTS en prod
│   ├── sentry.py               LoggingIntegration + before_send con request_id
│   ├── audit.py                Audit log para acciones admin
│   ├── health.py               /health y /health/ready
│   └── logging.py              JSON con request_id
│
├── modules/                    1 carpeta por dominio
│   └── <dominio>/
│       ├── domain/             Modelos SQLAlchemy + excepciones de dominio
│       ├── application/        Servicios / use cases (sin FastAPI ni SQLAlchemy)
│       ├── infrastructure/     Repositorios + clientes externos
│       └── api/                Router FastAPI + schemas Pydantic
│
├── alembic/                    Migraciones versionadas
├── supabase/migrations/        Histórico SQL pre-Alembic
└── tests/                      Unitarios + integración (marker @pytest.mark.integration)
```

Módulos: `deals`, `comments`, `alerts`, `notifications`, `categories`,
`stores`, `users`, `products`, `telegram`.

**Flujo de dependencias**: `api → application → domain ← infrastructure`.
El dominio no depende de FastAPI ni SQLAlchemy.

**Routers**: solo hablan HTTP. Toda la lógica vive en `application/`.
Más detalle y justificación en [ADR-001](../adr/ADR-001-monolito-modular-fastapi.md).

## Frontend — `buenchollo-web/`

**Estilo**: organización por features (no por tipos de archivo).

```
src/
├── routes/                     TanStack Router file-based
│   ├── __root.tsx              Providers (QueryClient, Auth, Toaster)
│   ├── index.tsx               Home (feed infinito + populares)
│   ├── chollo.$slug.tsx        Detalle
│   ├── explorar.tsx            Búsqueda
│   ├── alertas.tsx             Lista
│   ├── alertas_.nueva.tsx      Crear (sin anidamiento, ver ADR de routing)
│   ├── admin.tsx               Layout del panel
│   ├── admin.chollos.tsx       CRUD chollos
│   ├── admin.categorias.tsx    CRUD categorías
│   └── admin.tiendas.tsx       CRUD tiendas
│
├── features/                   Dominios funcionales
│   ├── deals/components/       DealCard · Comments · ShareBox
│   ├── admin/hooks/            useAdminStats
│   ├── notifications/hooks/    useUnreadNotifications · useNotificationsList · useMarkNotificationsRead
│   └── telegram/components/    TelegramPanel
│
├── components/
│   ├── layout/                 Header · Footer · Logo · CategoriesDrawer · Layout
│   └── ui/                     Primitivos shadcn (no modificar manualmente)
│
├── services/api/               Único punto de contacto con buenchollo-api
│   ├── client.ts               fetchWithAuth + ApiError class
│   ├── deals.ts                + isDuplicateDealError type guard
│   ├── comments.ts
│   ├── alerts.ts
│   ├── notifications.ts
│   ├── categories.ts
│   ├── stores.ts
│   ├── products.ts
│   ├── telegram.ts
│   └── auth.ts (+ admin users)
│
├── lib/                        Lógica pura — CORE para coverage 90%+
│   ├── format.ts               formatPrice · calculateDiscount · slugify · …
│   ├── errors.ts               errorMessage(unknown → string)
│   ├── constants.ts            DEAL_STATUS_OPTIONS · TEMPERATURE_*
│   ├── query-client.ts         Config TanStack Query
│   ├── validation/deals.ts     Zod schema admin form
│   └── validation/alerts.ts    Zod schema crear alerta
│
├── hooks/
│   └── useAuth.tsx             AuthProvider con supabase.auth.getSession
│
├── integrations/
│   ├── supabase/client.ts      Proxy lazy del cliente Supabase
│   └── supabase/types.ts       Generado por Supabase CLI
│
└── test/utils.tsx              renderWithProviders compartido
```

**Reglas de oro frontend**:

1. **Toda llamada HTTP pasa por `services/api/`**. Nunca `fetch` directo, nunca `supabase.from()`.
2. **Supabase sólo para Auth y Storage** desde el cliente (decisión documentada en [ADR-002](../adr/ADR-002-migracion-baas-a-api-gateway.md)).
3. **Validación con Zod en el cliente + Pydantic en el servidor** (doble frontera, ver [ADR-005](../adr/ADR-005-validacion-doble-frontera.md)).
4. **TanStack Query para fetching**: hooks por feature, `staleTime` razonable, no `useEffect + setState` manual.

## Sistema de UI / iconografía

Las categorías llevan icono dinámico desde la BD usando **Lucide React**
y un **Icon Mapper**:

1. Tabla `categories` guarda un string `icon` (p.ej. `"laptop"`).
2. `src/routes/index.tsx` mapea string → componente:

   ```ts
   const ICONS: Record<string, LucideIcon> = {
     laptop: Laptop, energy: Zap, cpu: Cpu, /* ... */
   };
   ```

3. Render:

   ```tsx
   const Icon = ICONS[cat.icon] ?? Sparkles;  // fallback
   return <Icon className="size-6 text-cyan-glow" />;
   ```

**Por qué SVG (Lucide)**: escalan sin pérdida, peso mínimo, se estilizan
con clases Tailwind directamente, evita CDN externo de imágenes.

**Para añadir categoría con icono nuevo**:
1. Elegir nombre en [lucide.dev](https://lucide.dev).
2. Importar componente en `index.tsx`.
3. Añadir entrada en `ICONS`.
4. Actualizar BD con la clave.

## Dónde añadir nuevas funcionalidades

| Tipo de cambio | Dónde |
|---|---|
| Nueva entidad de dominio | Nuevo módulo en `buenchollo-api/app/modules/<dominio>/` con las 4 capas |
| Nuevo endpoint admin | `<dominio>/api/router.py` con `Depends(require_admin)` + audit_log |
| Nuevo componente UI compartido | `buenchollo-web/src/components/` si es chrome; `features/<dominio>/components/` si es de un dominio |
| Nueva ruta pública | `buenchollo-web/src/routes/` (file-based) |
| Hook que consume API | `buenchollo-web/src/features/<dominio>/hooks/` con TanStack Query |
| Función pura reutilizable | `buenchollo-web/src/lib/` con test al lado |

Mantén la regla: una funcionalidad → como mucho un módulo backend + una feature frontend.
