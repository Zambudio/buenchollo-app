# Catálogo permanente — Fase 1 — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que los chollos no se borren: revisión diaria de precio/stock que termina y reactiva ofertas (aviso al canal Admin), purga solo tras 30 días sin disponibilidad, y modelo `products` + `product_listings` como base del catálogo.

**Architecture:** Nuevo módulo `app/modules/catalog/` (domain: modelos + reglas puras; infrastructure: repositorio; application: servicio de reactivación). La tarea programada `price_check` existente se reconvierte: evalúa listings (no deals), aplica transiciones y registra cada transición en `scheduled_task_run_items`. `deals` sigue siendo la oferta y la página pública.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, Alembic, pytest; React + TypeScript + TanStack Router/Query, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-05-catalogo-permanente-design.md`

## Global Constraints

- Trabajo solo en `C:\Users\fadwe\dev\bct-develop` (rama `develop`). Nunca cambiar de rama en el share del NAS.
- Tests backend: `cd buenchollo-api` y, con las variables de la CI exportadas
  (`DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test SUPABASE_URL=https://test.supabase.co SUPABASE_KEY=dummy SUPABASE_JWT_SECRET=dummy`),
  `"$LOCALAPPDATA/BuenCholloLocal/api-venv/Scripts/python.exe" -m pytest -m "not integration" -q -p no:cacheprovider`. Línea base: 562 passed.
