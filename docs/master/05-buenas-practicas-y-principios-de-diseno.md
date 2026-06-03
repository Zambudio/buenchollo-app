# 05 — Buenas prácticas y principios de diseño

Este capítulo muestra cómo se han aplicado **SOLID, DRY, KISS y
YAGNI** sobre el propio código del proyecto, no como teoría general.
Los ejemplos son reales y referencian archivos concretos.

## SOLID

### S — Single Responsibility Principle

**Aplicado en**: separación de capas dentro de cada módulo del backend.

Cada clase tiene una razón para cambiar:

| Clase | Responsabilidad |
|---|---|
| `Deal` ([`deals/domain/models.py`](../../buenchollo-api/app/modules/deals/domain/models.py)) | Estructura de datos persistible (campos + relaciones) |
| `DealRepository` ([`deals/infrastructure/repository.py`](../../buenchollo-api/app/modules/deals/infrastructure/repository.py)) | Acceso a BD (queries SQL) |
| `DealService` ([`deals/application/deal_service.py`](../../buenchollo-api/app/modules/deals/application/deal_service.py)) | Orquestación (auto_slug, asignar creador, disparar AlertMatcher) |
| Router (`deals/api/router.py`) | Sólo HTTP: validar, llamar servicio, devolver respuesta |

**Contraejemplo evitado**: en sprints tempranos el router de deals
contenía lógica de generación de slug, asignación de `created_by` y
disparo de notificaciones. Se refactorizó al sprint F2 extrayendo
`DealService`. El router pasó de 240 a 70 líneas.

### O — Open/Closed Principle

**Aplicado en**: el caso de uso `PreviewProductFromUrlUseCase` no
cambia al añadir un nuevo proveedor de productos.

```python
# domain/entities.py
class ProductPreviewProvider(Protocol):
    def get_product_preview(self, url_or_asin: str) -> ProductPreview | None: ...

class AIEnricher(Protocol):
    def enrich(self, preview: ProductPreview) -> ProductPreview: ...

# application/preview_product_from_url.py
class PreviewProductFromUrlUseCase:
    def __init__(self, provider: ProductPreviewProvider, enricher: AIEnricher):
        self._provider = provider
        self._enricher = enricher

    def execute(self, url: str) -> ProductPreview | None:
        preview = self._provider.get_product_preview(url)
        return self._enricher.enrich(preview) if preview else None
```

Para añadir **Aliexpress** sólo hay que crear
`AliexpressProductClient` implementando el Protocol y registrarlo
en el router. **El caso de uso queda intacto**.

### L — Liskov Substitution Principle

**Aplicado en**: las excepciones de dominio.

```python
class DomainError(Exception):
    http_status: int = 500

class NotFoundError(DomainError):
    http_status: int = 404

class ConflictError(DomainError):
    http_status: int = 409

class DuplicateDealError(ConflictError):
    def __init__(self, existing_id, existing_slug, existing_title):
        super().__init__(f"Ya existe un chollo con este ASIN: '{existing_title}'")
        self.payload = {
            "code": "DUPLICATE_DEAL",
            "existing_deal": {"id": existing_id, "slug": existing_slug, "title": existing_title},
        }
```

Cualquier `DomainError` puede pasarse al handler global que lo
traduce a HTTP, sin importar la subclase concreta. El `payload`
opcional se fusiona si está presente, no rompe el contrato.

### I — Interface Segregation Principle

**Aplicado en**: los Protocols del dominio de productos son
**mínimos**.

`ProductPreviewProvider` declara sólo `get_product_preview()`.
`AIEnricher` declara sólo `enrich()`. **No se mezclan**, así un test
puede mockear uno sin tener que implementar métodos que no usa.

### D — Dependency Inversion Principle

**Aplicado en**: el `composition root` con `Depends` de FastAPI.

```python
# infrastructure depende del dominio, no al revés
def get_deal_service(db: AsyncSession = Depends(get_db)) -> DealService:
    repo = DealRepository(db)
    matcher = AlertMatcher(AlertRepository(db), NotificationRepository(db))
    return DealService(repo, matcher)

@router.post("/admin")
async def create_deal(
    deal_in: DealCreate,
    service: DealService = Depends(get_deal_service),
    current_user=Depends(require_admin),
):
    payload = deal_in.model_dump(exclude_none=True)
    return await service.create_deal(payload, str(current_user.id))
```

