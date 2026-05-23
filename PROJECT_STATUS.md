# PROJECT_STATUS — BuenCholloTech
*Última actualización: Mayo 2026*

> **⚠️ Revisar este documento antes de migrar a dominio web en producción.**
> Contiene el estado real del proyecto, deuda técnica pendiente y la hoja de ruta completa.

---

## 1. Estado general

**Valoración arquitectónica: 7.8 / 10**

El proyecto tiene una base sólida y está en producción funcionando. Las decisiones técnicas
(Clean Architecture, DIP con Protocols, async/await, PgBouncer) son correctas y defendibles
académicamente para el TFM. La deuda pendiente es de consistencia, no de diseño fundamental.

---

## 2. Principios de arquitectura (no negociables)

1. **El router solo habla HTTP** — recibe request, llama al caso de uso, devuelve respuesta. Sin SQL ni lógica de negocio.
2. **Casos de uso en `application/`** — toda la orquestación va ahí, independiente de FastAPI y de la BD.
3. **El repositorio es el único que toca la BD** — ningún `session.execute()` fuera de `infrastructure/`.
4. **Módulos sin acoplamiento cruzado** — `deals` no importa de `products`. Lo compartido va a `core/`.
5. **Un proveedor externo = un adaptador en `infrastructure/`** — añadir AliExpress = crear `aliexpress_client.py` que implemente `ProductPreviewProvider`. Nada más cambia.
6. **ADR-002: el frontend nunca llama a Supabase DB directamente** — toda la lógica de datos pasa por FastAPI. Excepción aprobada: Supabase Auth y Storage.

---

## 3. Historial de refactorización completada

| Fase | Tarea | Estado |
|---|---|---|
| 1 | Documentación y onboarding | ✅ Completado |
| 2 | Limpiar router deals — extraer `DealService`, `auto_slug`, FK check | ✅ Completado |
| 3 | Favoritos vía FastAPI — eliminar `supabase.from("favorites")` del frontend | ✅ Completado |
| 4 | Stores CRUD admin — panel de gestión de tiendas | ✅ Completado |
| 5 | Scheduler — activación programada, expiración automática, limpieza al arrancar | ✅ Completado |
| 6 | Telegram — panel completo con preview, GPT, categorías, canales, emojis Premium | ✅ Completado |
| 7 | Tests actualizados | ⬜ Pendiente |

---

## 4. Deuda técnica — Auditoría Mayo 2026

### 🔴 Alta prioridad

#### ADR-002 incumplido en el frontend — múltiples rutas

El problema más extendido del proyecto. Estas rutas siguen llamando a Supabase directamente
en lugar de pasar por FastAPI:

| Archivo | Tablas / operaciones | Tarea backend necesaria |
|---|---|---|
| `explorar.tsx` | `favorites` (read) | Endpoint `GET /deals?with_favorites=true` o incluir `is_favorited` en DealCard |
| `index.tsx` | `favorites` (read) | Mismo que arriba |
| `chollo.$slug.tsx` | `deals` (click_count +1, comment_count) | `POST /deals/{id}/click`, o contador en BD via trigger |
| `alertas.tsx` | `alerts` CRUD completo | Módulo `alerts` en FastAPI |
| `alertas.nueva.tsx` | `categories`, `stores`, `alerts` | Módulo `alerts` + reutilizar endpoints existentes |
| `notificaciones.tsx` | `notifications` (read + mark read) | Módulo `notifications` en FastAPI |
| `perfil.tsx` | `profiles` (read) | `GET /users/me/profile` o ampliar `GET /auth/me` |
| `admin.index.tsx` | Stats: deals, favorites, alerts, comments, profiles | `GET /admin/stats` endpoint |
| `admin.usuarios.tsx` | `profiles` con roles (read) | `GET /admin/users` endpoint |

**Excepción aprobada (no tocar):** `login.tsx`, `registro.tsx` — usan Supabase Auth directamente, correcto por diseño.

---

### 🟡 Media prioridad

#### Capas incompletas en módulos menores

`categories/`, `stores/` y `users/` van directamente `router → repository` sin capa `application/`.
Funcional pero inconsistente con la arquitectura declarada.

```
deals/        ✅  api → DealService → DealRepository
products/     ✅  api → PreviewProductFromUrlUseCase → adapters
categories/   ⚠️  api → repository  (sin application layer)
stores/       ⚠️  api → repository  (sin application layer)
users/        ⚠️  api → repository  (sin application layer)
telegram/     ✅  api → TelegramPostGenerator → infrastructure
```

Para `categories` y `stores` (lógica CRUD simple) es aceptable.
Para `users` (gestión de perfiles, roles) debería tener su capa de uso.

