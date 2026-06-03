# buenchollo-web

Frontend de **BuenCholloTech**. SPA con SSR opcional en React 19 +
TypeScript strict + Vite + TanStack Router/Query + Tailwind +
shadcn/ui.

Se comunica **exclusivamente** con `buenchollo-api` mediante el
cliente HTTP centralizado en `src/services/api/`. Las consultas a la
BD nunca pasan por el cliente directamente: van por la API
([ADR-002](../docs/adr/ADR-002-migracion-baas-a-api-gateway.md)).
Sólo se usa Supabase directamente para Auth (OAuth Google) y Storage
(subida de imágenes desde el panel admin).

Para la documentación completa del repositorio (instalación, setup,
estructura, despliegue, troubleshooting) ver
[`docs/project/`](../docs/project/00-index.md).

---

## Setup rápido

```bash
# Dependencias (npm, no pnpm — el monorepo usa Husky con package.json root)
npm install

# Variables de entorno
cp .env.example .env.local
# Editar .env.local

# Arrancar
npm run dev
```

Servidor en `http://localhost:8080` (vinxi default; salta a 8081/8082
si está ocupado). Setup detallado:
[`docs/project/02-installation-and-setup.md`](../docs/project/02-installation-and-setup.md).

---

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `VITE_SUPABASE_URL` | ✅ | URL del proyecto Supabase |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | ✅ | **anon key** (pública, embebida en el bundle) |
| `VITE_API_URL` | ✅ | Base de `buenchollo-api` sin `/v1` final |

> Las `VITE_*` se **embeben en el JavaScript del cliente** al hacer
> `npm run build`. Cualquier valor que pongas aquí es público. Nunca
> pongas la `service_role key` de Supabase.

---

## Scripts

```bash
# Desarrollo
npm run dev               # vite dev con hot-reload
npm run build             # build estático en dist/

# Calidad
npm run lint              # ESLint estricto
npm run typecheck         # tsc --noEmit (strict)
npm run format            # Prettier

# Tests
npm run test              # Vitest watch
npm run test:run          # 72 tests one-shot
npm run test:coverage     # con threshold en src/lib/**
npm run test:e2e          # 8 Playwright (chromium, levanta dev server)
npm run test:e2e:ui       # modo interactivo

# Gates compuestos
npm run quality           # lint + typecheck + test:run (lo del Husky pre-commit/pre-push)
npm run quality:full      # + test:e2e
```

---

## Estructura

Organización por features de dominio (no por tipos de archivo):

```
src/
├── routes/                TanStack Router file-based
│   ├── __root.tsx         Providers (QueryClient, Auth, Toaster)
│   ├── index.tsx          Home (feed infinito + populares)
│   ├── chollo.$slug.tsx   Detalle
│   ├── explorar.tsx       Búsqueda
│   ├── alertas.tsx        Lista
│   ├── alertas_.nueva.tsx Crear alerta (sin anidamiento)
│   └── admin.*.tsx        Panel administración
│
├── features/              Dominios funcionales
│   ├── deals/components/  DealCard · Comments · ShareBox
│   ├── admin/hooks/       useAdminStats
│   ├── notifications/hooks/  useUnreadNotifications · useNotificationsList · …
│   └── telegram/components/  TelegramPanel
│
├── components/
│   ├── layout/            Header · Footer · Logo · CategoriesDrawer · Layout
│   └── ui/                Primitivos shadcn (no modificar manualmente)
│
├── services/api/          ⚠️ Único punto de contacto con buenchollo-api
│   ├── client.ts          fetchWithAuth + ApiError
│   ├── deals.ts           + isDuplicateDealError type guard
│   ├── alerts.ts · notifications.ts · comments.ts · …
│
├── lib/                   Lógica pura (CORE para coverage 90%+)
│   ├── format.ts          formatPrice, calculateDiscount, slugify, …
│   ├── errors.ts          errorMessage(unknown → string)
│   ├── constants.ts       DEAL_STATUS_OPTIONS, TEMPERATURE_*
│   ├── query-client.ts    config TanStack Query
│   └── validation/        deals.ts, alerts.ts (Zod schemas)
│
├── hooks/useAuth.tsx      AuthProvider con supabase.auth.getSession
├── integrations/supabase/ cliente lazy + tipos generados
└── test/utils.tsx         renderWithProviders compartido
```

Justificación: [`docs/project/03-project-structure.md`](../docs/project/03-project-structure.md).

---

## Reglas de oro

1. **Toda llamada HTTP pasa por `services/api/`**. Nunca `fetch`
   directo, nunca `supabase.from()`.
2. **Supabase sólo para Auth y Storage** desde el cliente
   ([ADR-002](../docs/adr/ADR-002-migracion-baas-a-api-gateway.md)).
3. **Validación con Zod en cliente + Pydantic en servidor** (doble
   frontera, [ADR-005](../docs/adr/ADR-005-validacion-doble-frontera.md)).
4. **TanStack Query para fetching**: hooks por feature, sin
   `useEffect + setState` manual.

---

## Tests

| Capa | Cantidad | Stack | Duración |
|---|---|---|---|
| Unit | 59 | Vitest + jsdom | ~0,5 s |
| Integration | 13 | Vitest + Testing Library + userEvent | ~0,7 s |
| E2E | 8 | Playwright chromium | ~6 s |

Threshold automático en `vitest.config.ts`:

```ts
"src/lib/**": { lines: 90, functions: 90, branches: 80, statements: 90 }
```

Estrategia completa: [`docs/project/06-testing-and-quality.md`](../docs/project/06-testing-and-quality.md).

---

## Despliegue

Build estático:

```bash
# Crear .env.production con valores reales
echo "VITE_API_URL=https://api.tudominio.com" > .env.production
echo "VITE_SUPABASE_URL=https://<ref>.supabase.co" >> .env.production
echo "VITE_SUPABASE_PUBLISHABLE_KEY=eyJ..." >> .env.production

npm run build   # genera dist/
```

Servir `dist/` desde:

- Reverse proxy del NAS Synology (mismo que sirve el backend), o
- Cloudflare Pages / Vercel / Netlify para CDN global.

Despliegue completo con dominio definitivo:
[`docs/project/08-deployment.md`](../docs/project/08-deployment.md).

---

## Documentación relacionada

| Tema | Documento |
|---|---|
| **Setup completo del repo** | [`docs/project/02-installation-and-setup.md`](../docs/project/02-installation-and-setup.md) |
| **Estructura por features** | [`docs/project/03-project-structure.md`](../docs/project/03-project-structure.md) |
| **Variables de entorno** | [`docs/project/04-configuration.md`](../docs/project/04-configuration.md) |
| **Tests y coverage** | [`docs/project/06-testing-and-quality.md`](../docs/project/06-testing-and-quality.md) |
| **Seguridad** | [`docs/project/07-security.md`](../docs/project/07-security.md) |
| **Despliegue** | [`docs/project/08-deployment.md`](../docs/project/08-deployment.md) |
| **Troubleshooting** | [`docs/project/09-troubleshooting.md`](../docs/project/09-troubleshooting.md) |
