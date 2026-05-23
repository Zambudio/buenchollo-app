# buenchollo-api

Backend **FastAPI** de BuenCholloTech. Actúa como **API Gateway** centralizado: autenticación, lógica de negocio, acceso a PostgreSQL (Supabase) e integración con Amazon Creators API y OpenAI.

- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## Prerequisitos

- **Python 3.11+** (el contenedor Docker usa `python:3.11-slim`)
- Acceso a un proyecto de **Supabase** (BD PostgreSQL + Auth)
- Credenciales de **Amazon Creators API** y **OpenAI** (opcionales para arrancar, obligatorias para el autocomplete)

---

## Setup local (desarrollo)

```bash
cd buenchollo-api

# 1. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
.venv\Scripts\Activate.ps1         # Windows PowerShell

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con los valores reales (ver sección Variables de entorno)

# 4. Arrancar en modo desarrollo (hot-reload)
uvicorn app.main:app --reload
```

---

## Variables de entorno

Copia `.env.example` a `.env` y rellena cada valor. Nunca subas `.env` al repositorio.

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | ✅ | Conexión asyncpg al pooler de Supabase. Formato: `postgresql+asyncpg://postgres.[REF]:[PWD]@aws-0-[region].pooler.supabase.com:6543/postgres` |
| `SUPABASE_URL` | ✅ | URL del proyecto: `https://[REF].supabase.co` |
| `SUPABASE_KEY` | ✅ | **Service role key** (no la anon key). Empieza por `eyJ...` y tiene `"role":"service_role"` |
| `CORS_ORIGINS` | ✅ | Orígenes CORS permitidos, separados por comas. En local: `*` |
| `OPENAI_API_KEY` | ⚠️ | Necesaria para el autocomplete con IA. Sin ella, el endpoint `/products/preview-from-url` falla |
| `AMAZON_CLIENT_ID` | ⚠️ | Necesaria para el autocomplete de Amazon |
| `AMAZON_CLIENT_SECRET` | ⚠️ | Necesaria para el autocomplete de Amazon |
| `AMAZON_AFFILIATE_TAG` | ⚠️ | Tag de afiliado Amazon (p.ej. `buenchollo0b-21`) |
| `AMAZON_API_VERSION` | — | Versión LWA. Por defecto: `3.2` |
| `APP_ENV` | — | `local` \| `staging` \| `production`. Por defecto: `local` |
| `LOG_LEVEL` | — | `DEBUG` \| `INFO` \| `WARNING`. Por defecto: `INFO` |

> **Nota sobre `SUPABASE_KEY`**: usa siempre la `service_role key`, nunca la `anon key`. El backend la necesita para validar JWTs y acceder a tablas con RLS desactivada.

---

## Estructura del proyecto

```
app/
├── core/
│   ├── config.py        # Settings cargadas desde .env (Pydantic Settings)
│   ├── database.py      # Motor SQLAlchemy async, sesión get_db()
│   ├── security.py      # get_current_user, require_admin
│   └── logging.py       # Configuración de logs estructurados
│
├── modules/             # Cada módulo es independiente
│   ├── deals/
│   │   ├── domain/      # Modelos ORM: Deal, DealVote
│   │   ├── application/ # DealCleanerService (scheduler)
│   │   ├── infrastructure/ # DealRepository — único acceso a BD
│   │   └── api/         # Router FastAPI + schemas Pydantic
│   ├── categories/      # (mismo patrón)
│   ├── stores/          # (mismo patrón)
│   ├── products/
│   │   ├── domain/      # ProductPreview entity + Protocols (DIP)
│   │   ├── application/ # PreviewProductFromUrlUseCase
│   │   └── infrastructure/ # AmazonProductClient, OpenAIAssistant
│   ├── users/           # Endpoint /auth/me
│   └── telegram/        # (pendiente de implementar)
│
├── tests/               # Unitarios e integración
└── main.py              # Entrypoint: lifespan, CORS, routers
```

---

## API Reference

