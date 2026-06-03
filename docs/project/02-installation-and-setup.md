# 📥 02 · Instalación y setup

> **TL;DR** · Clonar repo · instalar Husky con `npm install` raíz ·
> levantar backend con Python venv + uvicorn · levantar frontend con
> `npm run dev` · configurar Supabase. En 10 minutos lo tienes
> funcionando.

---

## ✅ Requisitos

| Herramienta | Versión mínima | Comprobar con |
|---|---|---|
| 📦 Git | cualquiera reciente | `git --version` |
| 🐍 Python | **3.11+** | `python --version` |
| 🟢 Node.js | **20+ (LTS)** | `node --version` |
| 📦 npm | **10+** (viene con Node 20) | `npm --version` |
| 🐳 Docker + Compose | opcional para deploy NAS | `docker --version` |

> 💡 **Por qué npm y no pnpm**: Husky (configurado en este proyecto)
> usa `package.json` de raíz con `prepare: husky`. El primer
> `npm install` engancha los hooks automáticamente. Si usaras pnpm,
> tendrías que reconfigurar.

---

## 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/Zambudio/buenchollo-app.git
cd buenchollo-app

# Instalar Husky (gates pre-commit / pre-push)
npm install
```

> ✅ Tras este `npm install`, los hooks de Git están activos.
> Cualquier commit ejecutará lint + typecheck automáticamente.

---

## 2️⃣ Backend — `buenchollo-api`

```bash
cd buenchollo-api

# 📦 Entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1            # 🪟 Windows PowerShell
# source .venv/bin/activate           # 🐧 Linux/Mac

# 🔧 Dependencias (runtime + dev para tests)
pip install -r requirements-dev.txt

# 🔑 Variables de entorno
cp .env.example .env
# 👉 Editar .env con valores reales (ver 04-configuration.md)

# 🚀 Arrancar en modo desarrollo
uvicorn app.main:app --reload --port 8000
```

### 📡 Endpoints útiles tras arrancar

| URL | Para qué |
|---|---|
| `http://localhost:8000` | Base de la API |
| `http://localhost:8000/docs` | 📜 OpenAPI interactivo (Swagger) |
| `http://localhost:8000/health` | ❤️ Liveness check |
| `http://localhost:8000/health/ready` | 🩺 Readiness (incluye latencia BD) |

### 🧪 Tests

```bash
pytest -q -m "not integration"   # ✅ 87 unitarios, ~1s, sin BD
pytest -q                         # 🟡 incluye 9 integración (Postgres real)
```

> 📚 **Migraciones Alembic**: ver
> [`buenchollo-api/MIGRATIONS.md`](../../buenchollo-api/MIGRATIONS.md).

---

## 3️⃣ Frontend — `buenchollo-web`

```bash
cd buenchollo-web

# 📦 Dependencias
npm install

# 🔑 Variables de entorno
cp .env.example .env.local
# 👉 Editar .env.local (ver tabla más abajo)

# 🚀 Arrancar
npm run dev
```

> 🌐 Web disponible en `http://localhost:8080` (vinxi default; salta a
> 8081/8082 si está ocupado).

### 🛠️ Scripts útiles

| Comando | Para qué |
|---|---|
| `npm run typecheck` | TypeScript strict |
| `npm run lint` | ESLint estricto |
| `npm run test` | Vitest en modo watch |
| `npm run test:run` | Vitest one-shot (72 tests) |
| `npm run test:coverage` | Con thresholds en `src/lib/**` |
| `npm run test:e2e` | Playwright (8 tests) |
| `npm run quality` | lint + typecheck + test:run |
| `npm run quality:full` | + E2E |

---

## 4️⃣ Supabase (Auth + Storage + DB)

> 🎯 El proyecto requiere un proyecto Supabase configurado.
> Es lo único que no podemos preparar por ti.

### 4.1 🆕 Crear proyecto

1. Entra a [supabase.com](https://supabase.com) → **New project**
   - Elige región más cercana (p.ej. `eu-central-1`)
2. En `Settings → API`, anota:

| Credencial | Dónde se usa |
|---|---|
| **Project URL** | `SUPABASE_URL` (backend) y `VITE_SUPABASE_URL` (frontend) |
| **anon public** | `VITE_SUPABASE_PUBLISHABLE_KEY` (frontend) — pública por diseño |
| **service_role** | `SUPABASE_KEY` (backend) — 🔒 **secreta**, bypassa RLS |

### 4.2 🔐 Auth con Google

```
1. Google Cloud Console
   ├─ Crear OAuth Client ID
   └─ Redirect URI:
      https://<tu-supabase-ref>.supabase.co/auth/v1/callback

2. Supabase → Authentication → Providers → Google
   ├─ Pegar Client ID
   └─ Pegar Client Secret

3. Supabase → Authentication → URL Configuration
   ├─ Site URL: http://localhost:8080
   └─ Redirect URLs: http://localhost:8080/**
```

### 4.3 💾 Base de datos

El esquema vive en dos sitios por motivos históricos:

```
buenchollo-api/
├── supabase/migrations/*.sql     ← Histórico (2026-04 a 2026-05)
└── alembic/versions/*.py         ← Desde 2026-05-27 en adelante
```

> 📚 Setup completo de un proyecto Supabase nuevo:
> [`buenchollo-api/MIGRATIONS.md`](../../buenchollo-api/MIGRATIONS.md).

### 4.4 🔒 RLS activado

✅ Las **12 tablas** de `public` tienen Row Level Security activado.
El backend usa la `service_role key` para bypassarlo de forma
controlada ([ADR-006](../adr/ADR-006-rls-service-role.md)).

> ⚠️ **Sin RLS activado**, cualquier visitante con el `anon key`
> podría leer la BD.

**Verificación**: Supabase Dashboard → `Authentication → Policies` →
cada tabla debe tener **RLS = ON**.

---

## 5️⃣ Servicios externos opcionales

| Servicio | Necesario para | Donde se obtiene |
|---|---|---|
| 🛒 **Amazon Creators API** | Autocomplete del panel admin | `developer.amazon.com` (Associate Creators) |
| 🤖 **OpenAI API** | Copy del autocomplete | `platform.openai.com` |
| ✈️ **Telegram Bot** | Publicación al canal | `@BotFather` en Telegram |
| 🐛 **Sentry SaaS** | Error tracking | `sentry.io` (gratuito) |

> ⚙️ **Sin estas credenciales el proyecto arranca igual**; sólo se
> desactivan las features que dependen de cada una.

---

## ✅ Comprobación final

```bash
# 🐍 Backend
curl -s http://localhost:8000/health
# → {"status":"ok"}

# 🌐 Frontend
# Abrir http://localhost:8080 → debe cargar la home con el shell

# 🧪 Suite completa
cd buenchollo-web && npm run quality
cd ../buenchollo-api && pytest -q -m "not integration"
```

> ✅ Si todo verde → **listo para desarrollar**.

---

> 🔍 Para problemas comunes ver
> [`09 · Troubleshooting`](09-troubleshooting.md).

---

<p align="center">
  <a href="01-overview.md">← Anterior: Overview</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="03-project-structure.md">Siguiente: Estructura →</a>
</p>