`DealService` no sabe nada de FastAPI ni de la BD concreta. Recibe
abstracciones (Repository, AlertMatcher) por constructor. Documentado
en [ADR-007](../adr/ADR-007-di-fastapi-depends.md).

## DRY — Don't Repeat Yourself

### `_base_deal_query()` en el repositorio

Se repetía 6 veces el patrón:

```python
select(Deal).options(
    selectinload(Deal.category),
    selectinload(Deal.subcategory),
    selectinload(Deal.store),
)
```

Refactorizado a:

```python
@staticmethod
def _base_deal_query():
    return select(Deal).options(
        selectinload(Deal.category),
        selectinload(Deal.subcategory),
        selectinload(Deal.store),
    )
```

Cualquier query nueva parte de esta base sin repetir el `selectinload`.

### `errorMessage(unknown → string)` en el frontend

Centraliza el patrón "tengo un `unknown` capturado en catch,
necesito un string":

```ts
export function errorMessage(e: unknown, fallback = "Error inesperado"): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  return fallback;
}
```

Usado en 12+ catch blocks del frontend. **Sin esto**, cada catch tenía
su propio `(e as Error)?.message ?? "..."` con casts inseguros.

### `_safe_run` en el cleaner

`DealCleanerService` ejecuta tres jobs distintos (`mark_expired`,
`activate_scheduled`, `clean_expired`). Cada uno con su propio
try/except idéntico:

```python
def _safe_run(self, name: str, action: Callable[[], int], default: int = 0) -> int:
    try:
        return action()
    except Exception:
        logger.exception("Falló %s — el scheduler sigue ejecutando los otros", name)
        return default
```

Si un job revienta, los otros siguen vivos. Patrón aplicado, no
repetido en cada método.

### Constantes de dominio centralizadas

`src/lib/constants.ts`:

```ts
export const TEMPERATURE_HOT_THRESHOLD = 200;
export const TEMPERATURE_WARM_THRESHOLD = 100;
export const DEAL_STATUS_OPTIONS = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activos" },
  // ...
] as const;
```

Antes había 4 sitios con literales `200` y `"active"` repetidos. Si
mañana cambia el umbral, se cambia en un único sitio.

## KISS — Keep It Simple, Stupid

### Paginación offset/limit en vez de cursor

**Decisión**: cuando se añadió el feed infinito de la home, se eligió
paginación `offset/limit` simple en vez de cursor-based.

Razones:

- Volumen actual: cientos de chollos, no millones. Offset no genera
  problemas de rendimiento.
- Contrato simple: el frontend hace `?limit=16&offset=N`. No hay que
  inventar tokens opacos.
- Migración futura abierta: si el volumen sube, se puede pasar a
  cursor por `published_at + id` sin romper el cliente actual.

### Sin clases base abstractas innecesarias

Los routers usan **funciones** decoradas con `@router.post(...)`. No
hay `BaseHandler`, `CRUDController`, `AbstractEndpoint`. FastAPI ya
provee la abstracción correcta con `Depends`.

### Sin factories ni builders donde un constructor basta

Los servicios se instancian con `DealService(repo, matcher)`. No
hay `DealServiceFactory` ni `DealServiceBuilder.with_repo().with_matcher().build()`.

### Sin "abstracciones especulativas"

No hay capa de "Mappers" entre el dominio y el ORM cuando ambos son la
misma estructura. Las excepciones del dominio extienden `Exception`
directamente, no una jerarquía de "BaseException > BusinessException >
DomainException > ...".

## YAGNI — You Aren't Gonna Need It

### Sin sistema de plugins genérico

Cuando se decidió que el proveedor de productos podía cambiar, no se
construyó un "PluginManager" con registro dinámico. Se hizo un
`Protocol` y se documentó cómo añadir un proveedor nuevo: implementa
el Protocol y regístralo en el router con `Depends`.

### Sin notificaciones por email "por si acaso"

El modelo `Alert` tiene `notify_email` para preparar el campo
**cuando se integre proveedor de correo**, pero el código de envío
NO existe. Se podría haber implementado "para tenerlo", pero sin
proveedor SMTP elegido sería código muerto. Decisión: dejar el
campo, dejar la decisión "cuando aplique", documentar como mejora
futura.

