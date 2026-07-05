# ⚛️ buenchollo-web

> **Frontend de BuenChollo Tech**. SPA con SSR opcional en React 19 +
> TypeScript strict + Vite + TanStack Router/Query + Tailwind +
> shadcn/ui.

<p align="center">
  <img alt="react" src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black">
  <img alt="typescript" src="https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white">
  <img alt="vite" src="https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white">
  <img alt="tests" src="https://img.shields.io/badge/tests-72%20+%208%20E2E%20✓-22c55e">
</p>

> 🚪 Se comunica **exclusivamente** con `buenchollo-api` mediante el
> cliente HTTP centralizado en `src/services/api/`. Las consultas a
> la BD nunca pasan por el cliente directamente — van por la API
> ([ADR-002](../docs/adr/ADR-002-migracion-baas-a-api-gateway.md)).
>
> 🔐 Sólo se usa Supabase directamente para **Auth** (OAuth Google)
> y **Storage** (subida de imágenes desde el panel admin).

📚 Documentación operativa completa:
[`../docs/project/`](../docs/project/00-index.md).

---

## 🚀 Setup rápido

```bash
# 📦 Dependencias (npm, no pnpm — el monorepo usa Husky con package.json root)
npm install

# 🔑 Variables de entorno
cp .env.example .env.local
# 👉 Editar .env.local

# 🚀 Arrancar
npm run dev
```

> 🌐 Servidor en `http://localhost:8080` (vinxi default; salta a
> 8081/8082 si está ocupado).

📚 Setup completo:
[`../docs/project/02-installation-and-setup.md`](../docs/project/02-installation-and-setup.md).

---

## ⚙️ Variables de entorno

| Variable                           | Obligatoria | Descripción                                   |
| ---------------------------------- | ----------- | --------------------------------------------- |
| 🔑 `VITE_SUPABASE_URL`             | ✅          | URL del proyecto Supabase                     |
| 🔐 `VITE_SUPABASE_PUBLISHABLE_KEY` | ✅          | **anon key** (pública). ⚠️ Nunca service_role |
| 🌐 `VITE_API_URL`                  | ✅          | Base de `buenchollo-api` (sin `/v1`)          |

> ⚠️ Las `VITE_*` se **embeben en el JavaScript del cliente** al
> hacer `npm run build`. Cualquier valor que pongas aquí es público.
> 🚨 Nunca pongas la `service_role key` de Supabase.

---

## 🛠️ Scripts

### 💻 Desarrollo

| Comando         | Para qué                  |
| --------------- | ------------------------- |
| `npm run dev`   | vite dev con hot-reload   |
| `npm run build` | build estático en `dist/` |

### 🧪 Calidad

| Comando             | Para qué              |
| ------------------- | --------------------- |
| `npm run lint`      | ESLint estricto       |
| `npm run typecheck` | tsc --noEmit (strict) |
| `npm run format`    | Prettier              |

### 🧪 Tests

| Comando                 | Para qué                      |
| ----------------------- | ----------------------------- |
| `npm run test`          | Vitest watch                  |
| `npm run test:run`      | 72 tests one-shot             |
| `npm run test:coverage` | Con threshold en `src/lib/**` |
| `npm run test:e2e`      | 8 Playwright (chromium)       |
| `npm run test:e2e:ui`   | Modo interactivo              |

### 🎯 Gates compuestos

| Comando                | Para qué                    |
| ---------------------- | --------------------------- |
| `npm run quality`      | lint + typecheck + test:run |
| `npm run quality:full` | + test:e2e                  |

---

## 🗂️ Estructura

> _Organización por features de dominio · no por tipos de archivo._