- UUIDs `Uuid(as_uuid=False)`; FK entre módulos importando el modelo destino; schemas Pydantic separados del ORM.
- Amazon: solo precio vigente sobrescrito; **ningún** histórico de precios.
- Valores por defecto: `price_tolerance_percent` 10, `min_discount_percent` 5, `purge_after_days` 30, antispam Admin 7 días.
- Migración reversible, idempotente, corre en `alembic upgrade head` al arrancar el contenedor.
- Frontend mobile-first, sin desbordamiento a 375 px; todo HTTP por `apiClient`.
- Commits en inglés terminando en `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push a `origin develop` tras cada tarea.
- Doc (PROJECT_STATUS / TD) en el mismo commit del cambio que la motiva.

## Review Focus

1. **Fallo de Amazon (lote con error de red/5xx):** no se toca ni precio ni disponibilidad de ese lote; ninguna oferta termina por ello → test en Task 4.
2. **Ítem ausente en una respuesta 200:** cuenta como `not_found`, inicia `unavailable_since` pero no se purga hasta 30 días; volver a aparecer limpia `unavailable_since` → tests en Tasks 2 y 4.
3. **Reactivación repetida a diario del mismo producto:** solo un aviso al canal Admin cada 7 días salvo precio menor; las alertas de usuario siguen el mismo antispam → test en Task 5.
4. **Deals `draft`/`scheduled` y `expired` por fecha o manual:** se actualiza el precio (los expired) pero nunca se reactivan solos → test en Task 2.
5. **Migración con varios deals para el mismo ASIN y deals sin ASIN:** ningún deal pierde votos ni se borra; solo uno queda como principal → test de integración en Task 1.

---

### Task 1: Modelos y migración del catálogo

**Files:**
- Create: `buenchollo-api/app/modules/catalog/__init__.py`, `catalog/domain/__init__.py`, `catalog/domain/models.py`
- Modify: `buenchollo-api/app/modules/deals/domain/models.py` (columnas nuevas en `Deal`)
- Modify: `buenchollo-api/app/modules/scheduled_tasks/domain/models.py` (`ScheduledTaskRunItem.transition`)
- Modify: `buenchollo-api/alembic/env.py` si importa modelos explícitamente (registrar `catalog`)
- Create: `buenchollo-api/alembic/versions/20261105120000_permanent_catalogue.py` (`down_revision = "20261103140000"`)
- Test: `buenchollo-api/app/tests/test_catalog_models.py`, `app/tests/test_catalog_migration_integration.py` (marca `integration`)

**Interfaces:**
- Produces:
  - `Product` (`products`): `id, slug (unique), title, brand, description, short_description, image_url, images (JSON), category_id, subcategory_id, gtin, status ('active'|'discontinued'), created_at, updated_at`; `listings` relationship.
  - `ProductListing` (`product_listings`): `id, product_id (FK CASCADE), store_id (FK SET NULL), source ('amazon'|'manual'), external_id, canonical_url, affiliate_url, current_price, reference_price, discount_percentage, in_stock (bool|None), availability ('available'|'unavailable'|'not_found'|'unknown'), unavailable_since, last_checked_at, created_at, updated_at`; `UniqueConstraint(store_id, external_id)`; índice `(source, availability)`.
  - `Deal` nuevas: `product_id (FK products SET NULL)`, `listing_id (FK product_listings SET NULL)`, `offer_end_reason: str|None`, `offer_price: Numeric(10,2)|None`, `last_price_check_at`, `admin_notified_at`, `admin_notified_price`. Índice en `listing_id`.
  - `ScheduledTaskRunItem.transition: str` (`'offer_ended'|'reactivated'|'purged'`, default `'offer_ended'` para filas antiguas).

- [ ] **Step 1: Test de modelos** — `test_catalog_models.py`: `Product.__tablename__ == "products"`, `ProductListing.__table__` tiene la unique `(store_id, external_id)`, `Deal.__table__.c` contiene las 7 columnas nuevas, `ScheduledTaskRunItem.__table__.c.transition` existe.
- [ ] **Step 2: Ejecutar y ver que falla** (ImportError de `catalog.domain.models`).
- [ ] **Step 3: Implementar modelos.**
- [ ] **Step 4: Migración.** `upgrade()`:
  1. Crear `products`, `product_listings`, columnas de `deals`, `scheduled_task_run_items.transition` (server_default `'offer_ended'`).
  2. Backfill en SQL: clave de grupo `g = CASE WHEN external_id IS NOT NULL THEN coalesce(store_id::text,'-') || ':' || upper(external_id) ELSE id::text END`. Representante del grupo = `DISTINCT ON (g) ORDER BY g, published_at DESC`. Un `product` (slug = slug del representante) y un `listing` por grupo (`source = 'amazon'` si `canonical_url ILIKE '%amazon.%'` o el nombre de la tienda `ILIKE 'amazon%'`, si no `'manual'`; `availability = 'unknown'`; precios copiados del representante). Todos los deals del grupo → `product_id`, `listing_id`. `offer_price = current_price` en todos.
  3. Si un grupo tiene más de un deal `active`, los no representantes → `status='expired'`, `offer_end_reason='manual'`.
  4. `UPDATE scheduled_tasks SET enabled = true, frequency_preset = 'daily', config = config::jsonb || '{"min_discount_percent": 5, "purge_after_days": 30}' WHERE task_type = 'price_check'` (respetando `price_tolerance_percent` existente; `config` es `json`: castear a jsonb y de vuelta).
  `downgrade()`: quitar columnas y tablas en orden inverso; los deals quedan intactos.
- [ ] **Step 5: Test de integración** — en la BD local (`bct-local.cmd start`, DATABASE_URL local): dentro de una transacción revertida, insertar 3 deals (2 con mismo ASIN — uno active y otro expired —, 1 sin ASIN) + 1 voto, ejecutar el SQL de backfill (exponerlo como función `backfill_catalog(conn)` en el módulo de migración para poder llamarla), y comprobar: 2 productos, 2 listings, los 3 deals con `product_id`, el voto sigue, solo el más reciente active.
- [ ] **Step 6:** `alembic upgrade head` y `alembic downgrade -1` y `upgrade head` contra la BD local sin errores.
- [ ] **Step 7: Suite unitaria verde y commit** — `feat(catalog): products and listings model with lossless backfill`.

### Task 2: Reglas de oferta (dominio puro)

**Files:**
- Create: `buenchollo-api/app/modules/catalog/domain/offer_rules.py`
- Test: `buenchollo-api/app/tests/test_offer_rules.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True)
  class Observation:            # lo que devolvió la tienda para un listing
      found: bool               # False = ausente en respuesta correcta (not_found)
      in_stock: bool
      price: Decimal | None
      reference_price: Decimal | None
      discount_percentage: int | None

  @dataclass(frozen=True)
  class OfferState:             # lo relevante del deal principal
      status: str               # 'active'|'expired'|'draft'|'scheduled'
      offer_end_reason: str | None
      offer_price: Decimal | None
      previous_price: Decimal | None

  @dataclass(frozen=True)
  class RulesConfig:
      tolerance_percent: Decimal = Decimal("10")
      min_discount_percent: int = 5

  Decision = Literal["keep", "end", "reactivate", "none"]
  def decide(state: OfferState, obs: Observation, cfg: RulesConfig) -> tuple[Decision, str | None]
  def availability_of(obs: Observation) -> str   # 'available'|'unavailable'|'not_found'
  def rules_config_from(config: dict) -> RulesConfig  # tolerancia fuera de 0..100 o inválida → 10; min_discount inválido → 5
  REACTIVATABLE_REASONS = {"price_increase", "no_longer_deal", "out_of_stock", "not_found"}
  ```
  Semántica (spec 5.2): `active` → `("end", reason)` con prioridad `not_found` > `out_of_stock` > `price_increase` (precio > offer_price×(1+tol)) > `no_longer_deal` (descuento ≤ 0, o `previous_price > offer_price` y precio ≥ previous_price); si no, `("keep", None)`. `expired` con razón en `REACTIVATABLE_REASONS` → `("reactivate", None)` si found y in_stock y precio no nulo y (precio ≤ offer_price o descuento ≥ min); si no `("none", None)`. Cualquier otro estado/razón → `("none", None)`. Precio `None` con found+in_stock en `active` → `("keep", None)`.

- [ ] **Step 1: Tests** (parametrizados), al menos:
  `test_active_sube_mas_de_tolerancia_termina` (offer 100, precio 110.01 → end/price_increase; 110 → keep),
  `test_active_sin_stock_termina_out_of_stock`, `test_active_no_encontrado_termina_not_found`,
  `test_active_descuento_cero_termina_no_longer_deal`,
  `test_active_alcanza_previous_price_termina` (offer 80, previous 100, precio 100 → no_longer_deal),
  `test_active_con_cupon_sin_descuento_informado_se_mantiene` (discount None, precio = offer → keep),
  `test_expired_vuelve_a_su_precio_se_reactiva` (offer 80, precio 80, discount None → reactivate),
  `test_expired_descuento_tienda_5_se_reactiva` (precio 90 > offer 80, discount 5 → reactivate; discount 4 → none),
  `test_expired_por_fecha_o_manual_no_se_reactiva` (`expired_date`, `manual`, None),
  `test_draft_y_scheduled_nunca_cambian`,
  `test_rules_config_from_valores_invalidos` (`{"price_tolerance_percent": 150}` → 10; `"abc"` → 10; `{"min_discount_percent": -1}` → 5),
  `test_availability_of` (not found → not_found; sin stock → unavailable; ok → available).
- [ ] **Step 2: Ver que fallan.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Ver que pasan. Commit** — `feat(catalog): pure offer lifecycle rules`.

### Task 3: Repositorio del catálogo

**Files:**
- Create: `buenchollo-api/app/modules/catalog/infrastructure/__init__.py`, `catalog/infrastructure/repository.py`
- Test: `buenchollo-api/app/tests/test_catalog_repository_integration.py` (marca `integration`, patrón de `test_submission_repository_integration.py`)

**Interfaces:**
- Consumes: modelos de Task 1.
- Produces `CatalogRepository(session)`:
  - `async def get_checkable(self) -> list[tuple[ProductListing, Deal | None]]` — listings `source='amazon'` con `external_id`, cada uno con su deal principal (el más reciente por `published_at` entre los de estado `active`/`expired`; `None` si solo hay draft/scheduled). Deal cargado con `store`, `category`, `subcategory` (como `_base_deal_query`).
  - `async def link_new_deal(self, deal: Deal) -> None` — si existe listing `(store_id, upper(external_id))` lo reutiliza; si no, crea product (slug del deal, datos del deal) + listing (`source` según la misma regla que la migración). Asigna `deal.product_id`, `deal.listing_id`, `deal.offer_price = deal.current_price`. Sin `external_id` → product+listing `manual`.
  - `async def get_purgeable(self, older_than: datetime) -> list[ProductListing]` — `availability IN ('unavailable','not_found') AND unavailable_since <= older_than`.
  - `async def purge_listing(self, listing: ProductListing) -> list[str]` — borra el listing; si el producto conserva otros listings, repunta sus deals al listing `available` más barato (o al primero si ninguno lo está) y devuelve `[]`; si no, borra los deals del producto y el producto y devuelve los ids de deals borrados.
- [ ] **Step 1: Tests de integración** (transacción revertida): `get_checkable` excluye `manual` y elige el deal más reciente; `link_new_deal` reutiliza listing existente con ASIN en minúsculas; `purge_listing` con 2 listings repunta y no borra deals; con 1 listing borra producto, deal y sus votos.
- [ ] **Step 2–4:** fallo → implementar → verde (con la BD local arrancada).
- [ ] **Step 5: Commit** — `feat(catalog): catalogue repository (checkable listings, link, purge)`.

### Task 4: Revisión diaria — reconversión de `price_check`

**Files:**
- Modify: `buenchollo-api/app/modules/scheduled_tasks/application/task_handler.py` (`Candidate` + `transition`)
- Rewrite: `buenchollo-api/app/modules/scheduled_tasks/application/price_check_handler.py`
- Modify: `buenchollo-api/app/modules/scheduled_tasks/application/scheduled_task_service.py`, `application/factory.py`, `application/scheduler.py` (`_build_service`)
- Modify: `buenchollo-api/app/modules/scheduled_tasks/api/router.py`, `api/schemas.py`, `domain/exceptions.py`, `infrastructure/repository.py` (quitar restore)
- Test: rewrite `app/tests/test_price_check_handler.py`, update `test_scheduled_task_service.py`, `test_scheduled_tasks_api.py`, `test_scheduled_tasks_scheduler.py`

**Interfaces:**
- Consumes: `decide`, `availability_of`, `rules_config_from`, `Observation`, `OfferState` (Task 2); `CatalogRepository` (Task 3); `ProductVerifier.get_product_previews` (existente).
- Produces:
  - `Candidate` gana `transition: Literal["offer_ended","reactivated","purged"]`; `reason` admite además `not_found`, `listing_purged`, `product_purged`.
  - `@dataclass class ListingCheck: listing; deal; observation: Observation | None  # None = lote fallido`
  - `PriceCheckHandler(product_verifier, catalog_repo)`:
    - `def fetch(self, pairs: list[tuple[ProductListing, Deal|None]]) -> list[ListingCheck]` (síncrono, en threadpool; lotes de `MAX_ITEMS_PER_REQUEST`; excepción de lote → `observation=None` para todo el lote, log warning).
    - `def evaluate(self, checks: list[ListingCheck], config: dict, now: datetime) -> PreviewResult` — puro; candidatos de `end`/`reactivate` y de purga (listings cuya `unavailable_since` efectiva ≤ now − `purge_after_days`).
    - `async def apply(self, checks, config, now) -> list[Candidate]` — escribe listing (precio, referencia, descuento, in_stock, availability, `last_checked_at`, `unavailable_since`: se fija al pasar a no disponible y se limpia al volver), deal (`current_price`, `previous_price = reference_price` si viene, `discount_percentage`, `savings_amount`, `last_price_check_at`) y transiciones: end → `status='expired'`, `offer_end_reason`; reactivate → `status='active'`, `offer_end_reason=None`, `published_at=now`, `offer_price=precio`. Luego purga vía `catalog_repo.purge_listing`. Observación `None` → no toca nada. Devuelve candidatos aplicados.
  - `ScheduledTaskService`:
    - `async def preview(task_id) -> PreviewResult` (fetch + evaluate, sin escribir).
    - `async def run(task_id, *, trigger_type: Literal["manual","automatic"], triggered_by: str|None) -> tuple[ScheduledTaskRun, list[Candidate]]` — fetch + apply + `_persist_run` (items con `transition`; audit `deal.offer_transition` con `transition`, `reason`, precios) + `last_run_at`. Mismo manejo de fallo/rollback que el `run_automatic` actual.
    - `run_automatic(task_id)` y `confirm(task_id, triggered_by)` delegan en `run`. Se eliminan `restore_item`, `ItemAlreadyRestoredError`, `RestoreFailedError`, `RunItemNotFound`, `get_run_item_by_id`, `update_run_item` y el endpoint `POST /runs/items/{item_id}/restore`.
  - API: `POST /{task_id}/confirm` sin body (si llega body se ignora); devuelve `RunResponse`. `CandidateSchema` y `RunItemResponse` exponen `transition`. `ScheduledTaskUpdate.config` valida `min_discount_percent` 0–90 y `purge_after_days` 7–365 si vienen.
  - Las columnas `restored_at`/`restored_deal_id` se quedan en BD (sin uso) para no tocar datos históricos; se quitan del schema de respuesta.