### Sin cache de productos preview

Se podía cachear las respuestas de Amazon Creators API para no
gastar quota. **No se hizo** porque:

- El admin usa el endpoint manualmente, no en bucle.
- La quota actual es generosa.
- Cachear introduce invalidación, otro problema.

Si el volumen de uso sube, se añade Redis. Hoy no.

### Sin internacionalización

La web es sólo en español. Se podía haber preparado `i18next` "por
si acaso". **No se hizo** porque:

- El público objetivo es España.
- Internacionalizar pre-MVP triplica el trabajo de UI sin valor real.
- Si se internacionaliza después, el cambio es mecánico (extraer
  strings).

## Refactorizaciones documentadas

Cada sprint de refactorización dejó constancia en commits y en
`PROJECT_STATUS.md`. Los más relevantes:

### Refactor de buenas prácticas para TFM (2026-05-26)

Resumen en `PROJECT_STATUS.md §3.bis`. Bloque de 8+ refactors aplicados
con auditoría completa de SOLID/DRY/KISS/YAGNI. Métricas:

- TypeScript: 0 errores con strict.
- pytest: 49 verdes (luego ampliado a 87).
- Cero `any` injustificados, cero `null as any`.
- ADR-002 cumplido al 100%.

### Hardening arquitectónico F1–F7 (2026-05-30)

`docs/reference/PLAN_ARQUITECTURA.md`. 30 tareas en 7 fases con plan
documentado y commit por tarea. Métricas finales:

- 87 pytest verdes.
- TS strict + noUncheckedIndexedAccess.
- API versionada `/v1`.
- Frontend reorganizado por features.
- CI con coverage threshold automático.

### Calidad del software Q1–Q7 (2026-05-30)

`docs/QUALITY.md` (movido a `docs/master/06`). 7 fases con setup
Vitest, Testing Library, Playwright, Husky, CI con coverage, docs.

### Seguridad S1–S7 (2026-06-02)

6 fixes de severidad media + 1 commit de docs. Auditoría OWASP
completa con 10 hallazgos priorizados.

## Antipatrones evitados

| Antipatrón | Cómo se evitó |
|---|---|
| **God Component** | `admin.chollos.tsx` tiene 940 líneas (documentado como deuda asumida — partir conlleva alto riesgo). El resto del frontend está bajo 400 líneas/archivo. Los componentes reutilizables viven en `features/<dominio>/components/`. |
| **Prop drilling** | TanStack Query como state manager remoto. Auth en Context. No se pasan callbacks 5 niveles abajo. |
| **Magic numbers** | Constantes en `lib/constants.ts` con nombres descriptivos. |
| **Magic strings** | Status de chollos vienen de `DEAL_STATUS_OPTIONS as const` con literal types. |
| **Stringly typed** | Pydantic en backend + Zod en frontend + TS strict. Las APIs tienen contratos tipados que el cliente respeta. |
| **Stack trace al cliente** | `unhandled_exception_handler` devuelve siempre `"Error interno del servidor"`. El detalle está en logs internos. |
| **Validar sólo en el cliente** | Doble validación documentada en ADR-005. |
| **Secretos en el código** | `.env*` en `.gitignore`, gitleaks en CI, regenerar política documentada. |
| **Confiar en `isAdmin` del cliente** | `require_admin` consulta directamente `user_roles` con SQL parametrizado. El frontend sólo oculta UI por UX, no por seguridad. |
| **Mockear en exceso** | Los tests integration tienen ≤3 mocks (sólo fronteras). |

## Lo que está documentado como deuda asumida

No todo se puede ni se debe perfeccionar. Lo siguiente está
**conscientemente** dejado como mejora futura, con justificación en
[`09-limitaciones-y-mejoras-futuras.md`](09-limitaciones-y-mejoras-futuras.md):

- `admin.chollos.tsx` God Component (940 líneas).
- A11y warnings en algunos formularios admin.
- `style-src 'unsafe-inline'` en CSP (necesario para React + shadcn).
- Visual regression testing con `toHaveScreenshot`.
- Page Object Model elaborado.
- DAST automatizado con OWASP ZAP.
- SBOM con CycloneDX.

La decisión de NO hacer estas cosas es tan importante como las que sí
se hicieron: evita sobreingeniería y mantiene el coste de cambio
bajo.
