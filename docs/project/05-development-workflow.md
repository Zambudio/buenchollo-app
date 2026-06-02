# 05 — Flujo de desarrollo

## Ciclo típico

```
1. git pull
2. tocar código (con asistente IA si conviene — ver más abajo)
3. ejecutar suite local: npm run quality / pytest -m "not integration"
4. git commit (Husky corre lint + typecheck)
5. git push (Husky corre vitest)
6. CI verifica (backend, frontend, e2e, security-audit)
7. mergear cuando los 4 jobs estén verdes
```

## Husky — gates locales

Configurado en `.husky/`. Se activa con `npm install` en la raíz del repo
(`prepare: "husky"` en el `package.json` root).

### Pre-commit (~10s)

```sh
cd buenchollo-web
npm run lint
npm run typecheck
```

Si falla, el commit se aborta.

### Pre-push (~3s)

```sh
cd buenchollo-web
npm run test:run    # 72 tests Vitest unit + integration
```

Si falla, el push se aborta.

### Bypass legítimo

```bash
git commit --no-verify -m "fix(prod): rollback urgente"
git push --no-verify
```

**Sólo** en emergencias. Reglas:

- Justificar en el mensaje del commit.
- Nunca en main directo si hay otros desarrolladores.
- El siguiente commit debe restaurar el estado verde.

## Convención de commits

Estilo **Conventional Commits** usado en el proyecto:

| Prefijo | Cuándo |
|---|---|
| `feat:` | Nueva funcionalidad |
| `feat(sec):` | Funcionalidad de seguridad |
| `feat(web):` | Cambios visibles del frontend |
| `fix:` | Bug fix |
| `fix(sec):` | Fix de seguridad referenciado a SECURITY_AUDIT |
| `fix(ci):` | Arreglo del pipeline |
| `chore:` | Tareas de mantenimiento (deps, configs, archivado) |
| `chore(web):` o `chore(deps):` | Variante con scope |
| `ci:` | Cambios en `.github/workflows/` |
| `docs:` | Sólo documentación |
| `refactor:` | Reorganizar sin cambiar comportamiento |
| `test:` | Tests nuevos o cambios en suite |
| `ux:` | Mejoras de experiencia de usuario sin cambio lógico |
| `debug:` | Cambios temporales para diagnosticar |

Cuerpo del commit: por qué, no qué. El `git log` ya muestra el "qué".

## Ramas

- `main`: única rama estable. CI verde permanente.
- Para cambios grandes (sprints F1-F7, Q1-Q7, S1-S7): commits pequeños
  directos a `main`, cada uno verificado en local antes del push.
- No hay PR workflow estricto porque el proyecto tiene un único
  mantenedor. Si se incorporara un segundo dev, pasaríamos a feature
  branches + PR review.

## Tag de release

```bash
git tag -a v1.0.0-tfm -m "Versión presentada como Trabajo Final de Máster"
git push origin v1.0.0-tfm
```

Convención **SemVer** + sufijo descriptivo cuando aplique.

## Uso de IA en el desarrollo

Esta sección documenta **cómo** se usa la IA en el día a día. El _por
qué_ y la defensa académica viven en
[`docs/master/08-uso-de-ia-en-el-desarrollo.md`](../master/08-uso-de-ia-en-el-desarrollo.md)
y en [ADR-009](../adr/ADR-009-uso-de-ia-en-desarrollo.md).

### Herramienta principal

**Claude Code** (Anthropic) con `CLAUDE.md` en la raíz del repo. El
fichero contiene:

- Rol que la IA debe asumir (desarrollador senior, arquitecto).
- Contexto técnico del proyecto.
- Principios obligatorios (Clean Architecture, SOLID, KISS, sin
  sobreingeniería).
- Workflows de auditoría disponibles.
- Reglas de seguridad explícitas.

### Patrones de uso aplicados

1. **Auditoría por módulo** (calidad, seguridad, arquitectura):
   prompts dedicados y largos que la IA usa para inspeccionar el código,
   producir informe y proponer cambios priorizados. La implementación
   se hace después en commits pequeños.
2. **Implementación guiada**: descripción funcional → IA propone plan
   (modo plan) → revisión humana → implementación commit a commit con
   tests entre cada paso.
3. **Refactor seguro**: la IA propone, los tests garantizan que no se
   rompe nada. Si una refactorización deja un test rojo, se revierte.

### Reglas de oro al usar IA

- **Nunca commitear código que no se entienda.**
- **Cada cambio se valida con tests** antes del commit.
- Si la IA propone algo que parece sobreingeniería (patrón complejo
  para un único uso, abstracción especulativa), rechazar y simplificar.
- Si la IA crea tests pasando: revisar que realmente prueban algo, no
  sólo que pasan.
- No subir prompts ni contexto de IA a logs ni telemetría.

### Lo que la IA NO sustituye

- Decisiones arquitectónicas: van a ADR firmados.
- Revisión de seguridad final antes de release.
- Decidir si una feature merece la pena o no.
- Validar que un E2E refleja un flujo real del usuario.

## Checks antes de subir cambios grandes

Manual rápido para tirar de un sprint:

```bash
# Backend
cd buenchollo-api
pytest -q -m "not integration"   # 87 tests, ~1s
pip-audit -r requirements.txt    # 0 CVEs

# Frontend
cd ../buenchollo-web
npm run quality                  # lint + typecheck + 72 vitest
npm run test:e2e                 # 8 playwright (levanta dev server)
npm audit --omit=dev --audit-level=high   # 0 high+

# Documentos
# verificar enlaces relativos en docs/ funcionan
```

Si los 5 están en verde y el `git log --oneline -5` tiene mensajes
limpios → push y verificar CI.
