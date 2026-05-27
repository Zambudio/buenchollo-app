# ADR-004 — Persistencia con SQLAlchemy async + asyncpg + PgBouncer

| Campo        | Valor                                            |
|--------------|--------------------------------------------------|
| **Estado**   | Aceptado                                         |
| **Fecha**    | 2026-05-27                                       |
| **Autores**  | Pedro Zambudio                                   |
| **Relacionado** | [ADR-001](ADR-001-monolito-modular-fastapi.md), [ADR-002](ADR-002-migracion-baas-a-api-gateway.md), [ADR-006](ADR-006-rls-service-role.md) |

---

## Contexto

BuenCholloTech necesita persistir chollos, comentarios, votos, alertas,
notificaciones y perfiles. Requisitos de la capa de persistencia:

- Acceso **asíncrono** desde FastAPI (no bloquear el event loop).
- **Postgres** como motor (lo que provee Supabase y lo que conocemos).
- **Pool de conexiones** robusto: Supabase fuerza el uso de PgBouncer en
  modo `transaction` (puerto 6543) para limitar conexiones simultáneas.
- **Tipos ricos**: UUIDs, timestamps con zona horaria, JSON, arrays.
- **Migraciones versionadas** del esquema.
- **Testabilidad**: que el repositorio se pueda mockear sin necesidad de BD
  real para tests unitarios (ya conseguido en el refactor 2026-05-26).

Opciones evaluadas:

1. **Supabase JS / Python SDK** directamente desde el backend
   (`supabase.table("deals").select(...)`). Más ergonómico para CRUD simple,
   pero rompería la separación de capas: el backend acabaría parecido al
   antiguo frontend pre-ADR-002.
2. **asyncpg "a pelo"** con queries SQL escritas a mano. Máximo rendimiento
   y control, pero alto coste de mantenimiento (mapeo manual a DTOs,
   sin validación de tipos en compile time).
3. **SQLAlchemy 2.x async + asyncpg como driver**. Verbose pero ofrece ORM
   tipado, migraciones (Alembic), pool propio, expresiones SQL declarativas
   y compatibilidad con tests.
4. **SQLModel** (Pydantic + SQLAlchemy). Reduce código repetido pero al
   precio de acoplar modelo de dominio a Pydantic, y todavía no es estable
   para producción en su versión async.
5. **Tortoise ORM / Piccolo**. ORM Python async modernos, pero comunidad
   menor y menor compatibilidad con drivers/herramientas (sobre todo Alembic).

---

## Decisión

**SQLAlchemy 2.x con motor async + driver `asyncpg`**, conectado al pooler
PgBouncer de Supabase (puerto 6543, modo `transaction`).

Configuración concreta (ver
[`buenchollo-api/app/core/database.py`](../../buenchollo-api/app/core/database.py)):

```python
engine = create_async_engine(
    settings.database_url,                # postgresql+asyncpg://...:6543/...
    echo=settings.log_level == "DEBUG",
    future=True,
    pool_pre_ping=True,                   # detecta conexiones muertas
    connect_args={
        "server_settings": {"jit": "off"},
        "statement_cache_size": 0,        # obligatorio con PgBouncer transaction
    },
)
```

Convenciones de modelado:

- Todos los IDs son `UUID` representados como **string** en Python:
  `Mapped[str] = mapped_column(Uuid(as_uuid=False), ...)`. Evita problemas de
  serialización con FastAPI/Pydantic, mantiene el formato textual de Supabase.
- Timestamps siempre `DateTime(timezone=True)` con `server_default=func.now()`.
- Relaciones cross-módulo se resuelven con strings (`relationship("Category")`)
  y se garantizan importando el módulo destino al cargar el origen (ver
  comentario `noqa: F401` en `deals/domain/models.py`).
- Repositorios encapsulan TODA la persistencia. Las capas `application/` y
  `api/` no construyen queries SQL ni invocan a `session.execute` directamente.
- `get_db` (`AsyncSession` por dependencia) hace commit al final del request
  y rollback en excepción. No hay sesiones globales ni de proceso.

Migraciones:

- Las migraciones SQL viven en `buenchollo-api/supabase/migrations/`
  (movidas desde `buenchollo-web/supabase/` en F2.1 del plan, 2026-05-27).
  **F2.2** introducirá Alembic con baseline sobre el esquema actual para
  versionado nativo SQLAlchemy yendo adelante.

---

## Consecuencias

### Positivas

