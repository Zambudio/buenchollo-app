# buenchollo-web

Frontend de BuenCholloTech. SPA en React + TypeScript con TanStack Router.  
Se comunica **exclusivamente** con `buenchollo-api` mediante el cliente HTTP centralizado en `src/services/api/`.

---

## Prerequisitos

| Herramienta | Versión | Instalación |
|---|---|---|
| Node.js | 18+ | https://nodejs.org |
| pnpm | 8+ | `npm install -g pnpm` |

---

## Setup local (desarrollo)

```bash
cd buenchollo-web

# 1. Instalar dependencias
pnpm install

# 2. Configurar variables de entorno
cp .env.example .env.local
# Editar .env.local con los valores reales (ver sección Variables de entorno)

# 3. Arrancar en modo desarrollo
pnpm dev
```

Web disponible en `http://localhost:5173`

---

## Variables de entorno

Copia `.env.example` a `.env.local` y rellena los valores. Nunca subas `.env.local` al repositorio.

| Variable | Obligatoria | Descripción |
|---|---|---|
| `VITE_SUPABASE_URL` | ✅ | URL del proyecto Supabase: `https://[REF].supabase.co` |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | ✅ | **Anon key** de Supabase (pública, para Auth y Storage) |
| `VITE_API_URL` | ✅ | URL base de `buenchollo-api`. En local: `http://localhost:8000`. En producción: `https://[tu-ddns]:8000` |

> Las variables `VITE_*` se embeben en el build. No pongas aquí claves secretas.

---

## Scripts disponibles

```bash
pnpm dev          # Servidor de desarrollo con hot-reload
pnpm build        # Build de producción en dist/
pnpm preview      # Previsualizar el build de producción localmente
pnpm lint         # ESLint
pnpm format       # Prettier
```

---

## Estructura del proyecto

```
src/
├── services/api/         # ⚠️ Único punto de contacto con buenchollo-api
│   ├── client.ts         # fetchWithAuth: añade Bearer token automáticamente
│   ├── deals.ts          # dealsService: chollos, votos, favoritos
│   ├── categories.ts     # categoriesService
│   └── stores.ts         # storesService
│
├── routes/               # Páginas (TanStack Router, file-based routing)
│   ├── index.tsx         # Home
│   ├── explorar.tsx      # Explorar chollos
│   ├── chollo.$slug.tsx  # Detalle de chollo
│   ├── favoritos.tsx     # Chollos guardados
│   ├── admin/            # Panel de administración (requiere rol admin)
│   └── ...
│
├── components/           # Componentes reutilizables
│   ├── ui/               # Shadcn/ui (no modificar manualmente)
│   ├── DealCard.tsx
│   ├── Header.tsx
│   └── ...
│
├── hooks/
│   └── useAuth.tsx       # Hook de autenticación (sesión Supabase)
│
└── integrations/
    └── supabase/         # Cliente Supabase (solo Auth y Storage)
```

---

## Convenciones importantes

- **Toda llamada HTTP a la API pasa por `src/services/api/`**. No uses `fetch` directo ni `supabase.from()` en las páginas.
- **Supabase solo se usa para Auth y Storage** desde el frontend. Las consultas a la BD van siempre a través de FastAPI.
- El token Bearer se añade automáticamente en `client.ts` — no lo gestiones manualmente en los componentes.

---

## Despliegue

El frontend se despliega estáticamente (Cloudflare Pages, Vercel, etc.) o se sirve localmente.

```bash
pnpm build        # Genera dist/
# Subir el contenido de dist/ a tu proveedor de hosting estático
```

Para desarrollo conectado a la API de producción, cambia `VITE_API_URL` en `.env.local`:
```
VITE_API_URL=https://[tu-ddns]:8000
```
