# Chollos de usuarios (propuestas de la comunidad) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Los usuarios registrados comparten chollos (enlace → comprobación de duplicado → formulario, autorrelleno Amazon, imágenes por archivo/URL/portapapeles); el admin los modera por email + panel; al aprobar se publican con nuestro enlace de afiliado y con autoría.

**Architecture:** Módulo nuevo `submissions` (tabla `deal_submissions` separada de `deals`) + módulo de dominio puro `affiliates` (canonicalización y reescritores por tienda). Ingesta de imágenes en backend (Pillow → WebP → Supabase Storage). Al aprobar, el deal se crea con el `DealService` existente (`source='community'`, `created_by=autor`). Frontend: ruta `/publicar` (wizard 2 pasos), `/mis-chollos`, `/admin/propuestas`.

**Tech Stack:** FastAPI · SQLAlchemy async/asyncpg · Alembic · Pillow · httpx · supabase-py Storage · Jinja2/SMTP · React + TanStack Start/Router · TanStack Query · zod · shadcn/ui · sonner · Vitest · Playwright.

**Spec:** `docs/superpowers/specs/2026-11-03-chollos-de-usuarios-design.md` (leerla antes de cada tarea).

## Global Constraints

- Rama `develop`. Commit + push por tarea. **Nunca** tocar `main`.
- Capas `api → application → domain ← infrastructure`; routers sin lógica; dominio sin FastAPI/SQLAlchemy/HTTP.
- UUID: `Uuid(as_uuid=False)`. Migraciones Alembic `buenchollo-api/alembic/versions/YYYYMMDDHHMMSS_slug.py`, `revision` = timestamp, `down_revision = "20261103120000"` para la primera. **Solo cambios aditivos** (BD compartida dev/prod).
- Errores de negocio: subclases de `app/core/exceptions.py` (`ConflictError` 409, `ValidationError` 400, `ForbiddenError` 403, `NotFoundError` 404); 429 para límites por usuario (subclase nueva `TooManyRequestsError(DomainError)` con `http_status = 429` en `app/core/exceptions.py`).
- Repositorios hacen `flush()`, nunca `commit()` (lo hace `get_db` al final de la request → atomicidad por request).
- Toda acción admin de escritura → `audit_log(...)`.
- Frontend: toda llamada HTTP por `apiClient`; mobile-first, sin overflow horizontal a 360 px; validar en 375 px y 1280 px.
- Límites (exactos, de la spec): 5 pendientes por usuario; 15 propuestas / 24 h por usuario; 8 imágenes por propuesta; 5 MB por imagen; 40 MP máx.; WebP lado mayor ≤ 1600 px; título ≤ 200; `coupon_code` ≤ 64; `shipping_info` ≤ 120; `store_name` ≤ 80; `rejection_reason` ≤ 500; URL ≤ 2048. Rate limits por IP: check-link 20/min, crear 10/min, imágenes 30/min.
- Tag Amazon: `settings.amazon_affiliate_tag`. Solo `amazon.es` se reescribe.
- Copy del botón: **"+ Publicar chollo"**. Diálogo sin sesión: "Para compartir chollos con la comunidad necesitas una cuenta." Botones "Crear cuenta" / "Iniciar sesión".
- Python de tests: `C:\bct-venv311\Scripts\python.exe -m pytest` ejecutado desde `buenchollo-api/` (3.11, igual que CI). Frontend: `npm run test:run`, `npm run typecheck`, `npm run lint` desde `buenchollo-web/` (arrancar siempre desde la unidad `Z:` si se levanta el dev server — ver memoria del proyecto).
- No imprimir secretos del `.env` en ningún log/salida.

## Review Focus

1. **URL pegada con basura** (texto alrededor, espacios, sin esquema `www.amazon.es/dp/…`, URL móvil `amazon.es/gp/aw/d/ASIN`, acortador `amzn.eu/d/xxx`) → debe normalizarse o dar error claro, nunca 500. Test en Task 1 y Task 3.
2. **Doble envío / dos usuarios a la vez con el mismo producto** → exactamente una propuesta pendiente; el segundo recibe 409 "ya está en revisión" (índice único parcial + captura de `IntegrityError`). Test en Task 4 y estrés en Task 15.
3. **Pegar en el formulario algo que no es imagen** (texto normal, HTML copiado de una web con `<img>`, archivo PDF) → texto normal se pega en el campo enfocado sin interferir; HTML con `<img src>` → se importa esa URL; ficheros no imagen → error claro. Test en Task 10.
4. **Aprobar dos veces / aprobar una retirada** (doble clic, dos pestañas) → 409, nunca dos deals. Test en Task 7.
5. **Usuario sin perfil completo o sesión caducada a mitad del wizard** → redirección a onboarding / login sin perder el enlace (se guarda en `?url=`). Test en Task 9.

---

## Backend

### Task 1: Módulo `affiliates` — canonicalización y reescritura de enlaces

**Files:**
- Create: `buenchollo-api/app/modules/affiliates/__init__.py`, `domain/__init__.py`, `domain/links.py`, `domain/rewriters.py`
- Test: `buenchollo-api/app/tests/test_affiliate_links.py`

**Interfaces:**
- Produces:
  - `extract_url(raw: str) -> str` — primera URL http(s) dentro de un texto; añade `https://` si empieza por `www.` o por un host conocido; lanza `InvalidLinkError(ValidationError)` si no hay URL válida o > 2048.
  - `@dataclass(frozen=True) CanonicalLink(url: str, canonical_url: str, host: str, asin: str | None)`; `host` sin `www.`, minúsculas.
  - `canonicalize(url: str, *, asin: str | None = None) -> CanonicalLink` — quita fragmento, parámetros de tracking (`utm_*`, `fbclid`, `gclid`, `msclkid`, `ref`, `ref_`, `tag`, `ascsubtag`, `linkCode`, `linkId`, `psc`, `th`, `smid`, `spm`, `aff_*`, `affiliate*`, `clickref`, `irclickid`, `srsltid`), ordena el resto, quita `/` final. Si `is_amazon_host(host)` y hay `asin` (pasado o extraído con el regex de ruta `/dp/`, `/gp/product/`, `/gp/aw/d/`, `/product/`): `canonical_url = https://www.amazon.<tld>/dp/{ASIN}`.
  - `is_amazon_host(host: str) -> bool`, `is_amazon_short_host(host: str) -> bool` (`amzn.to`, `amzn.eu`, `a.co`, `link.amazon`).
  - `class AffiliateRewriter(Protocol): matches(link) -> bool; rewrite(link) -> str`
  - `@dataclass(frozen=True) RewriteResult(url: str, warnings: tuple[str, ...])`; warnings posibles (constantes): `"amazon_foreign_marketplace"`, `"third_party_affiliate_removed"`, `"not_affiliable"`.
  - `rewrite_affiliate_link(link: CanonicalLink, *, amazon_tag: str) -> RewriteResult` — recorre `REWRITERS` (lista; `AmazonEsRewriter(tag)` primero, `GenericRewriter` último).

