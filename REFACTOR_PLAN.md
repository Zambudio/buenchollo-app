# Plan de Proyecto — BuenCholloTech
*Revisión: Mayo 2026*

---

## 1. Estado actual — Diagnóstico honesto

### Lo que está bien
- Arquitectura modular en `buenchollo-api/`: módulos `deals`, `products`, `categories`, `stores`, `users` separados.
- Clean Architecture aplicada en `products`: Protocols DIP (`ProductPreviewProvider`, `CategoryClient`, `AIEnricher`), uso correctamente desacoplado de Amazon y OpenAI.
- Frontend con capa `src/services/api/` y `apiClient` con Bearer token automático.
- Auth JWT funcionando con `require_admin` y `get_current_user`.
- SQLAlchemy async + asyncpg + PgBouncer correctamente configurado.
- Votos (`/deals/{id}/vote`) implementados vía FastAPI.
- 29 tests pasando (unitarios + integración).

### Problemas detectados

| # | Problema | Impacto | Prioridad |
|---|---|---|---|
| 1 | **Sin documentación de arranque**: no hay un README que permita clonar el repo y levantar todo desde cero | Bloquea onboarding | 🔴 Alta |
| 2 | **Lógica de negocio en el router de deals**: `_auto_slug`, FK profile check, y el UPDATE de votos viven en `router.py` — los routers solo deben hablar HTTP | Mantenibilidad, tests | 🔴 Alta |
| 3 | **ADR-002 incumplido en frontend**: `favoritos.tsx` llama directamente a `supabase.from("favorites")` | Arquitectura | 🔴 Alta |
| 4 | **Módulo `deals` sin capa application**: no hay casos de uso para crear/actualizar deals — la lógica va Router → Repository saltándose la capa | Escalabilidad | 🟡 Media |
| 5 | **Features pendientes sin implementar**: Favoritos API, Stores CRUD admin, Scheduler activación, Telegram migración | Funcionalidad | 🟡 Media |
| 6 | **`test_amazon_client.py` roto**: el cliente de Amazon fue reescrito pero el test no se actualizó | CI | 🟡 Media |
| 7 | **Carpetas vendored en disco**: `amazon_creatorsapi/`, `creatorsapi_python_sdk/` y el `.whl` siguen en el directorio (aunque gitignoreados) | Limpieza | 🟢 Baja |
| 8 | **`telegram/` vacío**: módulo presente pero sin implementación | Funcionalidad | 🟢 Baja |

---

## 2. Principios que guiarán el trabajo

1. **El router solo habla HTTP**: recibe request, llama al caso de uso, devuelve respuesta. Sin SQL, sin lógica de negocio.
2. **Casos de uso en `application/`**: toda la orquestación va ahí. Independiente de FastAPI y de la BD.
3. **El repositorio es el único que toca la BD**: ningún `session.execute()` fuera de `infrastructure/`.
4. **Módulos sin acoplamiento cruzado**: `deals` no importa de `products`. Si necesitan compartir algo, va a `core/`.
5. **Un proveedor externo = un adaptador en `infrastructure/`**: agregar AliExpress = crear `aliexpress_client.py` que implemente `ProductPreviewProvider`. Nada más cambia.
6. **Documentación como primera ciudadana**: cualquier cambio que afecte al setup o al contrato API → README actualizado.

---

## 3. Plan de acción

### Fase 1 — Documentación y Onboarding 🔴
*Objetivo: cualquier persona (o tú en otro ordenador) puede levantar el proyecto leyendo el README.*

- [ ] **README raíz** (`/README.md`): visión general, estructura del monorepo, prerequisitos.
- [ ] **README backend** (`buenchollo-api/README.md`): 
  - Requisitos (Python 3.11+, Docker, PostgreSQL/Supabase)
  - Setup local: clonar → crear venv → `pip install -r requirements.txt` → configurar `.env` → `uvicorn app.main:app --reload`
  - Setup NAS/producción: cómo construir y levantar el contenedor Docker paso a paso
  - Variables de entorno explicadas una por una
  - Cómo ejecutar los tests
