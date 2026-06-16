# SETUP — BuenCholloTech

Guía para levantar el proyecto completo desde cualquier IDE o máquina nueva.

---

## Requisitos previos del sistema

| Herramienta | Versión mínima | Instalar desde |
|---|---|---|
| Python | 3.11+ | https://python.org |
| Node.js | 20+ (LTS) | https://nodejs.org |
| pnpm | 9+ | `npm install -g pnpm` |
| Git | cualquiera | https://git-scm.com |

---

## 1. buenchollo-api (FastAPI · Python)

### Primera vez

```powershell
cd buenchollo-api

# Crear entorno virtual
python -m venv .venv

# Activar (PowerShell)
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Copiar y rellenar variables de entorno
copy .env.example .env
```

> Para desarrollo/testing instala `requirements-dev.txt` en su lugar.

### Arrancar

```powershell
uvicorn app.main:app --reload --port 8000
```

API disponible en: http://localhost:8000  
Docs interactivos: http://localhost:8000/docs

### Variables de entorno necesarias (`.env`)

```env
APP_NAME=BuenCholloTech
APP_ENV=development
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://user:password@host:6543/postgres

SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<service_role_key>

OPENAI_API_KEY=sk-...

CORS_ORIGINS=["http://localhost:5173"]
```

---

## 2. buenchollo-web (React · TypeScript · Vite)

### Primera vez

```powershell
cd buenchollo-web

# Instalar pnpm si no está disponible
npm install -g pnpm

# Instalar dependencias del proyecto
pnpm install

# Copiar y rellenar variables de entorno
copy .env.example .env.local
```

### Arrancar

```powershell
pnpm run dev
```

App disponible en: http://localhost:5173

### Variables de entorno necesarias (`.env.local`)

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon_key>
```

---

## Orden de arranque recomendado

1. `buenchollo-api` (backend)
2. `buenchollo-web` (frontend)

---

## Resolución de problemas comunes

| Problema | Solución |
|---|---|
| `pnpm` no reconocido | `npm install -g pnpm` y reiniciar terminal |
| Error de conexión a BD | Verificar `DATABASE_URL` en `.env` y que el pooler de Supabase esté activo |
| CORS error en el frontend | Añadir `http://localhost:5173` a `CORS_ORIGINS` en `.env` del backend |
| `asyncpg` falla en Windows | Asegurarse de usar Python 3.11+ de 64 bits |
| PowerShell no permite scripts | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
