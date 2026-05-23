# 🍄 BuenCholloTech

Plataforma para publicar, gestionar y automatizar chollos tecnológicos.  
Proyecto dual: uso personal + Trabajo Final de Máster (TFM) en Desarrollo con IA 2025.

---

## Arquitectura

```
Browser (React SPA)
        │
        ▼
 FastAPI — buenchollo-api       (Docker en NAS Synology)
        ├──► PostgreSQL (SQLAlchemy async)  ← Supabase DB
        ├──► Supabase Auth                  ← validación JWT
        ├──► Amazon Creators API            ← scraping de productos
        └──► OpenAI API                     ← categorización y copy

 Excepción controlada:
 Browser ──► Supabase Storage   ← subida directa de imágenes (rendimiento)
```

**El frontend nunca llama directamente a Supabase DB.** Toda la lógica de negocio pasa por FastAPI (ADR-002).

---

## Estructura del monorepo

| Directorio | Stack | Rol |
|---|---|---|
| `buenchollo-api/` | Python 3.11 · FastAPI · SQLAlchemy · asyncpg | API Gateway — toda la lógica de negocio |
| `buenchollo-web/` | React · TypeScript · TanStack Router · Vite | Frontend — solo habla con buenchollo-api |
| `docs/` | Markdown | ADRs y documentación técnica |

---

## Prerequisitos

| Herramienta | Versión | Necesario para |
|---|---|---|
| Git | cualquiera | clonar el repo |
| Python | **3.11+** | backend |
| Node.js | 18+ | frontend |
| pnpm | 8+ | gestión de paquetes frontend (`npm install -g pnpm`) |
| Docker + Docker Compose | cualquiera | despliegue en NAS / producción |

---

## Setup desde cero

### 1. Clonar el repositorio

```bash
git clone https://github.com/Zambudio/buenchollo-app.git
cd buenchollo-app
```

### 2. Backend (buenchollo-api)

```bash
cd buenchollo-api

# Crear entorno virtual
python -m venv .venv

# Activar (Linux/Mac)
source .venv/bin/activate
# Activar (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales reales (ver buenchollo-api/README.md)

# Arrancar en modo desarrollo
uvicorn app.main:app --reload
```

API disponible en `http://localhost:8000` · Swagger en `http://localhost:8000/docs`

### 3. Frontend (buenchollo-web)

En una terminal nueva:

```bash
cd buenchollo-web

# Instalar dependencias
pnpm install

# Configurar variables de entorno
cp .env.example .env.local
# Editar .env.local con tu URL de Supabase y la URL de la API

# Arrancar en modo desarrollo
pnpm dev
```

Web disponible en `http://localhost:5173`

---

## Despliegue en producción (NAS Synology)

Ver instrucciones detalladas en [`buenchollo-api/README.md`](buenchollo-api/README.md#despliegue-en-nas-synology-docker).

Flujo resumido:
1. `git pull` en el NAS (o esperar a que SynologyDrive sincronice).
2. `docker-compose build --no-cache && docker-compose up -d`
3. Verificar: `https://[tu-ddns]:8000/health`

---

## Tests

```bash
cd buenchollo-api
python -m pytest app/tests/ -v
```

---

## Documentación técnica

| Documento | Contenido |
|---|---|
| [`buenchollo-api/README.md`](buenchollo-api/README.md) | Setup, API reference, variables de entorno, despliegue |
| [`buenchollo-web/README.md`](buenchollo-web/README.md) | Setup frontend, variables de entorno |
| [`REFACTOR_PLAN.md`](REFACTOR_PLAN.md) | Estado del proyecto y plan de desarrollo |
| [`docs/adr/ADR-001`](docs/adr/ADR-001-monolito-modular-fastapi.md) | Decisión: arquitectura monolito modular |
| [`docs/adr/ADR-002`](docs/adr/ADR-002-migracion-baas-a-api-gateway.md) | Decisión: migración BaaS → API Gateway |
| [`docs/SUPABASE_SETUP.md`](docs/SUPABASE_SETUP.md) | Esquema de BD y configuración Supabase |

---

*Desarrollado por Pedro Zambudio · Máster en Desarrollo con IA 2025*
