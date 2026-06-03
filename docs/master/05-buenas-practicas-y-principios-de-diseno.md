# ✨ 05 · Buenas prácticas y principios de diseño

> **TL;DR** · **SOLID**, **DRY**, **KISS** y **YAGNI** aplicados sobre
> el propio código del proyecto — con ejemplos reales, archivos
> concretos, y refactorizaciones documentadas. Nada de teoría genérica.

---

## 🧠 SOLID

### 🔵 S · Single Responsibility Principle

> _Cada clase tiene una sola razón para cambiar._

Aplicado en la **separación de capas dentro de cada módulo del backend**:

```
┌──────────────────────────────────────────────────────────────┐
│  modules/deals/                                              │
│                                                              │
│  📦 domain/models.py     →  Estructura persistible          │
│  🧠 application/         →  Orquestación (auto_slug, FK,    │
│       deal_service.py        AlertMatcher)                  │
│  🔌 infrastructure/      →  Acceso a BD (queries SQL)       │
│       repository.py                                          │
│  🌐 api/router.py        →  Sólo HTTP (recibir, llamar,     │
│                              devolver)                       │
└──────────────────────────────────────────────────────────────┘
```

#### Contraejemplo evitado

En sprints tempranos el router de deals contenía lógica de:
- generación de slug
- asignación de `created_by`
- disparo de notificaciones

Se refactorizó al sprint F2 extrayendo `DealService`. El router pasó
de **240 a 70 líneas**.

---

### 🟢 O · Open/Closed Principle

> _Abierto a extensión, cerrado a modificación._

El caso de uso `PreviewProductFromUrlUseCase` **no cambia** al añadir
un nuevo proveedor de productos:

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

> 💡 Para añadir **Aliexpress** sólo hay que crear `AliexpressProductClient`
> implementando el Protocol y registrarlo en el router. **El caso de uso
> queda intacto**.

---

### 🟡 L · Liskov Substitution Principle

> _Cualquier subclase debe poder usarse donde se espera la clase base._

Aplicado en la **jerarquía de excepciones de dominio**:

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

✅ Cualquier `DomainError` puede pasarse al handler global que lo
traduce a HTTP, sin importar la subclase concreta.

---

### 🟠 I · Interface Segregation Principle

> _Mejor varias interfaces específicas que una grande._

Los Protocols del dominio de productos son **mínimos**:

- `ProductPreviewProvider` declara **sólo** `get_product_preview()`.
- `AIEnricher` declara **sólo** `enrich()`.

✅ **No se mezclan**, así un test puede mockear uno sin tener que
implementar métodos que no usa.

---

### 🟣 D · Dependency Inversion Principle

> _Depender de abstracciones, no de implementaciones concretas._

Aplicado con `Depends` de FastAPI como **composition root**:

```python
# Infrastructure depende del dominio, no al revés
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

✅ `DealService` **no sabe nada** de FastAPI ni de la BD concreta.
Recibe abstracciones por constructor.

📚 Documentado en [**ADR-007**](../adr/ADR-007-di-fastapi-depends.md).

---

## 🔁 DRY · Don't Repeat Yourself

### `_base_deal_query()` — repetido 6 veces

❌ **Antes**: el mismo `selectinload` en 6 queries distintas.

✅ **Después**:

```python
@staticmethod
def _base_deal_query():
    return select(Deal).options(
        selectinload(Deal.category),
        selectinload(Deal.subcategory),
        selectinload(Deal.store),
    )
```

Cualquier query nueva parte de esta base.

---

### `errorMessage(unknown → string)` — frontend

❌ **Antes**: cada `catch` con `(e as Error)?.message ?? "..."`.

✅ **Después**:

```ts
export function errorMessage(e: unknown, fallback = "Error inesperado"): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  return fallback;
}
```

Usado en **12+ catch blocks** del frontend.

---

### `_safe_run` en el cleaner

`DealCleanerService` ejecuta 3 jobs distintos (`mark_expired`,
`activate_scheduled`, `clean_expired`). Antes, cada uno tenía su propio
try/except idéntico.

```python
def _safe_run(self, name: str, action: Callable[[], int], default: int = 0) -> int:
    try:
        return action()
    except Exception:
        logger.exception("Falló %s — el scheduler sigue ejecutando los otros", name)
        return default