- [ ] **Step 1: Tests del handler** (fakes como los actuales): `test_lote_fallido_no_toca_nada` (verifier lanza → apply no cambia precio ni estado ni availability), `test_ausente_en_respuesta_marca_not_found_y_fija_unavailable_since`, `test_vuelve_disponible_limpia_unavailable_since`, `test_actualiza_precio_sin_transicion`, `test_end_no_borra_deal` (el fake repo no tiene `delete`), `test_reactivate_fija_offer_price_y_published_at`, `test_purga_tras_purge_after_days` (29 días → no; 30 → sí), `test_lotes_de_10`.
- [ ] **Step 2: Tests del servicio/API:** `confirm` sin body ejecuta `run` con `trigger_type="manual"`; el run persiste items con `transition`; el endpoint restore devuelve 404/405; `run_automatic` con excepción registra run `failed` (test existente adaptado).
- [ ] **Step 3–4:** fallo → implementar → suite completa verde.
- [ ] **Step 5: Commit** — `feat(price-check): update prices daily and toggle offers instead of deleting deals`.

### Task 5: Aviso al canal Admin y alertas en la reactivación

**Files:**
- Create: `buenchollo-api/app/modules/catalog/application/__init__.py`, `catalog/application/reactivation_notifier.py`
- Modify: `buenchollo-api/app/core/config.py` (`public_site_url: str = "https://buenchollotech.com"`)
- Modify: `scheduled_tasks/application/scheduler.py` y `api/router.py` (llamar al notifier tras el commit del run)
- Test: `buenchollo-api/app/tests/test_reactivation_notifier.py`

