# ADR-007 — Inyección de dependencias con `Depends` de FastAPI

| Campo        | Valor                                            |
|--------------|--------------------------------------------------|
| **Estado**   | Aceptado                                         |
| **Fecha**    | 2026-05-27                                       |
| **Autores**  | Pedro Zambudio                                   |
| **Relacionado** | [ADR-001](ADR-001-monolito-modular-fastapi.md), [ADR-004](ADR-004-persistencia-sqlalchemy-pgbouncer.md) |

---

## Contexto

El proyecto sigue Clean Architecture pragmática (ADR-001). Como tal, los
casos de uso (`DealService`, `AlertMatcher`, `PreviewProductFromUrlUseCase`)
dependen de **abstracciones** (repos, adaptadores) que se construyen en
algún sitio y se inyectan donde toca.

Necesitamos resolver:

1. **Dónde ensamblar las dependencias** (composition root).
2. **Cómo gestionar el scope**: la `AsyncSession` debe ser per-request (no
   global); el cliente HTTP de Supabase puede ser singleton o per-request.
3. **Cómo testear**: poder sustituir un repo real por uno fake/mock sin
   tocar el código de producción.

Opciones evaluadas:

1. **IoC container externo** tipo `dependency-injector` o `punq`. Potente,
   declarativo. Coste: añade un concepto más a aprender, configuración
   separada del código que la usa, doble fuente de verdad.
2. **Construcción manual** con un fichero `composition_root.py` central.
   Explícito y sencillo. Coste: si añades una dependencia, hay que tocar
   ese fichero. Para FastAPI implica además gestionar scopes (per-request
   sessions) "a mano".
3. **`Depends` nativo de FastAPI**. Es el sistema de DI integrado del
   framework. Resuelve scopes automáticamente, encadena dependencias por
   firma de función, e integra el override para tests.
4. **Service Locator pattern**. Antipatrón documentado. Descartado.

---

## Decisión

**`Depends` de FastAPI como sistema de inyección de dependencias**.
El composition root está **distribuido en factories `get_X()`** que viven
junto al router del módulo que las consume.

### Patrón estándar

```python
# En cada router, factories que ensamblan la cadena:
def get_deal_repository(db: AsyncSession = Depends(get_db)) -> DealRepository:
    return DealRepository(db)

def get_deal_service(db: AsyncSession = Depends(get_db)) -> DealService:
    repo = DealRepository(db)
    matcher = AlertMatcher(AlertRepository(db), NotificationRepository(db))
    return DealService(repo, matcher)

# Los endpoints declaran sus deps por firma:
@router.post("/admin", response_model=DealDetailResponse)
async def create_deal(
    deal_in: DealCreate,
    service: DealService = Depends(get_deal_service),
    current_user=Depends(require_admin),
):
    return await service.create_deal(deal_in.model_dump(...), str(current_user.id))
```

### Scopes resueltos automáticamente

| Recurso | Scope | Quién lo construye |
|---|---|---|
| `Settings` | Singleton (`@lru_cache`) | `core/config.get_settings` |
| `AsyncSession` | Per-request | `core/database.get_db` con `async with` |
| `Repositories` | Per-request (reciben sesión) | `get_X_repository` |
| `Services / use cases` | Per-request (reciben repos) | `get_X_service` |
| `Supabase Client` (auth) | Per-request | `core/security.get_supabase_client` |
| `Current user` | Per-request (resuelto desde JWT) | `core/security.get_current_user` |
| `require_admin` | Per-request (encadena `get_current_user`) | `core/security.require_admin` |

FastAPI resuelve la cadena automáticamente: para `require_admin` carga
`get_current_user` → que carga `get_supabase_client` → que carga
`get_settings`. Si una dependencia se usa varias veces en la misma
petición, FastAPI la cachea por defecto (`use_cache=True`).

### Testing

`app.dependency_overrides` permite sustituir cualquier factory por una
implementación de test. Patrón ya usado en
[`buenchollo-api/app/tests/test_deals_api.py`](../../buenchollo-api/app/tests/test_deals_api.py):

```python
async def mock_require_admin():
    return MockUser()

@pytest.fixture(autouse=True)
def override_admin():
    app.dependency_overrides[require_admin] = mock_require_admin
    yield
    app.dependency_overrides.clear()
```