- [ ] **Step 1: Write failing tests** (`test_affiliate_links.py`), incluyendo:
  - `extract_url("mira esto https://www.amazon.es/dp/B0ABCDEFGH?tag=otro-21 !!")` → `"https://www.amazon.es/dp/B0ABCDEFGH?tag=otro-21"`; `extract_url("www.pccomponentes.com/x")` → `"https://www.pccomponentes.com/x"`; `extract_url("hola")` y `extract_url("javascript:alert(1)")` lanzan `InvalidLinkError`.
  - `canonicalize("https://www.amazon.es/Some-Name/dp/B0ABCDEFGH/ref=sr_1_1?tag=otro-21&th=1").canonical_url == "https://www.amazon.es/dp/B0ABCDEFGH"` y `.asin == "B0ABCDEFGH"`; idem con `/gp/aw/d/B0ABCDEFGH`.
  - `canonicalize("https://WWW.PcComponentes.com/item?utm_source=x&b=2&a=1#top").canonical_url == "https://pccomponentes.com/item?a=1&b=2"`.
  - `rewrite_affiliate_link(canonicalize("https://www.amazon.es/dp/B0ABCDEFGH?tag=otro-21"), amazon_tag="buenchollo0b-21").url == "https://www.amazon.es/dp/B0ABCDEFGH?tag=buenchollo0b-21"`, `warnings == ()`.
  - amazon.de → url sin tag ajeno y `"amazon_foreign_marketplace" in warnings`.
  - `https://tienda.com/p?aff_id=9&color=red` → `url == "https://tienda.com/p?color=red"`, warnings contiene `"third_party_affiliate_removed"` y `"not_affiliable"`.