- [ ] **README frontend** (`buenchollo-web/README.md`):
  - Requisitos (Node 18+, pnpm)
  - Setup: clonar → `pnpm install` → configurar `.env.local` → `pnpm dev`
  - Variables de entorno
- [ ] **`.env.example`** revisado y completo (backend y frontend).
- [ ] Limpiar disco: borrar `amazon_creatorsapi/`, `creatorsapi_python_sdk/`, `amazon_creators_sdk-0.1.0-py3-none-any.whl`.

---

### Fase 2 — Limpiar lógica del router de deals 🔴
*Objetivo: `deals/router.py` solo hace HTTP. Toda la lógica baja a su capa correspondiente.*

- [ ] Mover `_auto_slug()` a `deals/domain/` (lógica pura de dominio, sin dependencias).
- [ ] Mover el profile FK check a `DealRepository` como método `user_has_profile(user_id) → bool`.
- [ ] Crear `deals/application/deal_service.py` con `DealService`:
  - `create_deal(data, user_id) → Deal`
  - `update_deal(deal_id, data) → Deal`
  - `delete_deal(deal_id) → None`
- [ ] Mover el UPDATE de votos (el `text("""UPDATE deals...""")`) a `DealRepository.recalculate_votes(deal_id)`.
- [ ] El router queda limpio: solo valida schemas, llama al servicio, devuelve respuesta.

---

### Fase 3 — Completar ADR-002: Favoritos vía FastAPI 🔴
*Objetivo: eliminar la última llamada directa a Supabase desde el frontend (salvo Storage).*

**Backend:**
- [ ] Modelo `Favorite` en `deals/domain/models.py` (tabla `favorites` ya existe en Supabase).
- [ ] Métodos en `DealRepository`: `get_favorites(user_id)`, `add_favorite(deal_id, user_id)`, `remove_favorite(deal_id, user_id)`, `is_favorite(deal_id, user_id) → bool`.
- [ ] Endpoints en `deals/router.py`:
  - `GET /deals/favorites` → lista de deals favoritos del usuario autenticado
  - `POST /deals/{deal_id}/favorite` → marcar/desmarcar favorito (toggle)
- [ ] Añadir `is_favorited` al schema `DealDetailResponse` (solo cuando hay usuario autenticado).

**Frontend:**
- [ ] Añadir `favoritesApi` en `src/services/api/deals.ts`.
- [ ] Migrar `favoritos.tsx` para usar `favoritesApi.getFavorites()`.
- [ ] Migrar `chollo.$slug.tsx`: sustituir `supabase.from("favorites")` por `favoritesApi.isFavorite()`.

---

### Fase 4 — Stores CRUD admin 🟡
*Objetivo: gestionar tiendas desde el panel de admin (actualmente solo hay read-only).*

- [ ] Schemas `StoreCreate`, `StoreUpdate` en `stores/api/schemas.py`.
- [ ] Métodos en `StoreRepository`: `create`, `update`, `delete`.
- [ ] Endpoints admin en `stores/router.py`:
  - `POST /stores/admin`
  - `PUT /stores/admin/{store_id}`
  - `DELETE /stores/admin/{store_id}`
- [ ] Panel admin frontend: UI para crear/editar/eliminar tiendas (similar al de categorías).

---

### Fase 5 — Scheduler: activar chollos programados 🟡
*Objetivo: si un chollo tiene `status="scheduled"` y `scheduled_for` llega, se activa automáticamente.*

- [ ] Nuevo método en `DealRepository`: `get_due_scheduled() → list[Deal]`.
- [ ] Ampliar `DealCleanerService` (o crear `DealSchedulerService`) con `activate_scheduled_deals()`.
- [ ] Registrar job en el scheduler de `main.py` (cada 5 minutos, o cada hora según necesidad).

