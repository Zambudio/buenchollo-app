# buenchollo-api

Backend **FastAPI** de BuenCholloTech. Actúa como **API Gateway** del
sistema: autenticación con JWT de Supabase, autorización por rol,
lógica de negocio en módulos con Clean Architecture pragmática, y
acceso único a PostgreSQL (Supabase pooler PgBouncer).

- **OpenAPI**: `http://localhost:8000/docs`
- **Health**: `http://localhost:8000/health`
- **Readiness** (incluye latencia BD): `http://localhost:8000/health/ready`

Para la documentación completa del repositorio (instalación, setup,
estructura, despliegue, troubleshooting) ver
[`docs/project/`](../docs/project/00-index.md).

---

## Setup rápido

```bash
# Entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows
# source .venv/bin/activate        # Linux/Mac

# Dependencias (runtime + tests)
pip install -r requirements-dev.txt

# Variables de entorno
cp .env.example .env
# Editar .env (ver tabla de variables abajo)

# Arrancar
uvicorn app.main:app --reload --port 8000
```

Setup detallado, incluido Supabase con Auth Google y RLS:
[`docs/project/02-installation-and-setup.md`](../docs/project/02-installation-and-setup.md).

---

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | ✅ | Conexión asyncpg al pooler de Supabase (puerto **6543**) |
| `SUPABASE_URL` | ✅ | `https://<ref>.supabase.co` |
| `SUPABASE_KEY` | ✅ | **service_role key** (privada, bypassa RLS) |
| `CORS_ORIGINS` | ✅ | Lista separada por comas. **Nunca `*`** en producción |
| `APP_ENV` | — | `local` \| `staging` \| `production` |
| `LOG_LEVEL` | — | `INFO` recomendado. **Nunca `DEBUG` en prod** |
| `LOG_FORMAT` | — | `json` para Loki/ELK, `text` para dev |
| `RATE_LIMIT_ENABLED` | — | `true` por defecto |
| `SENTRY_DSN` | — | Vacío para desactivar tracking |
| `OPENAI_API_KEY` | ⚠️ | Para copy del autocomplete |
| `AMAZON_CLIENT_ID/SECRET` | ⚠️ | Para preview Amazon |
| `AMAZON_AFFILIATE_TAG` | ⚠️ | Tag de afiliado |
| `TELEGRAM_BOT_TOKEN` | ⚠️ | Para publicación al canal |
| `TELEGRAM_MAIN_CHANNEL_ID` / `ADMIN_CHANNEL_ID` | ⚠️ | Canales |

✅ obligatoria · ⚠️ obligatoria para la feature concreta.
Detalle completo: [`docs/project/04-configuration.md`](../docs/project/04-configuration.md).

> **Nota sobre `SUPABASE_KEY`**: usa la `service_role key`, nunca la
> `anon key`. El backend la necesita para validar JWT con
> `supabase.auth.get_user()` y para escribir sobre tablas con RLS
> activado.

---

## Estructura

Clean Architecture pragmática · una carpeta por módulo de dominio
con 4 capas:

```
app/
├── core/                  config · database · security · request_id ·
│                          rate_limit · security_headers · sentry ·
│                          audit · health · logging · exceptions
│
├── modules/               1 carpeta por dominio
│   └── <dominio>/
│       ├── domain/        modelos SQLAlchemy + excepciones de dominio
│       ├── application/   servicios / casos de uso (sin FastAPI ni SQL)
│       ├── infrastructure/repositorios + clientes externos
│       └── api/           router FastAPI + schemas Pydantic
│
├── alembic/               migraciones versionadas
├── supabase/migrations/   histórico SQL pre-Alembic
└── tests/                 unitarios + integración (marker)
```

Módulos: `deals`, `comments`, `alerts`, `notifications`, `categories`,
`stores`, `users`, `products`, `telegram`.

Flujo de dependencias: `api → application → domain ← infrastructure`.
El dominio no depende de FastAPI ni SQLAlchemy.

Justificación arquitectónica: [ADR-001](../docs/adr/ADR-001-monolito-modular-fastapi.md)
y [`docs/project/03-project-structure.md`](../docs/project/03-project-structure.md).

---

## API versionada `/v1`

Todos los routers de negocio cuelgan de **`/v1/`**. Sólo `/health` y
`/health/ready` quedan sin versionar (son infraestructura, no
contrato de negocio).

