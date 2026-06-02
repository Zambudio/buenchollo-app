# 02 — Instalación y setup

## Requisitos

| Herramienta | Versión mínima | Comprobar con |
|---|---|---|
| Git | cualquiera reciente | `git --version` |
| Python | 3.11+ | `python --version` |
| Node.js | 20+ (LTS) | `node --version` |
| npm | 10+ (viene con Node 20) | `npm --version` |
| Docker + Compose | opcional para deploy NAS | `docker --version` |

> Por qué npm y no pnpm: Husky (configurado en este proyecto) usa `package.json` de raíz con `prepare: husky`. El primer `npm install` engancha los hooks automáticamente. Si usaras pnpm, tendrías que reconfigurar.

## 1. Clonar el repositorio

```bash
git clone https://github.com/Zambudio/buenchollo-app.git
cd buenchollo-app

# Instalar Husky (gates pre-commit / pre-push)
npm install
```

## 2. Backend — `buenchollo-api`

```bash
cd buenchollo-api

# Entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate            # Linux/Mac

# Dependencias (runtime + dev para tests)
pip install -r requirements-dev.txt

# Variables de entorno
cp .env.example .env
# Editar .env con valores reales (ver 04-configuration.md)

# Arrancar en modo desarrollo
uvicorn app.main:app --reload --port 8000
```

API en `http://localhost:8000` · OpenAPI en `http://localhost:8000/docs`
· Health en `http://localhost:8000/health`.

**Tests**:

```bash
pytest -q -m "not integration"   # 87 unitarios, ~1s, sin BD
pytest -q                         # incluye 9 integración (necesitan Postgres real)
```

**Migraciones Alembic**: ver [`buenchollo-api/MIGRATIONS.md`](../../buenchollo-api/MIGRATIONS.md).

## 3. Frontend — `buenchollo-web`

```bash
cd buenchollo-web

# Dependencias
npm install

# Variables de entorno
cp .env.example .env.local
# Editar .env.local (VITE_SUPABASE_URL, VITE_SUPABASE_PUBLISHABLE_KEY, VITE_API_URL)

# Arrancar
npm run dev
```

Web en `http://localhost:8080` (vinxi default; salta a 8081/8082 si está ocupado).

**Scripts útiles**:

```bash
npm run typecheck       # tsc --noEmit (strict)
npm run lint            # ESLint estricto
npm run test            # Vitest watch
npm run test:run        # Vitest one-shot (72 tests)
npm run test:coverage   # con thresholds en src/lib/**
npm run test:e2e        # Playwright (8 tests, levanta dev server)
npm run quality         # lint + typecheck + test:run
npm run quality:full    # + E2E
```

## 4. Supabase (Auth + Storage + DB)

El proyecto requiere un proyecto Supabase configurado. Los pasos:

### 4.1 Crear proyecto

1. [supabase.com](https://supabase.com) → New project (región más cercana, p.ej. `eu-central-1`).
2. Copiar las credenciales que aparecen en `Settings → API`:
   - `Project URL` → `SUPABASE_URL` (backend) y `VITE_SUPABASE_URL` (frontend).
   - `anon public` → `VITE_SUPABASE_PUBLISHABLE_KEY` (frontend, embebida en el bundle, pública por diseño).
   - `service_role` → `SUPABASE_KEY` (backend, **secreta**, bypassa RLS).

### 4.2 Auth con Google

1. Google Cloud Console → crear OAuth Client ID con redirect URI `https://<tu-supabase-ref>.supabase.co/auth/v1/callback`.
2. Supabase → `Authentication → Providers → Google` → pegar Client ID + Client Secret.
3. Supabase → `Authentication → URL Configuration`:
   - `Site URL`: `http://localhost:8080` (dev) o tu dominio real.
   - `Redirect URLs`: `http://localhost:8080/**` para dev.

### 4.3 Base de datos

El esquema vive parcialmente en `buenchollo-api/supabase/migrations/*.sql` (histórico) y se gestiona desde 2026-05-27 con Alembic.

Pasos para sincronizar un proyecto Supabase nuevo:

1. Aplicar los SQL históricos de `buenchollo-api/supabase/migrations/` desde el SQL Editor de Supabase **en orden cronológico**.
2. Crear la tabla `alembic_version` y marcar la baseline (ver [`buenchollo-api/MIGRATIONS.md`](../../buenchollo-api/MIGRATIONS.md)).
3. Las siguientes migraciones (Alembic) se aplicarán automáticamente cada vez que el contenedor del NAS arranque (`alembic upgrade head` en el `command` del docker-compose).

### 4.4 RLS activado

Las 12 tablas de `public` tienen Row Level Security activado. El backend usa la `service_role key` para bypassarlo de forma controlada (ver [ADR-006](../adr/ADR-006-rls-service-role.md)). Sin RLS activado, cualquier visitante con el `anon key` podría leer la BD.

Verificar en Supabase Dashboard → `Authentication → Policies` que cada tabla tiene RLS = ON.

## 5. Servicios externos opcionales

- **Amazon Creators API**: necesario para el autocomplete del panel admin. Obtener credenciales en `developer.amazon.com` (Associate Creators).
- **OpenAI API**: necesario para el copy del autocomplete. Obtener key en `platform.openai.com`.
- **Telegram Bot**: opcional. Crear bot con `@BotFather`, anotar token + canal.
- **Sentry SaaS**: opcional. Sin DSN, no se envía nada.

Sin estas credenciales el proyecto arranca igual; sólo se desactivan las features que dependen de cada una.

## 6. Comprobación final

```bash
# Backend
curl -s http://localhost:8000/health
# {"status":"ok"}

# Frontend
# Abrir http://localhost:8080 → debe cargar la home con el shell

# Suite completa
cd buenchollo-web && npm run quality        # frontend
cd ../buenchollo-api && pytest -q -m "not integration"   # backend
```

Si todo verde, listo para desarrollar.

Para problemas comunes ver [`09-troubleshooting.md`](09-troubleshooting.md).