---

### Fase 6 — Telegram: migrar de Supabase Functions a FastAPI 🟡
*Objetivo: `POST /telegram/notify` en FastAPI reemplaza la Supabase Function.*

- [ ] Implementar `telegram/infrastructure/telegram_bot.py` con el cliente HTTP a la Bot API.
- [ ] Caso de uso `telegram/application/notify_deal.py`.
- [ ] Endpoint `POST /telegram/notify` con `require_admin`.
- [ ] Actualizar el panel admin para llamar al endpoint FastAPI en vez de la Supabase Function.
- [ ] Retirar la Supabase Function.

---

### Fase 7 — Tests 🟡
*Objetivo: suite de tests fiable que cubra lo que se ha construido.*

- [ ] Actualizar `test_amazon_client.py` para el nuevo cliente HTTP directo (mockear `requests.post`).
- [ ] Tests unitarios para `DealService` (mockear repositorio).
- [ ] Tests de integración para los nuevos endpoints: favoritos, stores CRUD.
- [ ] Añadir test de `GET /deals/favorites` con usuario autenticado.

---

## 4. Cómo escalar a nuevos proveedores (AliExpress, PCComponentes…)

La arquitectura ya está preparada. Para añadir AliExpress:

```
1. Crear buenchollo-api/app/modules/products/infrastructure/aliexpress_client.py
   └── class AliexpressProductClient:
           def get_product_preview(url_or_asin: str) -> ProductPreview | None
           # Implementa el Protocol ProductPreviewProvider

2. Registrar el adaptador en products/api/router.py como nueva dependencia.
   (El caso de uso PreviewProductFromUrlUseCase no cambia nada)

3. El Deal.source ya tiene el campo 'source: str' para identificar el origen.

Nada más. deals, categories, stores, users: sin tocar.
```

Este patrón aplica igual para cualquier integración externa: cada fuente es un adaptador independiente en `infrastructure/` que implementa el Protocol del dominio.

---

## 5. Arquitectura objetivo

```
buenchollo-api/
├── app/
│   ├── core/           # config, database, security, logging — compartido
│   └── modules/
│       ├── deals/
│       │   ├── domain/        # Deal, DealVote, Favorite — modelos ORM + lógica pura
│       │   ├── application/   # DealService, DealCleanerService, DealSchedulerService
│       │   ├── infrastructure/# DealRepository — único punto de acceso a BD
│       │   └── api/           # router (solo HTTP), schemas Pydantic
│       ├── products/
│       │   ├── domain/        # ProductPreview entity, Protocols
│       │   ├── application/   # PreviewProductFromUrlUseCase
│       │   └── infrastructure/# AmazonProductClient, AliexpressClient*, OpenAIAssistant
│       ├── categories/        # (mismo patrón)
│       ├── stores/            # (mismo patrón)
│       ├── users/             # (mismo patrón)
│       └── telegram/          # (mismo patrón)

buenchollo-web/
├── src/
│   ├── services/api/  # Única capa que habla con FastAPI
│   ├── routes/        # Páginas — solo llaman a services/api/
│   ├── components/    # UI sin lógica de datos
│   └── hooks/         # useAuth y hooks de estado
```

---

## 6. Orden de ejecución recomendado

Las fases están ordenadas por impacto/dependencia. No empezar la siguiente sin cerrar la anterior.

| Fase | Tarea | Estado |
|---|---|---|
| 1 | Documentación y onboarding | ✅ Completado |
| 2 | Limpiar router deals | ✅ Completado |
| 3 | Favoritos vía FastAPI | ✅ Completado |
| 4 | Stores CRUD admin | ✅ Completado |
| 5 | Scheduler deals programados | ✅ Completado |
| 6 | Telegram migración + panel completo | ✅ Completado |
| 7 | Tests actualizados | ⬜ Pendiente |