- [ ] **Step 2: Run** `C:\bct-venv311\Scripts\python.exe -m pytest app/tests/test_affiliate_links.py -v` → FAIL (ImportError).
- [ ] **Step 3: Implement** `links.py` y `rewriters.py` (solo `urllib.parse` + `re`, sin I/O). `InvalidLinkError` vive en `domain/links.py` heredando de `app.core.exceptions.ValidationError`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(affiliates): canonicalize links and rewrite Amazon affiliate tags` + push.

### Task 2: Esquema — `deal_submissions`, `deals.coupon_code`, `deals.canonical_url`, autoría

**Files:**
- Create: `buenchollo-api/alembic/versions/20261103140000_deal_submissions.py`
- Create: `buenchollo-api/app/modules/submissions/__init__.py`, `domain/__init__.py`, `domain/models.py`
- Modify: `buenchollo-api/app/modules/deals/domain/models.py` (columnas + relación `author` + propiedad `public_author`)
- Modify: `buenchollo-api/app/modules/deals/api/schemas.py` (`AuthorBasic`, `source`, `author`, `coupon_code`)
- Modify: `buenchollo-api/app/modules/deals/infrastructure/repository.py` (`_base_deal_query` + `selectinload(Deal.author)`)
- Modify: `buenchollo-api/app/modules/deals/application/deal_service.py` (rellenar `canonical_url`)
- Modify: `buenchollo-api/conftest.py` (importar el modelo nuevo si ahí se importan todos)
- Create: `buenchollo-api/scripts/backfill_canonical_urls.py`
- Test: `buenchollo-api/app/tests/test_deal_author_and_coupon.py`

**Interfaces:**
- Produces:
  - ORM `DealSubmission` (`__tablename__ = "deal_submissions"`) con columnas exactas de la spec §6.1 (+ `warnings: JSON list[str]` default `[]`), relaciones `user` → `Profile` (por `user_id`→`profiles.user_id`, `lazy="raise"`), `category`, `subcategory`, `store`.
  - Constantes en `submissions/domain/models.py`: `SubmissionStatus` = `Literal["pending","approved","rejected","withdrawn"]`, `PENDING="pending"`, etc.
  - `Deal.coupon_code: str | None`, `Deal.canonical_url: str | None`, `Deal.author` (relationship a `Profile`, `primaryjoin=Deal.created_by == Profile.user_id`, `viewonly=True`), `Deal.public_author` (property → `self.author if self.source == "community" else None`).
  - Schemas: `AuthorBasic(username: str | None, display_name: str | None, avatar_url: str | None)`; `DealCardResponse` añade `source: str = "manual"`, `author: AuthorBasic | None = Field(default=None, validation_alias="public_author")`; `DealDetailResponse` añade `coupon_code: str | None`; `DealCreate`/`DealUpdate` añaden `coupon_code: str | None = Field(default=None, max_length=64)`.
  - `DealService.create_deal`/`update_deal` asignan `canonical_url = canonicalize(affiliate_url, asin=external_id).canonical_url` cuando cambian `affiliate_url`/`external_id` (si `InvalidLinkError` → `None`, nunca rompe el flujo admin).
- Migración `upgrade()`: `op.create_table("deal_submissions", …)` + `CHECK (status IN (...))` + `CHECK (previous_price IS NULL OR previous_price > current_price)` + índices `ix_deal_submissions_status_created (status, created_at)`, `ix_deal_submissions_user_created (user_id, created_at)`, únicos parciales `uq_deal_submissions_pending_asin` (`asin`, `WHERE status='pending' AND asin IS NOT NULL`) y `uq_deal_submissions_pending_canonical` (`canonical_url`, `WHERE status='pending'`); `op.execute("ALTER TABLE deal_submissions ENABLE ROW LEVEL SECURITY")`; `op.add_column("deals", coupon_code varchar(64))`, `op.add_column("deals", canonical_url text)`, índice `ix_deals_canonical_url`. `downgrade()` inverso.

- [ ] **Step 1: Write failing tests**: `test_card_exposes_author_only_for_community` (construye `Deal(source="community", author=Profile(username="pepe", display_name="Pepe", avatar_url=None), …)` y valida `DealCardResponse.model_validate(deal).author.username == "pepe"`; con `source="manual"` → `author is None`); `test_detail_exposes_coupon_code`; `test_deal_create_rejects_coupon_over_64`; `test_create_deal_sets_canonical_url` (DealService con repo falso: `affiliate_url="https://www.amazon.es/dp/B0ABCDEFGH?tag=x"`, `external_id="B0ABCDEFGH"` → `canonical_url == "https://www.amazon.es/dp/B0ABCDEFGH"`).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** modelos, schemas, repo, servicio, migración.
- [ ] **Step 4: Run** el test nuevo + toda la suite `C:\bct-venv311\Scripts\python.exe -m pytest -q -m "not integration"` → PASS sin regresiones.
- [ ] **Step 5: Aplicar migración** a la BD compartida: `C:\bct-venv311\Scripts\python.exe -m alembic upgrade head` desde `buenchollo-api/` → termina en `20261103140000`. Verificar con el MCP de Supabase (`list_tables` / `execute_sql` de solo lectura) que existe `deal_submissions` con RLS activada y las dos columnas en `deals`. Comprobar `get_advisors` (security) sin avisos nuevos por la tabla.
- [ ] **Step 6: Backfill** `scripts/backfill_canonical_urls.py` (async, recorre deals con `canonical_url IS NULL` en lotes de 200, idempotente, `--dry-run` por defecto, `--apply` para escribir). Ejecutar dry-run, revisar recuento, ejecutar `--apply`.
- [ ] **Step 7: Commit** `feat(submissions): add deal_submissions schema, coupon code and community author` + push.

### Task 3: Comprobación de enlace (`check-link`)

**Files:**
- Create: `submissions/domain/exceptions.py`, `submissions/domain/rules.py`, `submissions/application/__init__.py`, `submissions/application/check_link.py`, `submissions/infrastructure/__init__.py`, `submissions/infrastructure/repository.py`, `submissions/api/__init__.py`, `submissions/api/schemas.py`, `submissions/api/router.py`, `submissions/api/dependencies.py`
- Modify: `buenchollo-api/app/main.py` (registrar `submissions_router` en `v1`)
- Test: `buenchollo-api/app/tests/test_submission_check_link.py`

**Interfaces:**
- Consumes: Task 1 (`extract_url`, `canonicalize`, `is_amazon_host`, `is_amazon_short_host`); `extract_asin_from_url` y `AmazonProductClient.get_product_preview` de `products/infrastructure/amazon_client.py`.
- Produces:
  - `SubmissionRepository(session)`: `find_live_deal(asin: str | None, canonical_url: str) -> Deal | None` (status en `active/scheduled/draft`), `find_expired_deal(asin, canonical_url) -> Deal | None`, `find_pending(asin, canonical_url) -> DealSubmission | None`, `find_store_by_host(host: str) -> Store | None` (match de `stores.domain` normalizado sin `www.`, solo `is_active`), `count_pending_by_user(user_id) -> int`, `count_since(user_id, since: datetime) -> int`, `add(sub) -> DealSubmission`, `get(id) -> DealSubmission | None` (con relaciones), `list_by_user(user_id, limit, offset) -> list`, `list_by_status(status, limit, offset) -> list` (autor cargado), `count_by_status(status) -> int`, `claim_pending(id, new_status) -> bool` (`UPDATE … SET status=:new WHERE id=:id AND status='pending'` → `rowcount == 1`).
  - `require_complete_profile` (en `api/dependencies.py`): depende de `get_current_user` + `ProfileRepository`; 403 `ProfileIncompleteError` (`code: "PROFILE_INCOMPLETE"`) si no hay `display_name`.
  - `CheckLinkUseCase(repo, product_provider: ProductPreviewProvider | None).execute(raw_url: str) -> LinkCheckResult` donde `LinkCheckResult` (dataclass) = `status: Literal["published","upcoming","in_review","ok"]`, `canonical_url`, `affiliate_url`, `asin`, `store_id`, `store_name`, `is_amazon`, `previously_published: bool`, `existing_deal: {id, slug, title, image_url, current_price} | None` (solo si `published`), `prefill: SubmissionPrefill | None`, `warnings`.
  - `SubmissionPrefill`: `title, brand, description, current_price, previous_price, image_url, images, expires_at` — `description` = características de Amazon como lista markdown (`- ` por línea, máx. 10).
  - Endpoint `POST /v1/submissions/check-link` body `{url: str (max 2048)}` → `LinkCheckResponse`; `@limiter.limit("20/minute")`; `Depends(require_complete_profile)`. La llamada a Amazon (`requests`, síncrona) va en `run_in_threadpool`. Amazon caído/sin credenciales → `prefill=None` y `status="ok"` (el usuario rellena a mano), nunca 5xx.
- Short links Amazon: si `is_amazon_short_host`, obtener ASIN con `extract_asin_from_url` (ya SSRF-safe) en threadpool; si no se resuelve → `InvalidLinkError("No hemos podido leer ese enlace de Amazon")`.

- [ ] **Step 1: Failing tests** (repo y provider falsos + `TestClient` con `dependency_overrides`): `published` cuando hay deal activo con mismo ASIN (con `existing_deal.slug`); `upcoming` para `scheduled`; `in_review` con propuesta pendiente; `ok` + `previously_published=True` con deal `expired`; `ok` + `prefill.title` para Amazon; `ok` con `prefill=None` si el provider lanza `ProductProviderUnavailableError`; tienda detectada por host (`store_id`); 401 sin token; 403 `PROFILE_INCOMPLETE` sin display_name; 400 con `"hola que tal"`; nunca 500 con `"   www.amazon.es/gp/aw/d/B0ABCDEFGH  "`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS + suite completa.
- [ ] **Step 5: Commit** `feat(submissions): check submitted links for duplicates and Amazon prefill` + push.

### Task 4: Crear, listar y retirar propuestas

**Files:**
- Create: `submissions/application/create_submission.py`, `submissions/application/user_submissions.py`
- Modify: `submissions/api/router.py`, `submissions/api/schemas.py`, `submissions/domain/rules.py`, `app/core/exceptions.py` (`TooManyRequestsError`)
- Test: `buenchollo-api/app/tests/test_submission_create.py`

**Interfaces:**
- Consumes: Task 1, Task 3 (`SubmissionRepository`, `CheckLinkUseCase` lógica de duplicados — extraer a función compartida `resolve_link(raw_url, repo) -> ResolvedLink` en `check_link.py` para no duplicar).
- Produces:
  - `SubmissionCreate` schema: `url`, `title` (1–200, strip), `description` (≤ 10 000), `current_price` (>0, ≤ 100000), `previous_price` (>current si viene), `coupon_code` (≤64), `shipping_info` (≤120), `store_name` (≤80), `category_id` (obligatorio), `subcategory_id`, `starts_at`, `expires_at` (> now y > starts_at), `images: list[HttpUrl-like str]` (máx. 8; cada una debe ser de nuestro bucket `…/storage/v1/object/public/deal-images/submissions/` **o** de `m.media-amazon.com`/`images-na.ssl-images-amazon.com`), `image_url` (debe estar en `images`).
  - `rules.py`: `MAX_PENDING_PER_USER = 5`, `MAX_PER_DAY = 15`, `MAX_IMAGES = 8`, `ensure_quota(pending: int, last_24h: int) -> None` (lanza `TooManyRequestsError` con mensaje en español).
  - `CreateSubmissionUseCase.execute(user_id: str, data: SubmissionCreate, amazon_tag: str) -> DealSubmission`: cuota → `resolve_link` → si `published/upcoming/in_review` → `SubmissionConflictError(ConflictError)` con `payload={"code": "SUBMISSION_DUPLICATE", "reason": status, "existing_deal": …}` → valida categoría existente → `rewrite_affiliate_link` → guarda (`warnings` del reescritor) → captura `IntegrityError` del índice parcial y la traduce a `SubmissionConflictError(reason="in_review")`.
  - Endpoints: `POST /v1/submissions` (10/min, `require_complete_profile`, 201, devuelve `SubmissionResponse`); `GET /v1/submissions/mine?limit=20&offset=0` → `list[SubmissionResponse]` (incluye `deal_slug` si aprobada y `rejection_reason`); `DELETE /v1/submissions/{id}` → 204 (solo propia y `pending`; ajena → 404; no pendiente → 409).
- La creación aún **no** notifica (lo cablea Task 6).

- [ ] **Step 1: Failing tests**: crea pendiente con `affiliate_url` reescrito y `status=="pending"`; 409 `SUBMISSION_DUPLICATE` con deal activo; 409 al chocar con `IntegrityError` simulado; 429 con 5 pendientes; 429 con 15 en 24 h; 422 `previous_price <= current_price`; 422 imagen de dominio no permitido; 422 `image_url` no incluida en `images`; 422 9 imágenes; 400 categoría inexistente; `mine` solo devuelve las del usuario; retirar ajena → 404; retirar aprobada → 409; retirar propia pendiente → 204 y `status=="withdrawn"`.
- [ ] **Step 2–4:** Run FAIL → implementar → Run PASS + suite.
- [ ] **Step 5: Commit** `feat(submissions): create, list and withdraw user submissions` + push.

### Task 5: Ingesta de imágenes (archivo, portapapeles, URL)

**Files:**
- Create: `app/core/ssrf.py` (mover `_resolves_to_private_ip` de `amazon_client.py` a `resolves_to_private_ip(url) -> bool` pública; `amazon_client.py` la importa — sin cambiar su comportamiento)
- Create: `submissions/application/image_processing.py` (puro: Pillow), `submissions/infrastructure/image_fetcher.py` (httpx), `submissions/infrastructure/storage.py` (Supabase Storage)
- Modify: `submissions/api/router.py`, `buenchollo-api/requirements.txt` (`Pillow==<última 11.x/12.x estable compatible con 3.11>` fijada)
- Test: `buenchollo-api/app/tests/test_submission_images.py`, actualizar `test_ssrf_allowlist.py` si importa el símbolo movido

**Interfaces:**
- Produces:
  - `process_image(data: bytes) -> ProcessedImage(data: bytes, width: int, height: int)` — `Image.MAX_IMAGE_PIXELS = 40_000_000`; abre con `Image.open(BytesIO)`, `verify()` + reabrir, formatos permitidos `{"JPEG","PNG","WEBP","GIF","AVIF"}` (AVIF solo si Pillow lo soporta), `ImageOps.exif_transpose`, primer frame, convierte a RGB/RGBA, `thumbnail((1600,1600))`, guarda WebP `quality=82`, sin EXIF. Errores → `InvalidImageError(ValidationError)` ("El archivo no es una imagen válida" / "La imagen es demasiado grande").
  - `ImageFetcher.fetch(url: str) -> bytes` — `httpx.AsyncClient(follow_redirects=False, timeout=10)`; sigue manualmente hasta 3 redirecciones validando en cada salto esquema http(s) y `not resolves_to_private_ip`; lee en streaming y corta a `5 * 1024 * 1024` bytes → `InvalidImageError`; `User-Agent` de navegador estándar.
  - `SubmissionImageStorage.upload(user_id: str, data: bytes) -> str` — sube a bucket `deal-images`, ruta `submissions/{user_id}/{uuid4}.webp`, `content-type: image/webp`, `cache-control: 31536000`, vía `get_supabase_client` (service role) en threadpool; devuelve URL pública (`client.storage.from_("deal-images").get_public_url(path)`).
  - Endpoints (ambos `require_complete_profile`, `30/minute`, respuesta `{"url": str, "width": int, "height": int}`):
    - `POST /v1/submissions/images` — `file: UploadFile`; lee como máximo 5 MB + 1 byte (si se excede → 413/`InvalidImageError`).
    - `POST /v1/submissions/images/from-url` — `{url}`; si el host es de Amazon (`m.media-amazon.com`, `images-na.ssl-images-amazon.com`) devuelve la URL tal cual sin descargar (`width/height = 0`).
- [ ] **Step 1: Failing tests** con imágenes generadas en memoria por Pillow: PNG 3000×2000 → WebP 1600×1067; JPEG con EXIF de orientación → rotado y sin EXIF; bytes `b"<html>…"` → `InvalidImageError`; SVG → error; imagen > 40 MP (cabecera de PNG grande) → error; `ImageFetcher` con `httpx.MockTransport`: 302 a `http://127.0.0.1/` → error; respuesta de 6 MB → error; `http://169.254.169.254/` → error; endpoint de subida con storage falso devuelve URL; endpoint from-url con URL de Amazon no descarga.
- [ ] **Step 2–4:** FAIL → implementar → PASS + suite (incl. `test_ssrf_allowlist.py`, `test_amazon_client.py`).
- [ ] **Step 5: Verificación real**: con la API local levantada (`uvicorn app.main:app --port 8000` desde `buenchollo-api/` con el venv 3.11) y un JWT real de prueba, subir una imagen y comprobar que la URL pública devuelta carga y es WebP. Borrar después el objeto de prueba del bucket.
- [ ] **Step 6: Commit** `feat(submissions): secure image ingestion via backend (Pillow → WebP)` + push.

