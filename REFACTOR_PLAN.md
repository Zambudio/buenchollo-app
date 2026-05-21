# Auditoría Técnica y Plan de Refactorización - BuenCholloTech

## 1. Resumen ejecutivo

El proyecto partía de una **grave discrepancia arquitectónica** respecto al ADR-001: la implementación real había derivado en un patrón **BaaS directo** donde el frontend React llamaba a Supabase sin intermediario, dejando FastAPI como microservicio satélite para scraping y OpenAI.

La refactorización completa corrige esto migrando a un patrón **API Gateway**: FastAPI centraliza toda la lógica de negocio, el frontend solo habla con FastAPI, y Supabase queda como proveedor de infraestructura (PostgreSQL, Auth, Storage).

**Estado final: refactorización completada. 19 de Mayo de 2026.**

---

## 2. Problemas detectados en el estado inicial

| Área | Problema | Riesgo |
|---|---|---|
| Arquitectura backend | FastAPI actuaba como microservicio secundario; no controlaba datos ni lógica de negocio | Alto |
| Arquitectura frontend | Llamadas directas a `supabase.from()` en componentes React (Home, Explorar, Admin) | Alto |
| Módulos backend | Estructura presente pero vacía; `deals` solo tenía cron, `telegram` vacío | Medio |
| Clean Architecture | `PreviewProductFromUrlUseCase` instanciaba clientes concretos (violación DIP) | Medio |
| Modelos y BD | Sin SQLAlchemy ni modelos ORM en el backend | Crítico |
| Seguridad | CORS abierto a `*`, `.env.example` incompleto, `SUPABASE_KEY` era la anon key | Alto |
| Testing | Sin tests en el backend | Medio |

---

## 3. Plan de Refactorización — Estado final

### Fase 1: Cimientos del Backend
- [x] Instalar y configurar `SQLAlchemy` y `Alembic`.
- [x] Configurar conexión a PostgreSQL (Supabase) con asyncpg + PgBouncer (`statement_cache_size=0`, `Uuid(as_uuid=False)`).
- [x] Crear modelos de dominio: `Deal`, `Category`, `Store`, `Profile`.
- [x] Crear repositorios base para acceder a los datos.

### Fase 2: API REST
- [x] Schemas Pydantic de entrada/salida separados de los modelos ORM.
- [x] Endpoints REST: chollos, categorías, tiendas, productos.
- [x] Autenticación JWT con `require_admin` — consulta directa a `user_roles` con `service_role key`.

### Fase 3: Desacople del Frontend
- [x] Capa `src/services/api/` en el frontend con `apiClient` (Bearer token automático).
- [x] Lectura pública migrada: Home, Explorar, Detalle de Chollo.
- [x] Panel de administración migrado: CRUD de chollos y categorías vía FastAPI.
- [x] Resuelto conflicto de tipos UUID entre SQLAlchemy y asyncpg.

### Fase 4: Clean Architecture y Correcciones
- [x] DIP en `PreviewProductFromUrlUseCase`: Protocols `ProductPreviewProvider`, `CategoryClient`, `AIEnricher`.
- [x] Scheduler movido a `lifespan()` en `main.py` (patrón oficial FastAPI).
- [x] CORS migrado a `CORSMiddleware` oficial con `CORS_ORIGINS` configurable por `.env`.
- [x] `.env.example` completo y documentado.
- [x] `require_admin` corregido: eliminado `has_role()` problemático con asyncpg, consulta directa a `user_roles`.
- [x] `create_deal` corregido: `model_dump(exclude_none=True)` para no sobreescribir `server_default` con NULL.
- [x] FK `deals.created_by → profiles.user_id` resuelta importando el modelo `Profile` en `deals/domain/models.py`.
- [x] Endpoint `/auth/me` para diagnóstico de sesión JWT en producción.

### Fase 5: Consolidación
- [x] **29 tests pasando, 0 warnings propios.**
  - `test_preview_use_case.py` — 7 tests unitarios con mocks de Protocols (sin red).
  - `test_categories_stores_api.py` — 8 tests de integración contra BD real.
  - `test_deals_api.py` — ciclo completo create/update/delete contra BD real.
  - `test_products_api.py` — endpoints de preview y health.
  - `conftest.py` refactorizado: fixture `integration_client` de sesión compartida.
  - `pytest.ini` con `filterwarnings` para silenciar DeprecationWarnings de FastAPI/Starlette (Python 3.14).
- [x] ADR-001: documento de arquitectura inicial (`docs/adr/ADR-001-monolito-modular-fastapi.md`).
- [x] ADR-002: decisión de migración BaaS → API Gateway (`docs/adr/ADR-002-migracion-baas-a-api-gateway.md`).
- [x] Documentación actualizada: README raíz, `buenchollo-api/README.md`, `docs/SUPABASE_SETUP.md`, `TODO.md`.
- [x] `CLAUDE.md` creado con contexto del proyecto e instrucciones para el asistente IA.

---

## 4. Arquitectura resultante

```
ANTES:
  Browser ──► Supabase (PostgREST / Auth / Storage)
  Browser ──► FastAPI  (scraping, OpenAI)

DESPUÉS:
  Browser ──► FastAPI (toda la lógica de negocio)
                ├──► PostgreSQL / Supabase DB (SQLAlchemy async)
                ├──► Supabase Auth (validación JWT con service_role key)
                ├──► Supabase Storage (subida directa desde cliente — excepción deliberada)
                └──► APIs externas (Amazon Creators API, OpenAI)
```

---

## 5. Pendientes para próximas iteraciones

- [ ] **Telegram**: migrar `notify-telegram` de Supabase Functions a `POST /telegram/notify` en FastAPI.
- [ ] **Alembic**: configurar migraciones desde el backend (actualmente el esquema se gestiona desde Supabase).
- [ ] **Scheduler**: activación automática de chollos `scheduled` cuando llegue `scheduled_for`.
- [ ] **Votos**: endpoint en FastAPI para el sistema de temperatura desde el frontend.
- [ ] **Favoritos**: endpoint en FastAPI para favoritos por usuario.
- [ ] **Gestión de Tiendas**: CRUD de tiendas desde el panel admin.
- [ ] **CI/CD**: automatizar build y despliegue al NAS.

---

*Refactorización completada: 19 de Mayo de 2026.*
