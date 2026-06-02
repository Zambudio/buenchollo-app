# Documentación operativa — BuenCholloTech

> Documentación del repositorio: útil para instalar, ejecutar, mantener
> y evolucionar BuenCholloTech.
>
> Para la documentación de **defensa académica** ver
> [`docs/master/`](../master/00-index.md).

## Índice

1. [01 — Overview](01-overview.md) — Qué es, problema que resuelve, módulos, roles, flujo.
2. [02 — Instalación y setup](02-installation-and-setup.md) — Clonado, backend, frontend, Supabase, servicios externos.
3. [03 — Estructura del proyecto](03-project-structure.md) — Monorepo, Clean Architecture, organización por features, UI System.
4. [04 — Configuración](04-configuration.md) — Variables de entorno detalladas (backend, frontend, CI).
5. [05 — Flujo de desarrollo](05-development-workflow.md) — Husky, commits, ramas, uso de IA.
6. [06 — Testing y calidad](06-testing-and-quality.md) — Comandos, gates, coverage estratégico, métricas.
7. [07 — Seguridad](07-security.md) — Controles, política `--no-verify`, respuesta a incidentes.
8. [08 — Despliegue](08-deployment.md) — NAS Synology + Docker, reverse proxy, dominio definitivo.
9. [09 — Troubleshooting](09-troubleshooting.md) — Errores comunes y soluciones.

## Documentación complementaria

- [`docs/adr/`](../adr/00-index.md) — Decisiones arquitectónicas (ADRs).
- [`docs/master/`](../master/00-index.md) — Documentación de defensa TFM.
- [`docs/reference/`](../reference/) — Referencias técnicas densas:
  - `PLAN_ARQUITECTURA.md` — sprint de hardening F1–F7.
  - `SECURITY_AUDIT.md` — auditoría OWASP completa.
  - `SMOKE_TEST.md` — checklist manual pre-release.
- [`buenchollo-api/MIGRATIONS.md`](../../buenchollo-api/MIGRATIONS.md) — Setup Alembic.
- [`docs/archive/`](../archive/) — Documentación histórica preservada.