### Públicos (sin auth)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/health/ready` | Readiness + latencia BD |
| `GET` | `/v1/deals/latest` | Últimos chollos activos |
| `GET` | `/v1/deals/popular` | Por temperatura |
| `GET` | `/v1/deals/search` | Buscar con paginación |
| `GET` | `/v1/deals/{slug}` | Detalle por slug |
| `GET` | `/v1/categories` | Catálogo de categorías |
| `GET` | `/v1/stores` | Catálogo de tiendas |

### Requieren JWT

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/v1/auth/me` | Diagnóstico de sesión + rol |
| `POST` | `/v1/deals/{id}/vote` | Votar (toggle, rate-limit 30/min) |
| `POST` | `/v1/deals/comments` | Comentar (rate-limit 10/min) |
| `GET` | `/v1/notifications` | Bandeja |
| `GET` | `/v1/notifications/unread-count` | Badge |
| `POST` | `/v1/notifications/mark-read` | Marcar todas leídas |
| `GET` | `/v1/alerts` / `POST` / `PUT` / `DELETE` | Gestión de alertas |
| `GET` | `/v1/favorites` / `POST /v1/deals/{id}/favorite` | Favoritos |

### Requieren JWT + rol `admin`

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/v1/deals/admin/all` | Todos los chollos |
| `POST` | `/v1/deals/admin` | Crear |
| `PUT` | `/v1/deals/admin/{id}` | Actualizar (detecta duplicados por ASIN) |
| `DELETE` | `/v1/deals/admin/{id}` | Eliminar |
| `POST` | `/v1/products/preview` | Preview desde URL Amazon (rate-limit 10/min) |
| `POST` | `/v1/telegram/publish` | Publicar al canal (rate-limit 5/min) |
| `GET` | `/v1/admin/stats` | 6 KPIs en una query |
| `GET` | `/v1/admin/audit` | Audit log paginado |

Documentación interactiva completa con request/response en
`http://localhost:8000/docs` (OpenAPI auto-generado).

---

## Tests

```bash
pytest -q -m "not integration"   # 78 unitarios, ~1s, sin BD
pytest -q                         # toda la suite (incluye 9 integración con BD real)
```

Los unitarios mockean Supabase, Amazon y la BD. Los de integración
exigen `.env` con Postgres real (Supabase) — no corren en CI, sí en
local antes de cada release.

Estrategia completa: [`docs/project/06-testing-and-quality.md`](../docs/project/06-testing-and-quality.md).

---

## Migraciones (Alembic)

Convive con SQL histórico (pre-2026-05-27). Desde el baseline
`20260527120000_baseline.py`, los cambios de esquema se gestionan con
Alembic desde el código Python.

Cada arranque del contenedor ejecuta `alembic upgrade head`
automáticamente antes de uvicorn, así Pedro no necesita SSH al NAS
para aplicar migraciones.

Setup detallado: [`MIGRATIONS.md`](MIGRATIONS.md).

---

## Despliegue en NAS Synology

Documentación operativa completa en
[`docs/project/08-deployment.md`](../docs/project/08-deployment.md):
Docker Compose, reverse proxy DSM, Let's Encrypt, pre-go-live al
dominio definitivo, rollback.

Resumen del flujo:

```bash
# En el NAS (carpeta del proyecto)
git pull
docker-compose build --no-cache
docker-compose up -d

# Verificar
curl -s https://embyzambu.synology.me:8000/health
# {"status":"ok"}
```

El `docker-compose.yml` ejecuta `alembic upgrade head` antes de
arrancar uvicorn. Las migraciones se aplican automáticamente.

---

## Documentación relacionada

| Tema | Documento |
|---|---|
| **Setup completo del repo** | [`docs/project/02-installation-and-setup.md`](../docs/project/02-installation-and-setup.md) |
| **Arquitectura del backend** | [`docs/project/03-project-structure.md`](../docs/project/03-project-structure.md) + [ADRs](../docs/adr/00-index.md) |
| **Variables de entorno detalladas** | [`docs/project/04-configuration.md`](../docs/project/04-configuration.md) |
| **Tests y quality gates** | [`docs/project/06-testing-and-quality.md`](../docs/project/06-testing-and-quality.md) |
| **Seguridad operativa** | [`docs/project/07-security.md`](../docs/project/07-security.md) |
| **Despliegue NAS + dominio** | [`docs/project/08-deployment.md`](../docs/project/08-deployment.md) |
| **Troubleshooting** | [`docs/project/09-troubleshooting.md`](../docs/project/09-troubleshooting.md) |
| **Migraciones Alembic** | [`MIGRATIONS.md`](MIGRATIONS.md) |
| **Política de seguridad** | [`SECURITY.md`](../SECURITY.md) raíz |