### Task 6: Emails y notificaciones de propuestas

**Files:**
- Create: `emails/templates/submission_admin.html.j2`, `.txt.j2`, `submission_approved.html.j2`, `.txt.j2`, `submission_rejected.html.j2`, `.txt.j2`
- Modify: `emails/application/rendering.py` (3 funciones `render_*`), `app/core/config.py` (`admin_notification_email: str = ""`), `buenchollo-api/.env.example` (si existe) / `docs/project/04-configuration.md`
- Create: `submissions/application/notifier.py`
- Modify: `submissions/api/router.py` (BackgroundTask tras crear)
- Test: `buenchollo-api/app/tests/test_submission_notifier.py`

**Interfaces:**
- Produces:
  - `render_submission_admin(branding, *, title, price: str, previous_price: str | None, store: str | None, author: str, image_url: str | None, review_url: str, warnings: list[str]) -> RenderedEmail` (asunto: `"🆕 Nueva propuesta de chollo: {title[:60]}"`).
  - `render_submission_approved(branding, *, name: str | None, title: str, deal_url: str) -> RenderedEmail` (asunto `"✅ Tu chollo ya está publicado"`).
  - `render_submission_rejected(branding, *, name: str | None, title: str, reason: str, my_deals_url: str) -> RenderedEmail` (asunto `"Tu propuesta de chollo no ha sido publicada"`).
  - `SubmissionNotifier(sender: EmailSenderProtocol, branding: EmailBranding, settings, user_email_lookup: Callable[[str], Awaitable[str | None]])`:
    - `notify_admin_new(submission_id: str) -> None` — abre su propia sesión (`async_session_factory`/equivalente de `core/database.py`), carga la propuesta, envía a `settings.admin_notification_email` si no está vacío. `review_url = {site_url}/admin/propuestas?id={id}`.
    - `notify_user_decision(submission_id: str) -> None` — crea `Notification` (`type="submission_approved"` con `deal_id` y `link_url=/chollo/{slug}`, o `"submission_rejected"` con `link_url=/mis-chollos`) y envía el email al autor (email obtenido con `auth.admin.get_user_by_id` de Supabase vía `user_email_lookup`).
    - Todo best-effort: cualquier excepción → `logger.exception` y return (nunca rompe la request).
  - Los textos de usuario (título, motivo) se escapan (autoescape Jinja activo en `.html.j2`; verificar).
