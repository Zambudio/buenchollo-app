# ADR-001 — Arquitectura inicial: Monolito Modular con FastAPI

| Campo        | Valor                                            |
|--------------|--------------------------------------------------|
| **Estado**   | Superado parcialmente (ver ADR-002)              |
| **Fecha**    | Marzo 2026                                       |
| **Autores**  | Pedro Zambudio                                   |
| **Sustituido por** | [ADR-002](ADR-002-migracion-baas-a-api-gateway.md) (en la parte de arquitectura de datos) |

---

## Contexto

Al inicio del proyecto se debía elegir una arquitectura backend para BuenCholloTech. Las opciones principales eran:

1. **BaaS puro (Supabase directo)**: El frontend habla directamente con Supabase. No hay capa backend propia.
2. **Microservicios**: Servicios independientes por dominio (deals, users, products...).
3. **Monolito Modular con FastAPI**: Un único proceso Python con módulos bien separados internamente.

---

## Decisión

**Monolito Modular con FastAPI**, siguiendo principios de Clean Architecture de forma pragmática:

```
buenchollo-api/
└── app/
    ├── core/          # Configuración, BD, seguridad (compartido)
    └── modules/
        ├── deals/     # Dominio, aplicación, infraestructura, API
        ├── products/  # Idem
        ├── categories/
        ├── stores/
        └── users/
```

Cada módulo tiene sus propias capas:
- **domain/** — Modelos de negocio (SQLAlchemy, entidades)
- **application/** — Casos de uso, lógica de negocio
- **infrastructure/** — Repositorios, clientes externos
- **api/** — Router FastAPI, schemas Pydantic

Las dependencias apuntan siempre hacia dentro: `api → application → domain ← infrastructure`.

---

## Justificación

- **Simplicidad operativa**: Un solo proceso Docker, una sola imagen, un solo puerto. No hay orquestación de múltiples servicios.
- **Despliegue en NAS doméstico**: Recursos limitados. Los microservicios requieren infraestructura que no justifica la escala del proyecto.
- **Modularidad sin complejidad**: La separación por módulos permite extraer a microservicio en el futuro si fuera necesario, sin reescribir desde cero.
- **Mantenibilidad**: Un equipo de una persona puede mantener un monolito modular mucho más eficientemente que múltiples servicios.
- **Contexto académico**: La arquitectura es suficientemente elaborada para demostrar principios de diseño (SOLID, Clean Architecture) en el TFM.

---

## Consecuencias

### Positivas
- Desarrollo y despliegue simples.
- Fácil de entender y navegar.
- Una sola base de código para testear.

### Negativas / Limitaciones
- **Implementación real inicial**: La primera implementación derivó hacia un patrón BaaS donde el frontend accedía directamente a Supabase, dejando FastAPI como microservicio satélite. Esta desviación fue corregida en la **Fase 3 de refactorización** (documentada en ADR-002).
- **Escalabilidad**: Si la carga crece significativamente, el modelo monolítico podría ser un cuello de botella. Aceptable para el scope actual.

---

## Notas de evolución

El ADR-001 definía la intención arquitectónica. La ejecución inicial no cumplió esa intención (el frontend quedó acoplado a Supabase). ADR-002 documenta la corrección de esa desviación mediante la migración a API Gateway completo.

La arquitectura modular interna de FastAPI (módulos, capas dominio/aplicación/infraestructura) sigue vigente y es la base del sistema actual.
