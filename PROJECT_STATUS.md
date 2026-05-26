# PROJECT_STATUS — BuenCholloTech
*Última actualización: 2026-05-26 (tras refactor de buenas prácticas)*

> **⚠️ Revisar este documento antes de migrar a dominio web en producción.**
> Contiene el estado real del proyecto, deuda técnica pendiente y la hoja de ruta completa.

---

## 1. Estado general

**Valoración arquitectónica: 8.7 / 10** (subió desde 7.8 tras el refactor 2026-05-26)

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
| 7 | Tests unitarios (DealService, AlertMatcher, matches_alert) | ✅ Completado (2026-05-26) |
| 8 | Refactor de buenas prácticas para TFM — ver § 3.bis | ✅ Completado (2026-05-26) |

---

### 3.bis  Refactor de buenas prácticas — 2026-05-26

Bloque grande de refactor previo a la entrega del TFM, con auditoría completa
SOLID / DRY / KISS / YAGNI y plan por fases. Resumen:

**Fase 1 — Imprescindibles (P0)**
- `B-01` Sanitizados los mensajes de error internos en `security.py` y
  `main.py`: ya no se filtra `str(exc)` al cliente.
- `F-01` Eliminadas las llamadas directas a Supabase desde el frontend en
  `DealCard`, `Comments`, `routes/index`, `useAuth`, `admin.usuarios`. Nuevo
  módulo backend `comments/` (Clean Arch) y endpoint `GET /admin/users`.
- `F-02` Tipado fuerte en `services/api/client.ts` y servicios (`deals`,
  `categories`, `auth`, `comments`, `products`, `admin users`). Eliminados
  todos los `any` y `null as any`.
- **Bug crítico de datos**: el trigger `handle_new_user` de Supabase había
  sido modificado en producción para insertar `role='admin'`. Restaurado al
  valor original `'user'` (hotfix SQL aplicado por Pedro).

**Fase 2 — Recomendables (P1)**
- `F-02 cont.` Tipado completo de `admin.chollos.tsx`: nuevo tipo `DealForm`,
  helper `dealToForm()`, `DealStatus` literal. Antes 9+ `any`, ahora 0.
  Bonus: `productsApi.previewFromUrl` reemplaza el `fetch` inline.
- `B-02` `DealService` recibe `AlertMatcher` opcional por DI y dispara
  `notify_matching_alerts` internamente en create/update. El router queda
  solo HTTP.
- `B-06` 12 tests unitarios con mocks (sin BD): `DealService` (8) y
  `AlertMatcher` (4).
- `F-06` Helper `errorMessage(e, fallback)` en `lib/errors.ts` reutilizado
  en `admin.categorias`, `admin.tiendas`, `admin.chollos`, `chollo.$slug`.
- `F-05`/`F-07` Constantes y utilidades centralizadas: `lib/constants.ts`
  (`DEAL_STATUS_OPTIONS`, thresholds de temperatura) y `lib/format.ts`
  (`calculateDiscount`, `toDatetimeLocal`, `temperatureColor`).

**Fase 3 — Opcionales (P2/P3)**
- `B-03` Helper `_base_deal_query()` en `DealRepository` centraliza el
  `selectinload(category, subcategory, store)` repetido 6 veces.
- `B-04` `matches_alert(alert, deal)` sale del repo a `alerts/application/
  matching.py` (función pura). 8 tests unitarios adicionales.
- `B-05` `DealCleanerService._safe_run(name, action, default)` elimina el
  patrón triple try/except idéntico.
- `F-04` Schemas Zod en `lib/validation/`: `alertFormSchema` (al menos un
  criterio, max_price > 0, min_discount 1-100) y `dealFormSchema` (título
  3-200, URL afiliada válida, previous_price > current_price).
- `F-03` Split de `admin.chollos.tsx` y `chollo.$slug.tsx`: **pospuesto** y
  documentado como mejora identificada en la memoria. Razón: tras tipar,
  validar y mover orquestación, el SRP funcional ya está cubierto; sólo
  queda el "tamaño de fichero", de bajo valor frente al riesgo de refactor
  antes de la entrega.

**Métricas finales del refactor**
- TypeScript: `tsc --noEmit` 0 errores.
- pytest: 47/49 tests verdes (los 2 fallos restantes son `test_amazon_client.py`,
  preexistentes y sin relación con el refactor).
- ADR-002: ya no hay llamadas directas a Supabase DB salvo Storage (excepción
  aprobada) y un único `update(click_count)` en `chollo.$slug.tsx` pendiente
  de migrar (no crítico, documentado en § 4).

---

## 4. Deuda técnica — Auditoría Mayo 2026 (revisada 2026-05-26)

### 🔴 Alta prioridad

#### ADR-002 — rutas restantes con llamadas directas a Supabase

Tras el refactor del 2026-05-26 la mayoría se han resuelto. Estado actualizado:

| Archivo | Tablas / operaciones | Estado |
|---|---|---|
| `explorar.tsx` | `favorites` (read) | ⬜ Pendiente |
| `index.tsx` | `favorites` (read) | ✅ Migrado a `favoritesApi.getFavorites()` |
| `chollo.$slug.tsx` | `deals` (click_count +1) | ⬜ Pendiente (1 llamada residual: `update click_count`) |
| `alertas.tsx` | `alerts` CRUD completo | ✅ El módulo `alerts` en FastAPI ya existe |
| `alertas.nueva.tsx` | `categories`, `stores`, `alerts` | ✅ Usa `alertsApi`, `categoriesService`, `storesService` |
| `notificaciones.tsx` | `notifications` (read + mark read) | ✅ Módulo `notifications` en FastAPI |
| `perfil.tsx` | `profiles` (read) | ⬜ Pendiente migrar a `authApi.me()` (ya existe) |
| `admin.index.tsx` | Stats varias | ⬜ Pendiente `GET /admin/stats` |
| `admin.usuarios.tsx` | `profiles` con roles | ✅ Endpoint `GET /admin/users` + `adminUsersApi` |
| `DealCard.tsx` | `favorites` toggle | ✅ Migrado a `favoritesApi.toggle()` |
| `Comments.tsx` | `deal_comments`, `comment_votes`, `profiles` | ✅ Nuevo módulo `comments` + `commentsApi` |
| `useAuth.tsx` | `user_roles` | ✅ Migrado a `authApi.me()` |

**Pendiente real**: 4 rutas (`explorar`, `chollo.$slug` click_count, `perfil`, `admin.index`).
Las 3 primeras son sustituciones triviales (los servicios ya existen); la última
requiere crear `GET /admin/stats` en backend.

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