- [ ] **Step 1: Failing tests**: render de las 3 plantillas contiene título/motivo y **escapa** `<script>`; `notify_admin_new` con sender falso envía a `admin_notification_email`; con email vacío no envía; `notify_user_decision` crea notificación correcta y manda email; fallo del sender → no lanza; endpoint `POST /v1/submissions` programa la BackgroundTask (override del notifier).
- [ ] **Step 2–4:** FAIL → implementar → PASS + suite.
- [ ] **Step 5: Verificación real**: `scripts/send_test_email.py` (o equivalente) renderizando `submission_admin` a `pjzambudio@gmail.com` con el SMTP real del `.env` local; confirmar en Gmail (MCP de Gmail, `search_threads` por asunto) que llegó y se ve bien.
- [ ] **Step 6: Commit** `feat(submissions): email admin on new submissions and notify users on review` + push.

### Task 7: Moderación admin (listar, aprobar, rechazar)

**Files:**
- Create: `submissions/application/review_submission.py`, `submissions/api/admin_router.py`
- Modify: `submissions/api/schemas.py`, `app/main.py` (registrar admin router)
- Test: `buenchollo-api/app/tests/test_submission_review.py`

**Interfaces:**
- Consumes: `DealService.create_deal(deal_data, user_id)`, `DealService.delete_deal`, `DealCreate`, Task 1 (`rewrite_affiliate_link`), Task 3 repo (`claim_pending`, `find_expired_deal`, `find_live_deal`), Task 6 (`notify_user_decision`).
- Produces:
  - `AdminSubmissionResponse` = `SubmissionResponse` + `author: AuthorBasic`, `original_url`, `warnings`, `previously_published`.
  - `ReviewSubmissionUseCase(repo, deal_service)`:
    - `approve(submission_id, admin_id, deal_in: DealCreate, amazon_tag) -> Deal`: `claim_pending(id, "approved")` (si False → `SubmissionNotPendingError` 409) → `find_live_deal` → si existe `DuplicateDealError` (la transacción se revierte entera, la propuesta vuelve a `pending` porque no hay commit) → `find_expired_deal` → si existe `delete_deal` + `audit_log("deal.delete", reason="replaced_by_submission")` → payload final: `deal_in` con `source="community"`, `affiliate_url` reescrito, `canonical_url`; si `starts_at` futura (`deal_in.scheduled_for`) → `status="scheduled"` → `create_deal(payload, user_id=submission.user_id)` → `submission.deal_id`, `reviewed_by`, `reviewed_at`.
    - `reject(submission_id, admin_id, reason: str) -> DealSubmission` (`reason` 3–500 chars, strip).
  - Endpoints (`require_admin`, `audit_log` en approve/reject):
    - `GET /v1/admin/submissions?status=pending&limit=50&offset=0` → `list[AdminSubmissionResponse]` (pending: más antiguas primero; resto: más recientes primero).
    - `GET /v1/admin/submissions/count` → `{"pending": int}`.
    - `GET /v1/admin/submissions/{id}` → `AdminSubmissionResponse`.
    - `POST /v1/admin/submissions/{id}/approve` body `DealCreate` → `DealDetailResponse`; BackgroundTask `notify_user_decision`.
    - `POST /v1/admin/submissions/{id}/reject` body `{reason}` → `AdminSubmissionResponse`; BackgroundTask `notify_user_decision`.