### Públicos (sin autenticación)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado de la API |
| `GET` | `/deals/latest` | Últimos chollos activos (`?limit=8`) |
| `GET` | `/deals/popular` | Chollos más calientes por temperatura (`?limit=4`) |
| `GET` | `/deals` | Buscar chollos (`?category_id=&store_id=&search=&limit=20`) |
| `GET` | `/deals/{slug}` | Detalle de un chollo por slug |
| `GET` | `/categories` | Listado de categorías |
| `GET` | `/stores` | Listado de tiendas |

### Requieren JWT (`Authorization: Bearer <token>`)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/auth/me` | Diagnóstico: usuario, roles y perfil |
| `POST` | `/deals/{id}/vote` | Votar un chollo (👍/👎, toggle) |
| `GET` | `/deals/{id}/my-vote` | Voto actual del usuario en un chollo |

### Requieren JWT + rol `admin`

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/deals/admin/all` | Todos los chollos (`?status=&limit=200`) |
| `POST` | `/deals/admin` | Crear chollo |
| `PUT` | `/deals/admin/{id}` | Actualizar chollo |
| `DELETE` | `/deals/admin/{id}` | Eliminar chollo |
| `POST` | `/products/preview-from-url` | Preview de producto Amazon con IA |

---

## Autenticación

1. El frontend obtiene el `access_token` de la sesión de Supabase Auth.
2. Lo envía en la cabecera `Authorization: Bearer <token>`.
3. `get_current_user()` llama a `supabase.auth.get_user(token)` con la `service_role key`.
4. `require_admin()` comprueba la tabla `user_roles` en la BD.

Para diagnosticar problemas de sesión en producción: `GET /auth/me` con el token en las DevTools.

---

## Tests

```bash
# Desde buenchollo-api/ con el venv activado
python -m pytest app/tests/ -v
```

Los tests de integración (`test_deals_api.py`, `test_categories_stores_api.py`) necesitan el `.env` configurado porque conectan con la BD real de Supabase.

Los tests unitarios (`test_preview_use_case.py`) usan mocks y no necesitan credenciales.

---

## Despliegue en NAS Synology (Docker)

### Primera vez

```bash
# En el NAS, desde la carpeta del proyecto (p.ej. /volume1/docker/buenchollo-api)
docker-compose build
docker-compose up -d
```

### Actualizar tras cambios en el código

```bash
# El volumen .:/app hace que los cambios de código se reflejen sin rebuild
docker-compose restart

# Si cambiaron requirements.txt o el Dockerfile:
docker-compose build --no-cache && docker-compose up -d
```

### Verificar que funciona

```
GET https://[tu-ddns]:8000/health
→ {"status": "ok", "app": "BuenChollo API", "environment": "production"}
```

### Configuración de producción

El archivo `docker-compose.yml` monta el directorio del proyecto como volumen (`.:/app`), por lo que los cambios de código en el NAS se reflejan sin rebuild. El `.env` debe estar en la misma carpeta que `docker-compose.yml`.

> **CORS en producción**: configura `CORS_ORIGINS` con los dominios exactos del frontend. Ejemplo: `CORS_ORIGINS=https://tudominio.com,https://www.tudominio.com`

---

## Scheduler (tareas automáticas)

`DealCleanerService` se ejecuta cada día a las **03:00 AM** vía APScheduler:
- Marca como `expired` los chollos con `expires_at` pasado.
- Se arranca y para automáticamente con el `lifespan` de FastAPI en `main.py`.

---

## Solución de problemas frecuentes

**Puerto 8000 ocupado (Windows)**
```powershell
netstat -ano | Select-String ':8000'
Stop-Process -Id <PID> -Force
```

**Error `statement_cache_size` al conectar con PostgreSQL**  
Asegúrate de que `DATABASE_URL` apunta al pooler de PgBouncer (puerto **6543**, no 5432). La configuración en `database.py` ya incluye `statement_cache_size=0` para compatibilidad.

**`La librería creators no está instalada`**  
Este error ya no debería ocurrir. El cliente Amazon fue reescrito usando `requests` directamente (sin SDK externo). Si aparece, revisa que estás usando el código más reciente.
