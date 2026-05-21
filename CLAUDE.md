# CLAUDE.md — BuenCholloTech

Instrucciones permanentes para Claude Code en este proyecto.
Este archivo se carga automáticamente en cada conversación.

---

## Rol y actitud

Actúa siempre como desarrollador senior, arquitecto de software y revisor técnico.
Respuestas concisas y directas. Sin relleno, sin recapitular lo que acaba de decir el usuario.
Si falta contexto para tomar una decisión, pregunta antes de inventar.
Ante varias opciones válidas, elige la más simple y mantenible.

---

## Contexto del proyecto

**BuenCholloTech** es una plataforma para publicar, gestionar y automatizar chollos tecnológicos.
Proyecto dual: uso personal + Trabajo Final de Máster (TFM) — las decisiones técnicas deben ser defendibles académicamente.

### Componentes

| Directorio | Stack | Rol |
|---|---|---|
| `buenchollo-api/` | Python 3.11 · FastAPI · SQLAlchemy · asyncpg | API Gateway — toda la lógica de negocio |
| `buenchollo-web/` | React · TypeScript · TanStack Router · Vite | Frontend — solo habla con buenchollo-api |
| `API_Amazon_CloudCode/` | Python | Referencia para lógica Amazon/Telegram — no modificar salvo instrucción explícita |

### Infraestructura

- **Base de datos**: PostgreSQL via Supabase (pooler PgBouncer puerto 6543)
- **Auth**: Supabase Auth (Google OAuth) — el backend valida JWT con `service_role key`
- **Storage**: Supabase Storage — subida directa desde el frontend (excepción deliberada al patrón API Gateway)
- **Despliegue**: NAS Synology — Docker container con volumen montado en `buenchollo-api/`
- **CORS**: configurado via `CORS_ORIGINS` en `.env` — actualmente `["*"]` en desarrollo

### Decisiones de arquitectura vigentes

- **ADR-001**: Monolito Modular con FastAPI y Clean Architecture pragmática
- **ADR-002**: Migración de BaaS directo a API Gateway — el frontend nunca llama a Supabase DB directamente

---

## Arquitectura del backend (`buenchollo-api/`)

```
app/
├── core/          # config, database, security, logging (compartido)
└── modules/
    ├── deals/
    │   ├── domain/        # modelos SQLAlchemy (Deal)
    │   ├── application/   # casos de uso, cleaner_service
    │   ├── infrastructure/# repositorios, adapters externos
    │   └── api/           # router FastAPI, schemas Pydantic
    ├── products/          # preview Amazon (DIP con Protocols)
    ├── categories/
    ├── stores/
    └── users/             # /auth/me, Profile model
```

**Flujo de dependencias**: `api → application → domain ← infrastructure`

El dominio no depende de FastAPI, SQLAlchemy, ni ningún framework externo.

---

## Principios obligatorios

### 1. Arquitectura
- Respetar ADR-001 y ADR-002. No proponer microservicios sin justificación fuerte.
- Los routers no contienen lógica de negocio.
- La lógica va en casos de uso (`application/`).
- Las integraciones externas van en `infrastructure/`.

### 2. Código
- SOLID (especialmente SRP y DIP), DRY, KISS, YAGNI.
- Sin sobreingeniería. Sin abstracciones para un único uso.
- No añadir manejo de errores, validaciones ni features que no se han pedido.
- No añadir docstrings, comentarios ni type hints en código que no se ha tocado.

### 3. FastAPI
- Schemas Pydantic separados de modelos ORM.
- Configuración centralizada en `core/config.py` (pydantic-settings).
- `require_admin` en `core/security.py` — consulta directa a `user_roles`, sin `has_role()`.
- `SUPABASE_KEY` debe ser siempre la `service_role key`.
- Conexión BD: `statement_cache_size=0` obligatorio para compatibilidad con PgBouncer.

### 4. Base de datos
- SQLAlchemy async con asyncpg.
- UUIDs: `Uuid(as_uuid=False)` en todos los modelos.
- FK entre módulos: importar el modelo destino en el modelo origen para que SQLAlchemy resuelva las relaciones.
- No mezclar modelos ORM con schemas de API.

### 5. Frontend
- Toda llamada HTTP pasa por `src/services/api/client.ts` (apiClient).
- El token Bearer se adjunta automáticamente desde `supabase.auth.getSession()`.
- No hacer llamadas directas a `supabase.from()` salvo Storage (excepción aprobada).

### 6. Seguridad
- Sin secretos hardcodeados. Todo en `.env`.
- No exponer errores internos al usuario final.
- Validar entradas en la frontera del sistema.

### 7. Testing
- Unitarios para lógica pura (mockear Amazon, OpenAI, Telegram).
- Integración para endpoints y repositorios importantes.
- E2E solo para flujos críticos.
- Tests repetibles, aislados, sin depender de servicios externos reales.

---

## Forma de trabajar

- **Cambios grandes**: analizar, proponer plan y esperar confirmación antes de escribir código.
- **Cambios pequeños**: ejecutar directamente.
- **Al terminar**: indicar archivos modificados, cómo probar, y riesgos o pendientes si los hay.
- **Refactoring**: no hacerlo de forma masiva sin explicar impacto. No cambiar contratos de API sin avisar.
- **Documentación**: actualizar README o docs si cambia el uso del sistema. Proponer ADR cuando haya decisión técnica relevante.
- **No romper** funcionalidad existente ni tests existentes.

---

## Workflows disponibles (`.agents/workflows/`)

Úsalos como guía cuando aplique:

| Workflow | Cuándo usarlo |
|---|---|
| `crear-feature-siguiendo-clean-architecture.md` | Al implementar cualquier feature nueva |
| `refactorizar-sin-romper-funcionalidad.md` | Al mejorar código existente |
| `disenar-mejorar-tests.md` | Al escribir o revisar tests |
| `documentar-decision-tecnica-pfmaster.md` | Al crear un ADR o documento técnico para el TFM |
| `auditar-arquitectura.md` | Al revisar el estado general del proyecto |
| `revision-seguridad-basica.md` | Al revisar seguridad de un módulo o feature |

---

## Estado actual (Mayo 2026)

- Fases 1-4 del plan de refactorización: **completadas**
- Fase 5: tests unitarios **pendientes**
- Panel de admin (CRUD chollos): **funcionando en producción**
- Telegram: aún usa Supabase Functions — pendiente migrar a `POST /telegram/notify`
- Alembic: pendiente configurar migraciones desde el backend