**Interfaces:**
- Consumes: `Candidate` con `transition == "reactivated"` (Task 4); `TelegramBot.send_admin_notification(text, chat_id)`; `AlertMatcher.notify_matching_alerts(deal)`.
- Produces:
  - `ADMIN_COOLDOWN = timedelta(days=7)`
  - `def should_notify(notified_at: datetime|None, notified_price: Decimal|None, price: Decimal, now: datetime) -> bool` — True si nunca se avisó, si pasaron ≥ 7 días, o si `price < notified_price`.
  - `def build_admin_message(deal, site_url: str) -> str` — texto plano exacto:
    ```
    🔁 Vuelve a estar en oferta
    {title}
    💶 {precio} €{ (antes {previous_price} €, -{discount} %) si hay previous_price}
    🏪 {store.name o "Tienda"}
    🛒 {affiliate_url}
    🌐 {site_url}/chollo/{slug}
    ```
    Precios con formato español (`_format_price_es` de `telegram/application/post_generator.py`).
  - `class ReactivationNotifier(bot, admin_chat_id: str, matcher, deal_repo, site_url)` con `async def notify(self, deal_ids: list[str], now: datetime) -> int` — por cada deal: si `should_notify` → envía al canal Admin (si `admin_chat_id` vacío, solo log) y dispara `matcher.notify_matching_alerts`; si el envío no falla actualiza `admin_notified_at/price`. Un fallo de Telegram no lanza ni revierte. Devuelve avisos enviados.