```
src/
├── 📁 routes/                     TanStack Router file-based
│   ├── __root.tsx                 Providers (QueryClient, Auth, Toaster)
│   ├── index.tsx                  🏠 Home (feed infinito + populares)
│   ├── chollo.$slug.tsx           📄 Detalle
│   ├── explorar.tsx               🔍 Búsqueda
│   ├── alertas.tsx                🔔 Lista
│   ├── alertas_.nueva.tsx         🆕 Crear alerta
│   └── admin.*.tsx                🛠️ Panel administración
│
├── 🎨 features/                   Dominios funcionales
│   ├── deals/components/          DealCard · Comments · ShareBox
│   ├── admin/hooks/               useAdminStats
│   ├── notifications/hooks/       useUnreadNotifications · …
│   └── telegram/components/       TelegramPanel
│
├── 🧩 components/
│   ├── layout/                    Header · Footer · Logo · Drawer · Layout
│   └── ui/                        Primitivos shadcn (no modificar)
│
├── 📡 services/api/               ⚠️ Único cliente HTTP
│   ├── client.ts                  fetchWithAuth + ApiError class
│   ├── deals.ts                   + isDuplicateDealError type guard
│   └── ...                        comments, alerts, notifications, ...
│
├── 🧠 lib/                        Lógica pura (CORE — coverage ≥90%)
│   ├── format.ts                  formatPrice · calculateDiscount · …
│   ├── errors.ts                  errorMessage(unknown → string)
│   ├── constants.ts               DEAL_STATUS_OPTIONS · TEMPERATURE_*
│   ├── query-client.ts            Config TanStack Query
│   └── validation/                deals.ts · alerts.ts (Zod)
│
├── 🪝 hooks/useAuth.tsx           AuthProvider
└── 🔌 integrations/supabase/      Cliente lazy + tipos generados
```

---

## 📜 Reglas de oro

> 🔴 **1.** Toda llamada HTTP pasa por `services/api/`.
> Nunca `fetch` directo, nunca `supabase.from()`.

> 🔴 **2.** Supabase sólo para Auth y Storage desde el cliente.
> Documentado en [ADR-002](../docs/adr/ADR-002-migracion-baas-a-api-gateway.md).

> 🔴 **3.** Validación con Zod en cliente + Pydantic en servidor.
> Doble frontera ([ADR-005](../docs/adr/ADR-005-validacion-doble-frontera.md)).

> 🔴 **4.** TanStack Query para fetching: hooks por feature, sin
> `useEffect + setState` manual.

---

## 🧪 Tests

| Capa           | Cantidad | Stack                                | Duración |
| -------------- | -------- | ------------------------------------ | -------- |
| ⚛️ Unit        | **59**   | Vitest + jsdom                       | ~0,5 s   |
| 🔗 Integration | **13**   | Vitest + Testing Library + userEvent | ~0,7 s   |
| 🎭 E2E         | **8**    | Playwright chromium                  | ~6 s     |

### 🎯 Threshold automático en `vitest.config.ts`

```ts
"src/lib/**": { lines: 90, functions: 90, branches: 80, statements: 90 }
```

> 🚨 Si el coverage en CORE baja del 90%, **CI rompe**.

📚 Estrategia completa:
[`../docs/project/06-testing-and-quality.md`](../docs/project/06-testing-and-quality.md).

---

## 🚀 Despliegue

```bash
# Crear .env.production con valores reales
echo "VITE_API_URL=https://api.tudominio.com" > .env.production
echo "VITE_SUPABASE_URL=https://<ref>.supabase.co" >> .env.production
echo "VITE_SUPABASE_PUBLISHABLE_KEY=eyJ..." >> .env.production

npm run build   # 📦 genera dist/
```

### 🌍 Dónde servir `dist/`

| Opción                                           | Cuándo                                         |
| ------------------------------------------------ | ---------------------------------------------- |
| 🏠 Reverse proxy del NAS apuntando a Nginx local | Coste cero, control total                      |
| ☁️ Cloudflare Pages / Vercel / Netlify           | CDN global, ideal para audiencia internacional |

📚 Guía completa: [`../docs/project/08-deployment.md`](../docs/project/08-deployment.md).

---

## 📚 Documentación relacionada

| Tema                           | Documento                                                         |
| ------------------------------ | ----------------------------------------------------------------- |
| 📥 **Setup completo del repo** | [`docs/project/02`](../docs/project/02-installation-and-setup.md) |
| 🗂️ **Estructura por features** | [`docs/project/03`](../docs/project/03-project-structure.md)      |
| ⚙️ **Variables de entorno**    | [`docs/project/04`](../docs/project/04-configuration.md)          |
| 🧪 **Tests y coverage**        | [`docs/project/06`](../docs/project/06-testing-and-quality.md)    |
| 🛡️ **Seguridad**               | [`docs/project/07`](../docs/project/07-security.md)               |
| 🚀 **Despliegue**              | [`docs/project/08`](../docs/project/08-deployment.md)             |
| 🔍 **Troubleshooting**         | [`docs/project/09`](../docs/project/09-troubleshooting.md)        |