#### `__init__.py` faltantes en subdirectorios

Python 3.3+ funciona sin ellos (namespace packages), así que no rompe nada.
Pero es mala práctica: problemas con linters, IDEs y herramientas de testing.

Faltan en: `deals/api/`, `deals/domain/`, `deals/infrastructure/`,
`categories/` (y todos sus subdirectorios), `stores/` (ídem), `users/` (ídem), `telegram/api/`.

#### `test_amazon_client.py` desactualizado

El cliente Amazon fue reescrito a HTTP directo pero el test sigue mockeando el SDK antiguo.
Es el único test roto conocido.

---

### 🟢 Baja prioridad

- **`admin.index.tsx` stats**: para lectura admin es tolerable, pero lo correcto es `GET /admin/stats`
- **Sin excepciones de dominio propias**: solo existe `ProductNotFoundError`. El resto usa `HTTPException` directamente en routers, mezclando protocolo HTTP con lógica de negocio.
- **Sin READMEs de setup**: `CLAUDE.md` cubre decisiones técnicas pero no "cómo arrancar desde cero"

---

## 5. Pendientes antes de migrar a dominio web en producción

> Esta sección es la checklist de producción. No migrar al dominio hasta completarla.

### Obligatorio
- [ ] **Variables de entorno de producción** revisadas: `CORS_ORIGINS` con el dominio real, `APP_ENV=production`, `LOG_LEVEL=WARNING`
- [ ] **CORS configurado** con el dominio exacto (no `*`) antes del go-live
- [ ] **Supabase RLS** revisado: confirmar que las tablas `deals`, `favorites`, `deal_votes`, `deal_comments` tienen políticas RLS activas
- [ ] **Dockerfile** probado con `docker build` limpio desde el repo (no desde imagen cacheada)
- [ ] **`categories.json`** del backend sincronizado con el catálogo definitivo de Telegram

### Muy recomendable
- [ ] Migrar `explorar.tsx` e `index.tsx` a `favoritesApi` (ADR-002 — impacta a todos los usuarios)
- [ ] `GET /admin/stats` para `admin.index.tsx` (elimina 6 queries directas a Supabase)
- [ ] Reparar `test_amazon_client.py` y ejecutar suite completa antes del despliegue
- [ ] README de setup (backend + frontend) para onboarding

### Opcional (mejora calidad)
- [ ] `__init__.py` en todos los subdirectorios de módulos
- [ ] Módulo `alerts` y `notifications` en FastAPI
- [ ] Capa `application/` en `users/`

---

## 6. Cómo escalar a nuevos proveedores (AliExpress, PCComponentes…)

La arquitectura ya está preparada. Para añadir AliExpress:

```
1. Crear buenchollo-api/app/modules/products/infrastructure/aliexpress_client.py
   └── class AliexpressProductClient:
           def get_product_preview(url: str) -> ProductPreview | None
           # Implementa el Protocol ProductPreviewProvider

2. Registrar el adaptador en products/api/router.py como nueva dependencia.
   El caso de uso PreviewProductFromUrlUseCase no cambia nada.

3. El campo Deal.source ya existe para identificar el origen del chollo.

Nada más. deals, categories, stores, users, telegram: sin tocar.
```

---

## 7. Arquitectura objetivo (referencia)

```
buenchollo-api/
├── app/
│   ├── core/           # config, database, security, logging
│   └── modules/
│       ├── deals/
│       │   ├── domain/        # Deal, DealVote, Favorite — modelos ORM + lógica pura
│       │   ├── application/   # DealService, DealCleanerService
│       │   ├── infrastructure/# DealRepository
│       │   └── api/           # router (solo HTTP) + schemas Pydantic
│       ├── products/
│       │   ├── domain/        # ProductPreview, Protocols (DIP)
│       │   ├── application/   # PreviewProductFromUrlUseCase
│       │   └── infrastructure/# AmazonClient, OpenAIClient, [AliexpressClient]
│       ├── categories/        # mismo patrón — pendiente application layer
│       ├── stores/            # mismo patrón — pendiente application layer
│       ├── users/             # mismo patrón — pendiente application layer
│       ├── telegram/          # api + application (post_generator) + infrastructure
│       ├── alerts/            # ⬜ pendiente crear módulo
│       └── notifications/     # ⬜ pendiente crear módulo

buenchollo-web/
├── src/
│   ├── services/api/  # Única capa que habla con FastAPI (apiClient)
│   ├── routes/        # Páginas — solo llaman a services/api/ o Supabase Auth/Storage
│   ├── components/    # UI sin lógica de datos
│   └── hooks/         # useAuth, otros hooks de estado
```