Para tests unitarios que **no levantan FastAPI** (`test_deal_service.py`,
`test_alert_matcher.py`), construimos las dependencias manualmente con
`AsyncMock` y `SimpleNamespace`. La arquitectura lo permite porque
`DealService(repo, matcher=None)` acepta cualquier objeto que respete la
interfaz, no requiere pasar por `Depends`.

---

## Consecuencias

### Positivas

- **Idiomático en FastAPI**: cualquiera que conozca el framework entiende
  el wiring sin documentación adicional.
- **Sin singletons globales** (excepto `Settings`, que es inmutable y
  cacheado con `lru_cache`). La sesión de BD vive y muere con la petición.
- **Composición explícita y cercana al uso**: la `get_deal_service` está
  al lado del router que la usa. No hay que ir a buscar un fichero remoto.
- **Override para tests trivial**: `app.dependency_overrides[X] = fake_X`.
- **Resolución de cadenas automática**: `require_admin` carga
  `get_current_user` que carga `get_supabase_client` sin que nadie tenga
  que orquestar el orden.
- **`@lru_cache` en `get_settings`** garantiza que la configuración se lee
  una sola vez por proceso.

### Negativas

- **Wiring distribuido**: cada módulo tiene sus factories en su router. Si
  alguien busca "todas las dependencias del sistema" no hay un único
  fichero. Mitigación: el nombre `get_X` es buscable globalmente con grep.
- **Acoplamiento sintáctico a FastAPI**: las factories usan `Depends(...)`
  en su firma. Si mañana se quisiera reusar la lógica de aplicación fuera
  de FastAPI (CLI, worker), las factories no servirían — pero los
  servicios (`DealService`, `AlertMatcher`) sí, porque su constructor no
  conoce `Depends`. Las factories son código de glue; reemplazables.
- **`Depends` tiene magia**: el flujo no es 100% linear en el código.
  Devs nuevos pueden tardar en entender por qué un parámetro "aparece
  rellenado". Mitigación: el patrón está en la documentación de FastAPI
  y este ADR lo enmarca.

---

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| `dependency-injector` | Buen producto, pero añade una capa de configuración separada que no aporta valor con FastAPI ya teniendo `Depends`. |
| `punq` | Similar, demasiado pequeño para justificar la introducción de un container externo. |
| Composition root central manual | Tendríamos que gestionar el scope per-request manualmente (escribir el `async with` por cada router). Reinventaría lo que ya hace `Depends`. |
| Service Locator | Antipatrón. Oculta dependencias en lugar de declararlas. |
| Constructor injection a pelo (instanciar todo en `main.py` y pasarlo a routers) | Imposible mantener el scope per-request de la sesión. |

---

## Convención que se sigue

Para añadir un módulo nuevo:

1. En `<modulo>/infrastructure/`, crear el repositorio (recibe `AsyncSession`).
2. En `<modulo>/application/`, crear el service (recibe el repositorio y
   cualquier otra dependencia por constructor).
3. En `<modulo>/api/router.py`, añadir factories `get_<modulo>_repository` y
   `get_<modulo>_service` que reciben `db: AsyncSession = Depends(get_db)`.
4. Los endpoints declaran las dependencias por firma con `Depends(...)`.
5. Para tests:
   - Unitarios: instanciar los servicios manualmente con mocks/stubs.
   - Integración: usar `app.dependency_overrides`.

---

## Evolución prevista

- **Corto plazo**: cuando se introduzca `request_id` (F3.1), se inyectará
  como dependencia opcional en los servicios que quieran loguearlo
  estructurado, vía `contextvars` para no contaminar firmas.
- **Medio plazo**: si crece el número de adaptadores externos (AliExpress,
  PCComponentes, scrapers), agruparlos en un `core/clients.py` con sus
  factories, manteniendo el patrón.
- **Largo plazo**: si la app se desacopla en workers (background jobs con
  Celery/Arq), los workers no usarán `Depends` — instanciarán los services
  manualmente. Para eso ya está preparada la arquitectura: los services no
  conocen `Depends`, sólo sus constructores. Las factories son sustituibles.