- [ ] **Step 1: Tests:** `should_notify` (nunca → True; 6 días mismo precio → False; 6 días precio menor → True; 7 días → True); `build_admin_message` con y sin previous_price (comparar string exacto); `notify` con bot fake que falla → no actualiza `admin_notified_at`, no lanza; con cooldown activo no llama al matcher.
- [ ] **Step 2–4:** fallo → implementar → verde.
- [ ] **Step 5: Commit** — `feat(catalog): notify the admin Telegram channel when an offer comes back`.

### Task 6: Retirar el borrado diario

**Files:**
- Modify: `buenchollo-api/app/modules/deals/application/cleaner_service.py` (eliminar `clean_expired_deals`), `deals/application/scheduler.py` (quitar job; `build_deals_scheduler` devuelve `tuple[BackgroundScheduler, DealCleanerService]` igual), `app/main.py` y `app/run_scheduler.py` (quitar la llamada inicial y actualizar logs)
- Test: `app/tests/test_scheduler_builder.py`

- [ ] **Step 1:** Test: los ids/funciones de jobs no incluyen `clean_expired_deals`; `DealCleanerService` no tiene atributo `clean_expired_deals`.
- [ ] **Step 2–4:** fallo → implementar → verde. `grep -rn clean_expired_deals buenchollo-api/app` sin resultados.
- [ ] **Step 5: Commit** — `feat(deals): stop deleting expired deals`.

