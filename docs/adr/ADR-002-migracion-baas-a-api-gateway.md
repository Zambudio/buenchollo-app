# ADR-002 — Migración de BaaS directo a API Gateway con FastAPI

| Campo        | Valor                                      |
|--------------|--------------------------------------------|
| **Estado**   | Aceptado                                   |
| **Fecha**    | 2026-05-19                                 |
| **Autores**  | Pedro Zambudio                             |
| **Relacionado** | [ADR-001](ADR-001-monolito-modular-fastapi.md) (Monolito Modular con FastAPI)  |

---

## Contexto

El ADR-001 declaraba la intención de construir un "Monolito Modular con FastAPI". Sin embargo, la implementación real derivó en una arquitectura **BaaS directa**: el frontend React llamaba a Supabase sin intermediario (RLS, PostgREST, Storage), y FastAPI actuaba únicamente como microservicio satélite para scraping Amazon y llamadas OpenAI.

Esta situación presentaba riesgos críticos:

- **Acoplamiento extremo frontend-BD**: Los componentes React conocían los nombres de tablas, columnas y las restricciones de la BD. Cambiar el esquema implicaba modificar el frontend.
- **Lógica de negocio distribuida**: Las validaciones residían en RLS de Supabase, el frontend y el backend por separado, sin una fuente de verdad única.
- **Autenticación dual e inconsistente**: El frontend gestionaba la sesión de Supabase Auth de forma independiente; FastAPI no podía ejercer autorización centralizada.
- **Imposibilidad de testing unitario del frontend**: Los `useEffect` con llamadas directas a `supabase.from()` no se pueden mockear de forma limpia.
- **CORS abierto a `*`**: Con credenciales JWT, el navegador exige un origen específico; `*` con `credentials: true` es inconsistente y puede fallar en ciertos browsers.

---

## Decisión

Migrar completamente a un patrón **API Gateway**: FastAPI centraliza **toda** la lógica de lectura y escritura; el frontend solo habla con FastAPI y nunca directamente con Supabase.

```
ANTES:
  Browser ──► Supabase (PostgREST / Auth / Storage)
  Browser ──► FastAPI  (scraping, OpenAI)

DESPUÉS:
  Browser ──► FastAPI (toda la lógica de negocio)
                ├──► PostgreSQL / Supabase DB (via SQLAlchemy)
                ├──► Supabase Auth (validación JWT)
                ├──► Supabase Storage (solo para imágenes, desde el cliente)
                └──► APIs externas (Amazon, OpenAI)
```

La excepción deliberada es **Supabase Storage**: las imágenes se suben directamente desde el navegador (por tamaño y latencia), y el backend solo almacena la URL pública resultante.

---

## Consecuencias

### Positivas

1. **Una sola capa de autorización**: `require_admin` en FastAPI valida JWT + rol antes de cualquier operación de escritura. El frontend no puede saltarse esta validación.
2. **Esquema de BD desacoplado del frontend**: El frontend trabaja con DTOs de Pydantic (`DealCardResponse`, `DealCreate`, etc.). Cambios internos de esquema no rompen la interfaz.
3. **CORS explícito y configurable**: `CORS_ORIGINS` en `.env` permite listar dominios exactos en producción, eliminando el `allow_origins=["*"]` inseguro.
4. **Testabilidad**: El backend tiene tests de integración reales (`test_deals_api.py`) que prueban el ciclo completo create/update/delete contra la BD real. El frontend puede mockearse a nivel de `fetch`.
5. **Trazabilidad**: Todos los errores (401, 403, 422, 500) pasan por FastAPI y son logeables. El endpoint `/auth/me` permite diagnóstico de sesión en producción sin abrir la BD.
6. **Inversión de Dependencias (DIP)**: El caso de uso `PreviewProductFromUrlUseCase` depende de Protocols (`ProductPreviewProvider`, `CategoryClient`, `AIEnricher`), no de implementaciones concretas. Los adaptadores de infraestructura (Amazon, Supabase, OpenAI) se inyectan en el router.

### Negativas / Trade-offs

- **Latencia añadida**: Cada request pasa ahora por FastAPI antes de llegar a la BD. En la práctica, con el backend en el mismo NAS que el cliente de red local, es despreciable.
- **Mantenimiento del doble contrato**: Hay que mantener los modelos SQLAlchemy sincronizados con el esquema de Supabase. Alembic gestiona las migraciones.
- **Supabase Storage sigue siendo directo**: La subida de imágenes permanece en el cliente por razones de rendimiento. Se acepta este acoplamiento puntual y controlado.

---

## Alternativas consideradas

| Alternativa | Razón de rechazo |
|---|---|
| Mantener BaaS directo con RLS más estricto | No resuelve el acoplamiento del frontend ni la falta de lógica de negocio central. |
| Migrar a una BD completamente gestionada por FastAPI (sin Supabase) | Alto coste de migración; Supabase Auth, Storage y Realtime siguen aportando valor. |
| GraphQL sobre Supabase | Aumenta la complejidad sin resolver el problema de autorización centralizada. |

---

## Estado de la migración

| Fase | Descripción | Estado |
|---|---|---|
| Fase 1 | SQLAlchemy + Alembic + modelos de dominio | ✅ Completada |
| Fase 2 | Endpoints REST + autenticación JWT | ✅ Completada |
| Fase 3 | Desacople del frontend (lectura + escritura admin) | ✅ Completada |
| Fase 4 | Clean Architecture + CORS + Scheduler lifespan | ✅ Completada |
| Fase 5 | Tests + ADR-002 + documentación | ✅ En curso |
