# Architecture Decision Records (ADRs)

> Decisiones arquitectónicas firmadas y datadas. Cada ADR documenta el
> contexto del problema, las alternativas consideradas, la decisión
> tomada y sus consecuencias.

## Índice

| # | Decisión | Estado | Fecha |
|---|---|---|---|
| [001](ADR-001-monolito-modular-fastapi.md) | Monolito Modular con FastAPI y Clean Architecture pragmática | ✅ Aceptado | 2026-05-13 |
| [002](ADR-002-migracion-baas-a-api-gateway.md) | Migración de BaaS directo a API Gateway | ✅ Aceptado · cumplido 100% | 2026-05-21 |
| [003](ADR-003-autenticacion-supabase-jwt.md) | Autenticación con Supabase Auth + validación de JWT en backend | ✅ Aceptado | 2026-05-27 |
| [004](ADR-004-persistencia-sqlalchemy-pgbouncer.md) | Persistencia con SQLAlchemy async + asyncpg + PgBouncer | ✅ Aceptado | 2026-05-27 |
| [005](ADR-005-validacion-doble-frontera.md) | Validación en doble frontera con Zod (cliente) y Pydantic (servidor) | ✅ Aceptado | 2026-05-27 |
| [006](ADR-006-rls-service-role.md) | Hardening de RLS y separación `anon` / `service_role` | ✅ Aceptado | 2026-05-27 |
| [007](ADR-007-di-fastapi-depends.md) | Inyección de dependencias con `Depends` de FastAPI | ✅ Aceptado | 2026-05-27 |
| [008](ADR-008-estrategia-calidad-testing.md) | Estrategia de calidad y testing 100/80/0 con pirámide unit/integration/E2E | ✅ Aceptado | 2026-06-02 |
| [009](ADR-009-uso-de-ia-en-desarrollo.md) | Uso de IA como apoyo supervisado al desarrollo | ✅ Aceptado | 2026-06-02 |

## Cómo se usa este directorio

- **Para entender el "por qué"** de una decisión técnica: leer el
  ADR correspondiente.
- **Para tomar una nueva decisión importante**: crear un nuevo ADR
  numerado (`ADR-XXX-slug-descriptivo.md`) siguiendo el formato.
- **Para reemplazar una decisión** anterior: marcar el ADR antiguo
  como "Reemplazado por ADR-XXX" y crear el nuevo con el contexto del
  cambio.

## Formato estándar

Cada ADR sigue esta estructura:

```markdown
# ADR-XXX — Título de la decisión

## Estado
Aceptado | Propuesto | Reemplazado por ADR-YYY

## Contexto
Qué problema o decisión había que resolver.

## Decisión
Qué se decidió.

## Motivo
Por qué se eligió esa opción.

## Alternativas consideradas
Qué otras opciones se valoraron y por qué se descartaron.

## Consecuencias
Ventajas, inconvenientes y efectos futuros.
```

## Mapa por bloque del máster

| Bloque del máster | ADRs relevantes |
|---|---|
| **Arquitectura de Software** | 001, 002, 004, 007 |
| **Calidad del Software** | 008 |
| **Seguridad** | 003, 005, 006 |
| **Desarrollo con IA** | 009 |