### Task 7: Alta de un producto ya existente reactiva el anuncio

**Files:**
- Modify: `buenchollo-api/app/modules/deals/application/deal_service.py`
- Modify: `buenchollo-api/app/modules/submissions/application/review_submission.py` (quitar bucle `find_expired_deals` + delete) y `submissions/infrastructure/repository.py` (eliminar `find_expired_deals` si queda sin uso)
- Modify: `deals/api/router.py` / dependencia que construye `DealService` para inyectar `CatalogRepository`
- Test: `app/tests/test_deal_service.py`, `app/tests/test_submission_review.py`, `app/tests/test_schedule_service.py`

**Interfaces:**
- Consumes: `CatalogRepository.link_new_deal` (Task 3).
- Produces: `DealService(repo, matcher=None, catalog=None)`; `create_deal(deal_data, user_id)`:
  - existente por `external_id` y `status == "active"` → `DuplicateDealError` (como hoy);
  - existente no activo (`expired`) → actualiza ese deal con `deal_data` (sin tocar `slug`, votos, `created_at`), `status` el pedido (o `active`), `published_at = now`, `offer_end_reason = None`, `offer_price = current_price`; `created_by = user_id` si tiene perfil; devuelve ese deal (mismo id). Alertas como en un alta.
  - nuevo → como hoy + `catalog.link_new_deal(deal)` antes de devolver.
  - existente en `draft`/`scheduled` → `DuplicateDealError` (como hoy).
- [ ] **Step 1: Tests:** `test_alta_de_asin_expirado_reactiva_mismo_deal` (mismo id y slug, published_at actualizado, offer_price = nuevo precio), `test_alta_de_asin_activo_sigue_dando_duplicado`, `test_alta_nueva_enlaza_catalogo` (fake catalog recibe el deal), `test_aprobar_propuesta_no_borra_expirados` (el fake `deal_service.delete_deal` no se llama; el deal devuelto es el existente; `created_by` = autor de la propuesta).
- [ ] **Step 2–4:** fallo → implementar → verde.
- [ ] **Step 5: Commit** — `feat(deals): re-adding a known product revives its existing deal`.

### Task 8: API pública de deals y sitemap

**Files:**
- Modify: `buenchollo-api/app/modules/deals/api/schemas.py` (`DealDetailResponse`: `offer_end_reason: str | None`, `last_price_check_at: datetime | None`)
- Modify: `buenchollo-web/src/services/api/deals.ts` (tipos), `buenchollo-web/src/routes/sitemap[.]xml.ts` (`.in("status", ["active","expired"])`, `changefreq` `weekly` para expired, prioridad 0.5)
- Test: `app/tests/test_deals_api.py` (el detalle incluye los dos campos)

