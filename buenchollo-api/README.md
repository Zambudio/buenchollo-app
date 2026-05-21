# buenchollo-api

Backend **FastAPI** de BuenCholloTech. Actúa como **API Gateway** centralizado: gestiona autenticación, lógica de negocio, acceso a la base de datos (SQLAlchemy + Supabase PostgreSQL) e integración con Amazon y OpenAI.

Documentación interactiva (Swagger): `http://localhost:8000/docs`

---

## Requisitos

- Python 3.12+. Validado con Python 3.14.
- `asyncpg` instalado para la versión de Python que uses.
- Variables de entorno configuradas en `.env` (ver `.env.example`).
- Ejecutar todos los comandos desde la carpeta `buenchollo-api/`.

---

## Instalación y arranque local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Crear .env a partir del ejemplo y rellenar credenciales
cp .env.example .env

# 3. Arrancar en modo desarrollo (hot-reload)
python -m uvicorn app.main:app --reload
```

**Endpoints de comprobación:**

```
GET  http://localhost:8000/health     → {"status": "ok", ...}
GET  http://localhost:8000/auth/me    → info del usuario autenticado (requiere JWT)
GET  http://localhost:8000/docs       → Swagger UI
```

---

## Variables de entorno

Ver [`.env.example`](.env.example) para la referencia completa y comentada.

Las más importantes:

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...@pooler.supabase.com:6543/postgres` |
| `SUPABASE_URL` | `https://[ref].supabase.co` |
| `SUPABASE_KEY` | **Service role key** (no la anon key) |
| `CORS_ORIGINS` | Orígenes permitidos, separados por comas. En local: `*` |
| `OPENAI_API_KEY` | Clave de OpenAI |
| `AMAZON_CLIENT_ID / SECRET` | Credenciales Amazon Creators API |

> ⚠️ Nunca subas `.env` al repositorio.

---

## Estructura de módulos

```
app/
├── core/
│   ├── config.py        # Settings (Pydantic Settings, .env)
│   ├── database.py      # Motor SQLAlchemy async, sesión get_db
│   ├── security.py      # JWT validation (get_current_user, require_admin)
│   └── logging.py       # Configuración de logs
│
├── modules/
│   ├── deals/           # Chollos — modelo, repositorio, router, schemas
│   ├── categories/      # Categorías y subcategorías
│   ├── stores/          # Tiendas
│   ├── products/        # Preview desde Amazon (scraping + IA)
│   └── users/           # Auth: endpoint /auth/me
│
├── tests/
│   ├── test_deals_api.py          # Integración: ciclo completo CRUD admin
│   ├── test_products_api.py       # Productos
│   ├── test_product_preview_use_case.py
│   └── test_amazon_client.py
│
└── main.py              # Entrypoint: lifespan, CORS, routers
```

---

## API Reference

### 🔓 Públicos

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado de la API |
| `GET` | `/deals/latest` | Últimos chollos activos (`?limit=8`) |
| `GET` | `/deals/popular` | Chollos más calientes por temperatura (`?limit=4`) |
| `GET` | `/deals` | Buscar chollos (`?category_id=&store_id=&search=&limit=20`) |
| `GET` | `/deals/{slug}` | Detalle de un chollo por slug |
| `GET` | `/categories` | Listado de categorías |
| `GET` | `/stores` | Listado de tiendas |

### 🔐 Requieren JWT de Supabase (`Authorization: Bearer <token>`)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/auth/me` | Diagnóstico: usuario, roles y perfil |

### 🔐🔴 Requieren JWT + rol `admin`

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/deals/admin/all` | Todos los chollos (`?status=&limit=200`) |
| `POST` | `/deals/admin` | Crear chollo |
| `PUT` | `/deals/admin/{id}` | Actualizar chollo |
| `DELETE` | `/deals/admin/{id}` | Eliminar chollo |
| `POST` | `/products/preview-from-url` | Preview de producto Amazon con IA |

### Ejemplo — Preview de Amazon con IA

```bash
curl -X POST http://localhost:8000/products/preview-from-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.amazon.es/dp/B0DTHWQJXN"}'
```

Respuesta: título, precio, imágenes, descripción generada por GPT-4o, categoría sugerida y texto para Telegram.

---

## Autenticación y roles

El backend valida JWTs emitidos por **Supabase Auth**:

1. El frontend obtiene el `access_token` de la sesión de Supabase.
2. Lo envía en la cabecera `Authorization: Bearer <token>`.
3. `get_current_user` llama a `supabase.auth.get_user(token)` para verificarlo.
4. `require_admin` comprueba el rol en la tabla `user_roles` mediante la función `has_role()` de la BD.

> Para diagnosticar problemas de sesión en producción, llama a `GET /auth/me` con las DevTools abiertas.

---

## Tests

```bash
python -m pytest app/tests/ -v
```

El test de integración `test_deals_api.py` requiere conexión real a la BD de Supabase (usa `.env`) y prueba el ciclo completo: crear chollo → actualizarlo → borrarlo.

---

## Despliegue en NAS

Ver [`DEPLOY_NAS.md`](DEPLOY_NAS.md) y [`docs/NAS_DEPLOYMENT_ARCHITECTURE.md`](docs/NAS_DEPLOYMENT_ARCHITECTURE.md).

Flujo resumido:
1. Copiar archivos modificados al NAS (carpeta `/volume1/docker/buenchollo-api`).
2. Reconstruir y relanzar el contenedor:
   ```bash
   sudo docker-compose up -d --build
   ```
3. Verificar: `https://embyZambu.synology.me:8000/health`

---

## Tareas del scheduler

El proceso de limpieza (`DealCleanerService`) se ejecuta automáticamente cada día a las 03:00 AM vía APScheduler. Elimina chollos caducados (`expires_at` pasado) o los marca como `expired`. Se gestiona mediante el `lifespan` de FastAPI en `main.py`.

---

## Si el puerto 8000 está ocupado (Windows)

```powershell
netstat -ano | Select-String ':8000'
Stop-Process -Id <PID> -Force
python -m uvicorn app.main:app --reload
```
