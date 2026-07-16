# 🐍 buenchollo-api

> **Backend FastAPI** de BuenCholloTech. Actúa como **API Gateway**
> del sistema: autenticación con JWT de Supabase, autorización por
> rol, lógica de negocio en módulos con Clean Architecture
> pragmática, y acceso único a PostgreSQL.

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="fastapi" src="https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white">
  <img alt="tests" src="https://img.shields.io/badge/tests-109%20✓-22c55e">
  <img alt="cve" src="https://img.shields.io/badge/CVEs%20prod-0-22c55e">
</p>

---

## 📡 Endpoints de utilidad

| URL | Para qué |
|---|---|
| `http://localhost:8000` | Base de la API |
| 📜 `http://localhost:8000/docs` | OpenAPI interactivo (Swagger) |
| ❤️ `http://localhost:8000/health` | Liveness check |
| 🩺 `http://localhost:8000/health/ready` | Readiness (incluye latencia BD) |

> 📚 Documentación operativa completa en
> [`../docs/project/`](../docs/project/00-index.md).

---

## 🚀 Setup rápido

```bash
# 📦 Entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1            # 🪟 Windows
# source .venv/bin/activate            # 🐧 Linux/Mac

# 🔧 Dependencias (runtime + tests)
pip install -r requirements-dev.txt

# 🔑 Variables de entorno
cp .env.example .env
# 👉 Editar .env (ver tabla más abajo)

# 🚀 Arrancar
uvicorn app.main:app --reload --port 8000
```

📚 Setup detallado, incluido Supabase Auth + RLS:
[`../docs/project/02-installation-and-setup.md`](../docs/project/02-installation-and-setup.md).

---

## ⚙️ Variables de entorno principales

Copia `.env.example` a `.env` y rellena cada valor. ⚠️ **Nunca subas
`.env` al repositorio**.

| Variable | Obligatoria | Descripción |
|---|---|---|
| 🔒 `DATABASE_URL` | ✅ | Conexión asyncpg al pooler (puerto **6543**) |
| 🔑 `SUPABASE_URL` | ✅ | `https://<ref>.supabase.co` |
| 🔐 `SUPABASE_KEY` | ✅ | **service_role key** (privada). ⚠️ NO la anon key |
| 🌐 `CORS_ORIGINS` | ✅ | Lista separada por comas. ❌ Nunca `*` en prod |
| 🤖 `OPENAI_API_KEY` | ⚠️ | Para autocomplete |
| 🛒 `AMAZON_CLIENT_ID/SECRET` | ⚠️ | Para autocomplete Amazon |
| 🏷️ `AMAZON_AFFILIATE_TAG` | ⚠️ | Tag de afiliado |
| 🔧 `APP_ENV` | — | `local` · `staging` · `production` |
| 📝 `LOG_LEVEL` | — | `INFO` por defecto |

> 📚 Tabla completa con todas las variables:
> [`../docs/project/04-configuration.md`](../docs/project/04-configuration.md).

> 💡 **Nota sobre `SUPABASE_KEY`**: usa la `service_role key`, nunca
> la `anon key`. El backend la necesita para validar JWT y para
> bypasear RLS desde el API Gateway.

---

## 🗂️ Estructura

> _Clean Architecture pragmática · una carpeta por módulo de dominio
> con 4 capas dentro._

```
app/
├── 🧠 core/                       Infraestructura compartida
│   ├── config.py                  Settings (pydantic-settings)
│   ├── database.py                Engine SQLAlchemy async + get_db
│   ├── security.py                get_current_user, require_admin
│   └── logging.py                 JSON con request_id
│
├── 🧱 modules/                    1 carpeta por dominio
│   └── <dominio>/
│       ├── 📦 domain/             modelos SQLAlchemy + excepciones
│       ├── 🎯 application/        casos de uso (services)
│       ├── 🔌 infrastructure/     repositorios + clientes externos
│       └── 🌐 api/                router FastAPI + schemas Pydantic
│
├── 🛠️ alembic/                    migraciones versionadas
├── 📜 supabase/migrations/        histórico SQL pre-Alembic
└── 🧪 tests/                      unitarios + integración
```

**Módulos**: `deals` · `comments` · `alerts` · `notifications` ·
`categories` · `stores` · `users` · `products` · `telegram`.

> 🔴 **Flujo de dependencias**: `api → application → domain ← infrastructure`
> El dominio no depende de FastAPI ni SQLAlchemy.