- [ ] **Step 1: Failing tests**: aprobar crea deal con `source=="community"`, `created_by==autor`, enlace con nuestro tag aunque el admin pegue `tag=otro-21`; aprobar con deal `expired` del mismo ASIN lo borra y crea el nuevo; aprobar con deal `active` → 409 y la propuesta sigue `pending`; segunda aprobación → 409; aprobar retirada → 409; `scheduled_for` futura → deal `scheduled`; rechazar guarda motivo; motivo vacío → 422; no admin → 403; `count` correcto; **no-filtración**: tras crear una propuesta pendiente, `GET /v1/deals/latest`, `/deals/page`, `/deals?q=`, `/deals/{slug-inventado}` no la devuelven.
- [ ] **Step 2–4:** FAIL → implementar → PASS + suite completa.
- [ ] **Step 5: Commit** `feat(submissions): admin moderation queue with approve/reject` + push.

## Frontend

### Task 8: Cliente API — FormData, servicios y validación

**Files:**
- Modify: `buenchollo-web/src/services/api/client.ts` (no fijar `Content-Type` si `body instanceof FormData`; añadir `apiClient.upload<T>(endpoint, formData, options)` con timeout 60 s; añadir `apiClient.delete` si no existe)
- Create: `buenchollo-web/src/services/api/submissions.ts`
- Create: `buenchollo-web/src/lib/validation/submissions.ts`
- Modify: `buenchollo-web/src/services/api/deals.ts` y `features/deals/components/DealCard.tsx` (`DealCardData.source?`, `author?`, detalle `coupon_code?`)
- Test: `client.test.ts` (si no existe, crear junto a `client.ts`), `src/lib/validation/submissions.test.ts`

**Interfaces:**
- Produces (TS, nombres exactos):
  - Tipos `LinkCheckStatus = "published" | "upcoming" | "in_review" | "ok"`, `SubmissionPrefill`, `LinkCheckResult`, `SubmissionStatus = "pending" | "approved" | "rejected" | "withdrawn"`, `Submission`, `AdminSubmission`, `SubmissionCreatePayload`, `UploadedImage = { url: string; width: number; height: number }`, `DealAuthor = { username: string | null; display_name: string | null; avatar_url: string | null }`.
  - `submissionsApi`: `checkLink(url)`, `create(payload)`, `mine()`, `withdraw(id)`, `uploadImage(file: Blob, filename?)`, `importImageUrl(url)`.
  - `adminSubmissionsApi`: `list(status)`, `count()`, `get(id)`, `approve(id, payload: DealCreatePayload)`, `reject(id, reason)`.
  - `isSubmissionDuplicateError(e): e is ApiError` (409 + `code === "SUBMISSION_DUPLICATE"`).
  - `submissionFormSchema` (zod) espejo de las reglas del backend (Task 4) con mensajes en español; `computeDiscount(current, previous) -> number | null`.
- [ ] **Step 1: Failing tests**: `fetchWithAuth` con `FormData` no envía `Content-Type: application/json`; schema rechaza `previous_price <= current_price`, 9 imágenes, título vacío, `expires_at` pasada; acepta un payload válido.
- [ ] **Step 2–4:** `npm run test:run -- client submissions` FAIL → implementar → PASS; `npm run typecheck` limpio.
- [ ] **Step 5: Commit** `feat(web): submissions API client and form validation` + push.

### Task 9: Botón de cabecera, diálogo de registro y paso 1 (`/publicar`)

**Files:**
- Create: `buenchollo-web/src/features/submissions/components/PublishDealButton.tsx`, `AuthRequiredDialog.tsx`, `LinkCheckStep.tsx`
- Create: `buenchollo-web/src/routes/publicar.tsx` (search params validados: `url?: string`)
- Modify: `buenchollo-web/src/components/layout/Header.tsx` (botón visible siempre; en móvil, variante compacta "+" con `aria-label="Publicar chollo"`; también en el menú móvil y en el dropdown "Mis chollos"), `routes/login.tsx` y `routes/registro.tsx` solo si hace falta para respetar un `redirect` de vuelta a `/publicar?url=…` (reutilizar el mecanismo de redirect existente si lo hay)
- Test: `PublishDealButton.test.tsx`, `LinkCheckStep.test.tsx`, actualizar `Header.test.tsx`

**Interfaces:**
- Consumes: Task 8 (`submissionsApi.checkLink`, tipos), `useAuth()` (`user`, `me.needs_onboarding`, `loading`).
- Produces: `LinkCheckStep({ initialUrl, onContinue(result: LinkCheckResult, url: string) })`.
- Comportamiento: sin sesión → `AuthRequiredDialog` (copy de Global Constraints, enlaces a `/registro` y `/login` con redirect a `/publicar`); con sesión y `needs_onboarding` → navegar al onboarding existente; `/publicar` sin sesión → muestra el diálogo en la página (no 404). Paso 1: input grande `type="url"` `inputMode="url"`, autofocus, botón "Comprobar"; estados: cargando (skeleton), `published` (mini tarjeta con enlace a `/chollo/{slug}` "Ver y votar"), `upcoming`, `in_review`, `ok` (+ aviso si `previously_published`; `warnings` no se enseñan al usuario). Error 400 → mensaje en línea; 401 → login con redirect conservando `url`.
- [ ] **Step 1: Failing tests** (Testing Library + `renderWithProviders`, `submissionsApi` mockeado): botón sin sesión abre diálogo con "Crear cuenta"; con sesión navega a `/publicar`; cada estado de `checkLink` muestra su texto; `ok` llama `onContinue`; 401 redirige a login con `redirect` que contiene la `url`.
- [ ] **Step 2–4:** FAIL → implementar → PASS; `typecheck` + `lint`.
- [ ] **Step 5: Commit** `feat(web): publish deal entry point and link check step` + push.

### Task 10: Paso 2 — formulario, imágenes con portapapeles, envío

**Files:**
- Create: `buenchollo-web/src/features/submissions/components/SubmissionForm.tsx`, `ImageUploader.tsx`, `SubmissionPreviewCard.tsx`, `SubmissionSuccess.tsx`
- Create: `buenchollo-web/src/features/submissions/hooks/useImageUploads.ts`, `src/features/submissions/lib/clipboard.ts`
- Modify: `buenchollo-web/src/routes/publicar.tsx`
- Test: `ImageUploader.test.tsx`, `clipboard.test.ts`, `SubmissionForm.test.tsx`

