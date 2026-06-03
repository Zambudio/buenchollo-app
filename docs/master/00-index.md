# Documentación de entrega — Trabajo Final de Máster

> Documentación formal del proyecto **BuenCholloTech** para la defensa
> ante tribunal del **Máster en Desarrollo con IA 2025**.
>
> Para la operativa del repositorio (instalación, comandos, troubleshooting)
> ver [`docs/project/`](../project/00-index.md).

## Índice

1. [01 — Introducción del proyecto](01-introduccion-del-proyecto.md)
   Contexto, motivación, problema que resuelve, alcance del proyecto.

2. [02 — Objetivos y alcance](02-objetivos-y-alcance.md)
   Objetivo general, objetivos específicos, alcance funcional y técnico,
   qué queda fuera.

3. [03 — Análisis funcional](03-analisis-funcional.md)
   Usuarios previstos, funcionalidades principales, flujos de uso,
   casos de uso, limitaciones funcionales.

4. [04 — Arquitectura y decisiones técnicas](04-arquitectura-y-decisiones-tecnicas.md)
   Arquitectura elegida (monolito modular + API Gateway), justificación,
   organización, dependencias externas, referencia a los 9 ADRs.

5. [05 — Buenas prácticas y principios de diseño](05-buenas-practicas-y-principios-de-diseno.md)
   Cómo se han aplicado SOLID, DRY, KISS, YAGNI; refactorizaciones
   documentadas; antipatrones evitados.

6. [06 — Calidad, testing y refactorización](06-calidad-testing-y-refactorizacion.md)
   Estrategia de calidad, pirámide de testing, coverage estratégico,
   métricas accionables, quality gates.

7. [07 — Seguridad](07-seguridad.md)
   Security by Design, Security by Default, OWASP Top 10 aplicado,
   controles implementados, riesgos detectados y mitigaciones,
   mejoras futuras.

8. [08 — Uso de IA en el desarrollo](08-uso-de-ia-en-el-desarrollo.md)
   Herramientas, patrones de uso, supervisión humana, ejemplos
   concretos, riesgos y mitigaciones aplicadas.

9. [09 — Limitaciones y mejoras futuras](09-limitaciones-y-mejoras-futuras.md)
   Limitaciones actuales del proyecto y mejoras técnicas, funcionales,
   de seguridad, rendimiento y testing.

10. [10 — Conclusiones](10-conclusiones.md)
    Qué se ha aprendido, qué demuestra el proyecto, contenidos del
    máster aplicados, valor del proyecto, pasos futuros.

## Lectura recomendada por bloque del máster

| Bloque del máster | Documentos clave |
|---|---|
| **Arquitectura de Software** | `04`, `05`, [`docs/adr/`](../adr/00-index.md) |
| **Calidad del Software** | `06`, [`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md) (no, esto es seguridad), [`docs/project/06-testing-and-quality.md`](../project/06-testing-and-quality.md) |
| **Seguridad** | `07`, [`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md), [`SECURITY.md`](../../SECURITY.md) |
| **Desarrollo con IA** | `08`, [ADR-009](../adr/ADR-009-uso-de-ia-en-desarrollo.md), [`CLAUDE.md`](../../CLAUDE.md) |
| **Cierre / Conclusiones** | `01`, `09`, `10` |

## Documentación complementaria

- [`docs/adr/`](../adr/00-index.md) — 9 ADRs firmados y datados.
- [`docs/reference/PLAN_ARQUITECTURA.md`](../reference/PLAN_ARQUITECTURA.md) — Sprint completo de hardening F1–F7 con métricas.
- [`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md) — Auditoría OWASP Top 10 con 10 hallazgos priorizados.
- [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md) — Bitácora viva del proyecto (cronología completa de sprints).