📚 Justificación: [ADR-001](../docs/adr/ADR-001-monolito-modular-fastapi.md)
y [`../docs/project/03-project-structure.md`](../docs/project/03-project-structure.md).

---

## 🌐 API versionada `/v1`

Todos los routers de negocio cuelgan de **`/v1/`**. Sólo `/health` y
`/health/ready` quedan sin versionar.

### 🌍 Públicos (sin auth)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Liveness |
| `GET` | `/health/ready` | Readiness + latencia BD |
| `GET` | `/v1/deals/latest` | Últimos chollos activos |
| `GET` | `/v1/deals/popular` | Por temperatura |
| `GET` | `/v1/deals/search` | Buscar con paginación |
| `GET` | `/v1/deals/{slug}` | Detalle por slug |
| `GET` | `/v1/categories` | Catálogo de categorías |
| `GET` | `/v1/stores` | Catálogo de tiendas |

### 🔐 Requieren JWT

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/v1/auth/me` | Diagnóstico de sesión + rol |
| `POST` | `/v1/deals/{id}/vote` | Votar (toggle, rate-limit 30/min) |
| `POST` | `/v1/deals/comments` | Comentar (rate-limit 10/min) |
| `GET` | `/v1/notifications` | Bandeja |
| `GET` | `/v1/notifications/unread-count` | Badge |
| `GET/POST/PUT/DELETE` | `/v1/alerts/...` | Gestión de alertas |

### 🛠️ Requieren JWT + rol `admin`

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/v1/deals/admin/all` | Todos los chollos |
| `POST` | `/v1/deals/admin` | Crear |
| `PUT` | `/v1/deals/admin/{id}` | Actualizar (detecta duplicados ASIN) |
| `DELETE` | `/v1/deals/admin/{id}` | Eliminar |
| `POST` | `/v1/products/preview` | Preview desde URL Amazon |
| `POST` | `/v1/telegram/publish` | Publicar al canal |
| `GET` | `/v1/admin/stats` | 6 KPIs en una query |
| `GET` | `/v1/admin/audit` | Audit log paginado |

> 📜 Documentación interactiva completa: `http://localhost:8000/docs`.

---

## 🧪 Tests

```bash
pytest -q -m "not integration"   # ✅ 87 unitarios + 9 security, ~1s, sin BD
pytest -q                         # 🟡 incluye 9 integración con BD real
```

📚 Estrategia: [`../docs/master/06-…`](../docs/master/06-calidad-testing-y-refactorizacion.md).

---

## 🛠️ Migraciones (Alembic)

Convive con SQL histórico pre-2026-05-27. Desde el baseline
`20260527120000_baseline.py`, los cambios de esquema se gestionan con
Alembic.

> ✅ Cada arranque del contenedor ejecuta `alembic upgrade head`
> automáticamente antes de uvicorn.

📚 Setup: [`MIGRATIONS.md`](../docs/guides/MIGRATIONS.md).

---

## 🚀 Despliegue en NAS Synology

```bash
# En el NAS
cd /volume1/docker/buenchollo-api
git pull
docker-compose build --no-cache
docker-compose up -d

# Verificar
curl -s https://embyzambu.synology.me:8000/health
# → {"status":"ok"}
```

📚 Guía completa:
[`../docs/project/08-deployment.md`](../docs/project/08-deployment.md).

---

## 📚 Documentación relacionada

| Tema | Documento |
|---|---|
| 📥 **Setup completo** | [`docs/project/02`](../docs/project/02-installation-and-setup.md) |
| 🗂️ **Arquitectura del backend** | [`docs/project/03`](../docs/project/03-project-structure.md) + [ADRs](../docs/adr/00-index.md) |
| ⚙️ **Variables de entorno** | [`docs/project/04`](../docs/project/04-configuration.md) |
| 🧪 **Tests y quality gates** | [`docs/project/06`](../docs/project/06-testing-and-quality.md) |
| 🛡️ **Seguridad operativa** | [`docs/project/07`](../docs/project/07-security.md) |
| 🚀 **Despliegue NAS + dominio** | [`docs/project/08`](../docs/project/08-deployment.md) |
| 🔍 **Troubleshooting** | [`docs/project/09`](../docs/project/09-troubleshooting.md) |
| 🛠️ **Migraciones Alembic** | [`MIGRATIONS.md`](../docs/guides/MIGRATIONS.md) |
| 🛡️ **Política de seguridad** | [`SECURITY.md`](../SECURITY.md) (raíz) |