**Interfaces:**
- Consumes: Task 8, Task 9 (`LinkCheckResult`), categorías (hook/servicio existente de categorías).
- Produces:
  - `extractClipboardItems(e: ClipboardEvent | DataTransfer) -> { files: File[]; urls: string[] }` — ficheros `image/*`; si no hay ficheros: `text/html` → `src` de los `<img>` (http/https); `text/plain` que sea una URL http(s) → urls. Texto normal → nada (y no se hace `preventDefault`, para no romper el pegado en inputs).
  - `useImageUploads(initial: string[])` → `{ images: UploadItem[]; addFiles(files); addUrls(urls); remove(id); move(id, dir); setCover(id); cover: string | null; isUploading: boolean }`; `UploadItem = { id; url?: string; previewUrl: string; status: "uploading" | "done" | "error"; error?: string }`; límite 8 con toast; ficheros > 5 MB se rechazan en cliente antes de subir.
  - `ImageUploader`: zona con texto "Arrastra, pega (Ctrl+V) o elige imágenes", botón "Pegar" (solo si `navigator.clipboard?.read` existe), input URL + "Añadir", input file `accept="image/*" multiple`; listener `paste` en `document` mientras el paso 2 está montado (ignora si el foco está en un `input`/`textarea` y el portapapeles solo trae texto); miniaturas con estado, flechas reordenar, estrella portada, quitar. Accesible por teclado.
  - `SubmissionForm`: campos de la spec (título, precio, precio anterior con `-X%` en vivo, cupón, gastos de envío, tienda — readonly si detectada, input si no —, categoría/subcategoría, fecha inicio/fin, descripción textarea), prefill desde `LinkCheckResult.prefill`; vista previa con `SubmissionPreviewCard` (reutiliza estilos de `DealCard`); submit deshabilitado mientras suben imágenes; 409 `SUBMISSION_DUPLICATE` → vuelve al paso 1 mostrando el estado; 429 → mensaje del backend.
  - `SubmissionSuccess`: "¡Gracias! Revisaremos tu chollo y te avisaremos por email." + enlaces "Ver mis chollos" y "Publicar otro".
- [ ] **Step 1: Failing tests**: `extractClipboardItems` con fichero imagen, con HTML `<img src="https://x/y.jpg">`, con URL en texto, con texto normal (vacío); `ImageUploader`: pegar imagen llama `uploadImage`; pegar URL llama `importImageUrl`; 9ª imagen → toast y no sube; reordenar y portada cambian el orden emitido; `SubmissionForm`: prefill de Amazon rellena título/precio/imágenes; error de validación en línea; envío correcto llama `create` con `image_url` = portada y muestra éxito; 409 vuelve al paso 1.
- [ ] **Step 2–4:** FAIL → implementar → PASS; `typecheck` + `lint`.
- [ ] **Step 5: Verificación visual** con el dev server (desde `Z:`) y Chrome (claude-in-chrome) a 375 px y 1280 px: paso 1 y 2, pegar imagen real del portapapeles, sin overflow horizontal. Capturas guardadas en el scratchpad.
- [ ] **Step 6: Commit** `feat(web): submission form with clipboard/drag/url image uploads` + push.

### Task 11: "Mis chollos"

**Files:**
- Create: `buenchollo-web/src/routes/mis-chollos.tsx`, `src/features/submissions/components/MySubmissionsList.tsx`
- Modify: `Header.tsx` (dropdown + menú móvil: "Mis chollos")
- Test: `MySubmissionsList.test.tsx`