```

> 💡 Si un job revienta, los otros siguen vivos.

---

### Constantes de dominio centralizadas

```ts
// src/lib/constants.ts
export const TEMPERATURE_HOT_THRESHOLD = 200;
export const TEMPERATURE_WARM_THRESHOLD = 100;
export const DEAL_STATUS_OPTIONS = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activos" },
  // ...
] as const;
```

❌ Antes había 4 sitios con literales `200` y `"active"`.
✅ Si mañana cambia el umbral, se cambia en un único sitio.

---

## 🪶 KISS · Keep It Simple, Stupid

### Paginación `offset/limit` en vez de cursor

| Por qué |
|---|
| 📊 Volumen actual: cientos de chollos. Offset no genera problemas |
| 📡 Contrato simple: `?limit=16&offset=N` |
| 🚪 Migración futura abierta: si crece, se pasa a cursor sin romper cliente |

### Sin clases base abstractas innecesarias

Los routers usan **funciones** decoradas con `@router.post(...)`.

❌ No hay: `BaseHandler`, `CRUDController`, `AbstractEndpoint`.
✅ FastAPI ya provee la abstracción correcta con `Depends`.

### Sin factories ni builders donde un constructor basta

✅ Los servicios se instancian con `DealService(repo, matcher)`.
❌ No hay: `DealServiceFactory`, `DealServiceBuilder.with_repo()…`.

### Sin "abstracciones especulativas"

✅ No hay capa de "Mappers" entre el dominio y el ORM cuando ambos son la misma estructura.
✅ Las excepciones de dominio extienden `Exception` directamente.

---

## 🚫 YAGNI · You Aren't Gonna Need It

### Sin sistema de plugins genérico

Cuando se decidió que el proveedor de productos podía cambiar, **no
se construyó un `PluginManager`**. Se hizo un `Protocol` y se
documentó cómo añadir un proveedor.

### Sin notificaciones por email "por si acaso"

El modelo `Alert.notify_email` está preparado, pero el código de envío
**NO existe**. Se podría haber implementado "para tenerlo", pero sin
proveedor SMTP elegido sería código muerto.

✅ Decisión: dejar el campo, dejar la decisión "cuando aplique",
documentar como mejora futura.

### Sin cache de productos preview

| Por qué no |
|---|
| El admin usa el endpoint manualmente, no en bucle |
| La quota actual de Amazon Creators es generosa |
| Cachear introduce invalidación — otro problema |

> 💡 Si el volumen sube, se añade Redis. **Hoy no.**

### Sin internacionalización

| Por qué no |
|---|
| El público objetivo es España |
| Pre-MVP triplica el trabajo de UI sin valor real |
| Internacionalizar después es mecánico (extraer strings) |

---

## 🛠️ Refactorizaciones documentadas

Cada sprint del proyecto incluyó refactors significativos sin que
ningún test rojo se quedara en `main`:

| Sprint | Bitácora | Resumen |
|---|---|---|
| **Buenas prácticas (2026-05-26)** | `PROJECT_STATUS.md §3.bis` | 8+ refactors con auditoría SOLID/DRY/KISS/YAGNI |
| **Hardening F1–F7** | `docs/reference/PLAN_ARQUITECTURA.md` | 30 tareas en 7 fases con commit por tarea |
| **Calidad Q1–Q7** | `docs/master/06-…` | Vitest + Testing Library + Playwright + CI |
| **Seguridad S1–S7** | `docs/reference/SECURITY_AUDIT.md` | 6 fixes de severidad media + docs/SECURITY.md |

### Métricas finales

| Métrica | Valor |
|---|---|
| 🧪 **pytest verdes** | **97** |
| ⚛️ **Vitest verdes** | **72** (59 unit + 13 integration) |
| 🎭 **Playwright verdes** | **8** |
| 📊 **TS strict + 0 errores** | ✅ |
| 🔍 **`any` injustificados** | **0** |
| 🛡️ **CVEs prod en backend** | **0** |
| 🎯 **ADR-002 cumplido** | **100%** |

---

## 🚨 Antipatrones evitados

<table>
<thead>
<tr><th>Antipatrón</th><th>Cómo se evitó</th></tr>
</thead>
<tbody>
<tr>
  <td>🪨 <strong>God Component</strong></td>
  <td><code>admin.chollos.tsx</code> tiene 940 líneas (documentado como deuda asumida — partir conlleva alto riesgo). El resto del frontend está bajo 400 líneas/archivo.</td>
</tr>
<tr>
  <td>🪜 <strong>Prop drilling</strong></td>
  <td>TanStack Query como state manager remoto. Auth en Context. No se pasan callbacks 5 niveles abajo.</td>
</tr>
<tr>
  <td>🔢 <strong>Magic numbers</strong></td>
  <td>Constantes en <code>lib/constants.ts</code> con nombres descriptivos.</td>
</tr>
<tr>
  <td>📝 <strong>Magic strings</strong></td>
  <td>Status de chollos vienen de <code>DEAL_STATUS_OPTIONS as const</code> con literal types.</td>
</tr>
<tr>
  <td>🧶 <strong>Stringly typed</strong></td>
  <td>Pydantic en backend + Zod en frontend + TS strict.</td>
</tr>
<tr>
  <td>📤 <strong>Stack trace al cliente</strong></td>
  <td>El handler global devuelve siempre <em>"Error interno del servidor"</em>. El detalle queda en logs internos.</td>
</tr>
<tr>
  <td>🛡️ <strong>Validar sólo en el cliente</strong></td>
  <td>Doble validación documentada en <a href="../adr/ADR-005-validacion-doble-frontera.md">ADR-005</a>.</td>
</tr>
<tr>
  <td>🔑 <strong>Secretos en el código</strong></td>
  <td><code>.env*</code> en <code>.gitignore</code>, gitleaks en CI, política de regeneración documentada.</td>
</tr>
<tr>
  <td>🎭 <strong>Confiar en isAdmin del cliente</strong></td>
  <td><code>require_admin</code> consulta directamente <code>user_roles</code> con SQL parametrizado.</td>
</tr>
<tr>
  <td>🃏 <strong>Mockear en exceso</strong></td>
  <td>Los integration tests tienen ≤3 mocks (sólo fronteras).</td>
</tr>
</tbody>
</table>

---

## 📋 Deuda asumida (conscientemente)

> No todo se puede ni se debe perfeccionar. Lo siguiente está
> **conscientemente** dejado como mejora futura, con justificación en
> [`09 · Limitaciones y mejoras futuras`](09-limitaciones-y-mejoras-futuras.md).

- 🪨 `admin.chollos.tsx` God Component (940 líneas)
- ♿ A11y warnings en algunos formularios admin
- 🎨 `style-src 'unsafe-inline'` en CSP (necesario para React + shadcn)
- 📷 Visual regression con `toHaveScreenshot`
- 🎭 Page Object Model elaborado
- 🤖 DAST automatizado con OWASP ZAP
- 📜 SBOM con CycloneDX

✅ **La decisión de NO hacer estas cosas es tan importante como las que sí se hicieron**: evita sobreingeniería y mantiene el coste de cambio bajo.

---

<p align="center">
  <a href="04-arquitectura-y-decisiones-tecnicas.md">← Anterior: Arquitectura</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="06-calidad-testing-y-refactorizacion.md">Siguiente: Calidad y testing →</a>
</p>