- **No bloquea el event loop**: `async/await` end-to-end desde el router
  hasta la BD. Una petición lenta no congestiona el servidor.
- **Compatibilidad con PgBouncer transaction mode**: clave para escalar.
  `statement_cache_size=0` y `jit=off` evitan los dos errores típicos
  (`prepared statement does not exist` y planes que mueren al recibir
  parámetros distintos).
- **Tipado fuerte**: `Mapped[str | None]`, `select(Deal).where(...)`. El IDE
  detecta errores antes de ejecutar.
- **Repos testables**: los unitarios del 2026-05-26 (`test_deal_service.py`,
  `test_alert_matching.py`) mockean los repos con `AsyncMock` y no tocan
  BD ni red. Cobertura real sin docker-compose.
- **Migraciones a futuro con Alembic**: al ser SQLAlchemy nativo, generar
  migraciones es `alembic revision --autogenerate -m "..."` y revisar.
- **Independencia del proveedor**: si mañana se migra a Postgres self-hosted
  o AWS RDS, sólo cambia el `DATABASE_URL`. Cero cambios de código.

### Negativas

- **Aceptamos "primitive obsession" pragmática en el dominio**: los modelos
  SQLAlchemy son a la vez modelos de dominio. Decisión consciente
  documentada en ADR-001 ("Clean Architecture pragmática"). Mantener
  entidades puras separadas de los ORM models requeriría mappers que para
  este alcance no compensan.
- **`statement_cache_size=0` tiene un coste de rendimiento medible** al no
  reutilizar planes preparados. En la práctica es despreciable frente a la
  latencia red Supabase, pero conviene revisitarlo si en el futuro se
  identifica como cuello de botella (la alternativa sería usar el pooler
  en modo `session` — puerto 5432 — limitando severamente el número de
  conexiones concurrentes).
- **No usar el SDK de Supabase desde el backend** significa que features
  como Realtime, RPC o Storage no se aprovechan "gratis". Mitigación: para
  Realtime existen WebSockets/SSE nativos en FastAPI cuando se necesiten;
  el RPC `get_user_stats` se invoca puntualmente con `text(...)` desde el
  repo de usuarios.

---

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Supabase SDK en backend | Ergonomía buena pero acoplaría el backend al SDK comercial y rompería la simetría arquitectónica con `repositorios`. Empeora la portabilidad. |
| asyncpg a pelo | Productividad muy baja para un proyecto con 12 tablas y relaciones. Sin Alembic. Sin tipado. |
| SQLModel | Estado del soporte async todavía no equiparable a SQLAlchemy 2.x al inicio del proyecto. Reevaluable a futuro. |
| Tortoise/Piccolo | Comunidad/ecosistema menores. Menos seniors disponibles si BuenChollo crece y se incorporan colaboradores. |
| ORM síncrono (SQLModel sync, Django ORM) | FastAPI es async-first; mezclar driver síncrono obliga a `run_in_threadpool` y mata las ventajas. |

---

## Notas de implementación

- **Connection string** (`.env`):
  `DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<password>@aws-0-eu-...-1.pooler.supabase.com:6543/postgres`.
  Es el pooler PgBouncer. Si por algún test/exporación se necesita modo
  `session`, cambiar a puerto **5432** (no recomendado en producción).
- **No usar `prepared_statement_cache_size`** distinto de cero. Romperá en
  el momento más inesperado en producción.
- **Modelos cross-módulo**: para que `Deal.created_by → profiles.user_id`
  funcione en el primer arranque, `deals/domain/models.py` importa
  `app.modules.users.domain.models  # noqa: F401`. Es el patrón estándar
  para resolver `relationship("ClassName")` por string.
- **`expire_on_commit=False`**: necesario para devolver entidades fuera
  del scope del session sin lazy-loading inesperado tras `commit`.

---

## Evolución prevista

- **F2.1**: mover migraciones SQL al backend (`buenchollo-api/supabase/migrations/`).
- **F2.2**: configurar Alembic con baseline sobre el esquema actual; futuras
  migraciones generadas con `alembic revision --autogenerate`.
- **Medio plazo**: si los joins crecen y el rendimiento se resiente, evaluar
  añadir índices selectivos (perfiles, `deals(status, published_at)`,
  `deal_comments(deal_id)`, `favorites(user_id)` ya existen via Supabase UI).
- **Largo plazo**: si volumen crece a millones de filas, evaluar particionado
  por fecha en `deals` y `deal_comments`. Postgres lo soporta nativo.