**Interfaces:**
- Consumes: `submissionsApi.mine()`, `submissionsApi.withdraw(id)`.
- Comportamiento: sin sesión → login con redirect; lista con badge por estado ("En revisión", "Publicado" → enlace `/chollo/{deal_slug}`, "Rechazado" + motivo, "Retirado"); botón "Retirar" solo en pendientes (confirmación con `AlertDialog` de shadcn, no `window.confirm`); estado vacío con CTA "+ Publicar chollo".
- [ ] **Step 1: Failing tests** de render por estado, retirar y estado vacío. **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat(web): my submissions page` + push.

### Task 12: Autoría y código de descuento en web pública + campo cupón en admin

**Files:**
- Create: `buenchollo-web/src/features/deals/components/DealAuthor.tsx`, `CouponCode.tsx`
- Modify: `features/deals/components/DealCard.tsx`, `routes/chollo.$slug.tsx`, `features/admin/deal-form.ts` (`coupon_code` en `DealForm`, `emptyForm`, `dealToForm`, `buildDealPayload`), `features/admin/components/DealFormPanel.tsx` (input cupón)
- Test: `DealAuthor.test.tsx`, `CouponCode.test.tsx`, actualizar `DealCard.test.tsx` y tests de `deal-form`

**Interfaces:**
- `DealAuthor({ author, size: "sm" | "md" })` → avatar (fallback inicial) + "Compartido por **{display_name || username}**"; no renderiza nada si `author` es null.
- `CouponCode({ code })` → código monoespaciado + botón "Copiar" (`navigator.clipboard.writeText`, toast "Código copiado").
- DealCard muestra `DealAuthor size="sm"` solo si `deal.author`; ficha muestra `DealAuthor size="md"` y `CouponCode` si `coupon_code`.
- [ ] **Step 1–4:** tests FAIL → implementar → PASS; `typecheck`; tests existentes de DealCard/admin siguen verdes.
- [ ] **Step 5: Commit** `feat(web): show community author and coupon codes` + push.

### Task 13: Panel admin "Propuestas"

**Files:**
- Create: `buenchollo-web/src/routes/admin.propuestas.tsx` (search: `id?: string`), `src/features/admin/components/SubmissionQueue.tsx`, `SubmissionReviewPanel.tsx`, `RejectSubmissionDialog.tsx`, `src/features/admin/hooks/useAdminSubmissions.ts`, `src/features/admin/submission-form.ts` (`submissionToDealForm(s: AdminSubmission): DealForm`)
- Modify: `routes/admin.tsx` (entrada "Propuestas" con icono `Inbox` y badge con `adminSubmissionsApi.count()`, `refetchInterval` 60 s)
- Test: `submission-form.test.ts`, `SubmissionReviewPanel.test.tsx`

**Interfaces:**
- Consumes: Task 8 (`adminSubmissionsApi`), `DealFormPanel` (sin modificar su contrato salvo el cupón de Task 12), `buildDealPayload`, `TelegramPanel` (lazy, mismo uso que en `admin.chollos.tsx`: `openTelegramPanelWith` — si hace falta compartirlo, extraer a `src/features/admin/hooks/useTelegramHandoff.ts` y usarlo en ambos sitios sin cambiar el comportamiento de `admin.chollos`).
- Comportamiento: cola (tarjetas con miniatura, título, precio, autor, antigüedad, avisos); al abrir una (`?id=`), `SubmissionReviewPanel` muestra enlace original + reescrito + avisos (`amazon_foreign_marketplace`, `third_party_affiliate_removed`, `not_affiliable`, `previously_published` → "Se borrará el chollo caducado anterior al aprobar") y `DealFormPanel` precargado con `submissionToDealForm` (incluye `external_id` = ASIN, `store_id`, imágenes, `coupon_code`, `shipping_info`, `scheduled_for` = `starts_at`, `status` = `scheduled` si `starts_at` futura). Botones "Aprobar y publicar" (+ checkbox "Publicar también en Telegram") y "Rechazar" (diálogo con motivos predefinidos: "Ya publicado", "Precio no es una oferta", "Enlace no válido o sin stock", "Información incompleta", "No es tecnología" + texto libre; resultado en `reason`). Tras aprobar: toast, invalidar cola y count; si Telegram marcado → abrir `TelegramPanel` con los datos del deal devuelto. 409 `DUPLICATE_DEAL` → toast con enlace al existente.
- [ ] **Step 1: Failing tests**: `submissionToDealForm` mapea todos los campos y `status`; aprobar llama `approve` con payload correcto; con Telegram marcado abre el panel; rechazar exige motivo.
- [ ] **Step 2–4:** FAIL → implementar → PASS; `typecheck` + `lint`; tests de `admin.chollos` siguen verdes.
- [ ] **Step 5: Commit** `feat(web): admin moderation queue for community deals` + push.

## Verificación global

### Task 14: E2E Playwright

**Files:**
- Create: `buenchollo-web/e2e/community-submission.spec.ts`, `buenchollo-web/e2e/admin-submissions.spec.ts`

- [ ] **Step 1:** Escribir los dos specs con el patrón existente (`page.route("**/v1/**")`, mock de `/auth/v1/user`): (a) anónimo pulsa "+ Publicar chollo" → diálogo; usuario logado pega enlace Amazon → prefill → pega una imagen (`page.evaluate` despachando `ClipboardEvent` con `DataTransfer`) → envía → éxito → "Mis chollos" muestra "En revisión"; enlace duplicado → "ya está publicado". (b) admin abre Propuestas → revisa → rechaza con motivo; otra → aprueba con Telegram → se abre el panel. Viewports 375×812 y 1280×800.
- [ ] **Step 2:** `npm run test:e2e -- community-submission admin-submissions` → PASS.
- [ ] **Step 3: Commit** `test(e2e): community submission and moderation flows` + push.

### Task 15: Prueba real extremo a extremo + estrés

**Files:**
- Create: `buenchollo-api/scripts/stress_submissions.py`

- [ ] **Step 1: E2E real local**: API local (venv 3.11) + web local (desde `Z:`) contra la BD/Storage/Amazon/SMTP reales: con una cuenta de usuario de prueba (no admin) recorrer el flujo con un producto real de Amazon y con un enlace de otra tienda (imagen pegada + por URL); comprobar email en `pjzambudio@gmail.com` (MCP Gmail); como admin aprobar uno (sin Telegram, para no publicar en el canal real) y rechazar otro; comprobar notificación + email del usuario, autoría en tarjeta/ficha, enlace con `tag=buenchollo0b-21`. **Al terminar, borrar los deals, propuestas, notificaciones e imágenes de prueba** (y dejarlo registrado).
- [ ] **Step 2: Script de estrés** (`httpx.AsyncClient`, argumentos `--base-url`, `--token-file`, `--concurrency`): (a) 50 `check-link` concurrentes → todas 200/429, ninguna 5xx, latencias p50/p95; (b) 20 creaciones concurrentes del **mismo** producto con 5 usuarios → exactamente 1 `pending`, resto 409/429; (c) 30 subidas de imagen concurrentes → sin 5xx, memoria del proceso estable; (d) ráfaga que dispare los rate limits → 429 con `Retry-After`. Ejecutar contra la API local con `RATE_LIMIT_ENABLED` real; limpiar los datos creados al final (el script borra lo que crea).
- [ ] **Step 3:** Suites completas: `pytest -q` (backend), `npm run test:run`, `npm run typecheck`, `npm run lint`, `npm run build` → todo verde. Push y comprobar CI de `develop` en verde (`gh run list --branch develop`).
- [ ] **Step 4: Commit** `test: stress script for community submissions` + push.

### Task 16: Documentación y cierre

**Files:**
- Create: `docs/adr/ADR-015-ingesta-imagenes-backend.md`, `docs/adr/ADR-016-propuestas-comunidad-y-afiliados.md`
- Modify: `docs/adr/00-index.md`, `docs/project/01-overview.md`, `03-project-structure.md`, `04-configuration.md` (`ADMIN_NOTIFICATION_EMAIL`), `07-security.md` (ingesta imágenes, SSRF, antiabuso), `08-deployment.md` (pasos de despliegue: `.env` NAS con `ADMIN_NOTIFICATION_EMAIL`, rebuild por Pillow), `10-technical-debt.md` (nuevos TD: preview Amazon sin auth, imágenes huérfanas en `submissions/`, digest nocturno con atributos inexistentes en `Deal`), `11-current-state.md`, `PROJECT_STATUS.md`, `CLAUDE.md` (módulos `submissions`, `affiliates` en el árbol)
- Modify: OBSIDIAN VAULT (`Z:\IA\02_Proyectos\OBSIDIAN VAULT`): ficha nueva `Concepts/Moderacion-Contenido-Usuario-Ingesta-Imagenes-Afiliados.md` + `Entities/Proyecto-BuenCholloTech.md` + `index.md` + `log.md`, según `SCHEMA.md`

- [ ] **Step 1:** Redactar ADRs y docs (sin inventar, el código manda).
- [ ] **Step 2:** Revisión final de rama completa (code review de todo el diff `main..develop` con subagente revisor) y corregir hallazgos.
- [ ] **Step 3: Commit** `docs: community submissions ADRs, guides and status` + push; CI verde.