- [ ] **Step 1–4:** test → fallo → implementar → verde (+ `npx tsc --noEmit` en `buenchollo-web`).
- [ ] **Step 5: Commit** — `feat(deals): expose offer state and last price check; sitemap keeps expired deals`.

### Task 9: Web — ficha y panel

**Files:**
- Modify: `buenchollo-web/src/routes/chollo.$slug.tsx`
- Create: `buenchollo-web/src/features/deals/components/OfferStatusNotice.tsx` + `OfferStatusNotice.test.tsx`
- Modify: `buenchollo-web/src/services/api/scheduled-tasks.ts` (quitar restore; `confirm` sin body; `transition`; config `min_discount_percent`, `purge_after_days`)
- Modify: `buenchollo-web/src/features/admin/components/ScheduledTaskConfigPanel.tsx`, `ScheduledTaskRunDetailDialog.tsx`, `ScheduledTaskRunsPanel.tsx`
- Modify: lista de chollos del admin (`routes/admin.chollos.tsx` o su componente) para mostrar motivo de fin y última comprobación

**Interfaces:**
- Produces: `OfferStatusNotice({ status, offerEndReason, currentPrice, lastPriceCheckAt, storeName, now? })`:
  - `expired`: título «Ahora mismo no está en oferta» + motivo legible (`price_increase` «Ha subido de precio», `no_longer_deal` «Ya no está rebajado», `out_of_stock` «Agotado», `not_found` «Ya no está en la tienda», resto «La oferta ha terminado») + «Precio actual: X € · comprobado hace N h» si la comprobación tiene ≤ 24 h; si > 24 h o nula y la tienda es Amazon: solo «Ver precio en Amazon».
  - `active` con `lastPriceCheckAt`: «Precio comprobado hace N h»; si > 24 h «Precio de hace N días: puede haber cambiado».
- [ ] **Step 1: Tests Vitest** de `OfferStatusNotice`: los 3 casos anteriores con `now` fijo.
- [ ] **Step 2–4:** fallo → implementar → `npx vitest run` + `npx tsc --noEmit` + `npm run lint` verdes.
- [ ] **Step 5: Panel de tareas:** etiquetas de transición («Oferta terminada», «Reactivada», «Eliminada»), sin botón Restaurar, botón «Ejecutar ahora» tras la vista previa, inputs de mínimo descuento y días de purga. Verificar en local a 375 px y escritorio.
- [ ] **Step 6: Commit** — `feat(web): offer status on deal page and transition-based scheduled task panel`.

### Task 10: Verificación en local, documentación y revisión

**Files:**
- Create: `docs/adr/ADR-0xx-catalogo-permanente.md` (siguiente número libre)
- Modify: `PROJECT_STATUS.md`, `docs/project/10-technical-debt.md` (nuevo TD: precio > 24 h en tarjetas si Amazon falla; TD: `restored_*` sin uso), `docs/guides/` si alguna guía describe el borrado de las 03:00
- Modify: `.claude/memory/` (nota del catálogo permanente + índice)

- [ ] **Step 1:** `bct-local.cmd start`; `alembic upgrade head` en la BD local; comprobar conteos: `products` = grupos, ningún deal perdido (`count(*)` de deals y deal_votes antes/después iguales).
- [ ] **Step 2:** Ejecutar la vista previa y «Ejecutar ahora» de `price_check` contra Amazon real en local (Telegram apagado en local: comprobar el log del aviso Admin). Revisar transiciones razonables.
- [ ] **Step 3:** `bct-local.cmd qa` verde; suite unitaria backend verde; `vitest` + `tsc` + lint verdes.
- [ ] **Step 4:** Documentación y commit `docs: permanent catalogue ADR, status and debt`.
- [ ] **Step 5:** Revisión de toda la rama (`superpowers:requesting-code-review`) y corrección de hallazgos.
- [ ] **Step 6:** Push a `develop`. **No** merge a `main`: el despliegue (con `pg_dump` previo) solo cuando Pedro lo pida.
