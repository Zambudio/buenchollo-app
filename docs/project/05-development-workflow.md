# 💻 05 · Flujo de desarrollo

> **TL;DR** · `git pull` → tocar código (con IA si conviene) →
> `npm run quality` → `git commit` (Husky ejecuta lint+tsc) →
> `git push` (Husky ejecuta vitest) → CI valida 4 jobs →
> merge cuando todo verde.

---

## 🔄 Ciclo típico

```
1. 📥 git pull
        │
        ▼
2. ✏️  Tocar código (con asistente IA si conviene)
        │
        ▼
3. ✅  Ejecutar suite local:
        ├─ npm run quality
        └─ pytest -m "not integration"
        │
        ▼
4. 💾  git commit         ┌── 🪝 Husky pre-commit (~10s)
                          │   lint + typecheck
                          └── (aborta si falla)
        │
        ▼
5. 📤  git push           ┌── 🪝 Husky pre-push (~3s)
                          │   vitest run
                          └── (aborta si falla)
        │
        ▼
6. ⚙️  CI verifica       ┌── backend (pytest)
                          ├── frontend (typecheck + lint + Vitest cov)
                          ├── e2e (Playwright)
                          └── security-audit (pip-audit + npm audit + gitleaks)
        │
        ▼
7. ✅  Mergear cuando los 4 jobs estén verdes
```

---

## 🪝 Husky — gates locales

Configurado en `.husky/`. Se activa con `npm install` en la raíz del
repo (`prepare: "husky"` en el `package.json` root).

### 🟢 Pre-commit (~10s)

```sh
cd buenchollo-web
npm run lint
npm run typecheck
```

> 🚨 Si falla, el commit se aborta.

### 🟡 Pre-push (~3s)

```sh
cd buenchollo-web
npm run test:run    # 72 tests Vitest unit + integration
```

> 🚨 Si falla, el push se aborta.

### 🚨 Bypass legítimo

```bash
git commit --no-verify -m "fix(prod): rollback urgente"
git push --no-verify
```

> ⚠️ **Sólo en emergencias**. Reglas:
> - 📝 Justificar en el mensaje del commit
> - ❌ Nunca en main directo si hay otros devs
> - ✅ El siguiente commit debe restaurar el estado verde

---

## 📝 Convención de commits

Estilo **Conventional Commits**:

<table>
<thead>
<tr><th>Prefijo</th><th>Cuándo</th></tr>
</thead>
<tbody>
<tr><td><code>feat:</code></td><td>✨ Nueva funcionalidad</td></tr>
<tr><td><code>feat(sec):</code></td><td>🛡️ Funcionalidad de seguridad</td></tr>
<tr><td><code>feat(web):</code></td><td>⚛️ Cambios visibles del frontend</td></tr>
<tr><td><code>fix:</code></td><td>🐛 Bug fix</td></tr>
<tr><td><code>fix(sec):</code></td><td>🛡️ Fix de seguridad (referenciado a SECURITY_AUDIT)</td></tr>
<tr><td><code>fix(ci):</code></td><td>⚙️ Arreglo del pipeline</td></tr>
<tr><td><code>chore:</code></td><td>🧹 Mantenimiento (deps, configs, archivado)</td></tr>
<tr><td><code>chore(deps):</code></td><td>📦 Actualización de dependencias</td></tr>
<tr><td><code>ci:</code></td><td>⚙️ Cambios en <code>.github/workflows/</code></td></tr>
<tr><td><code>docs:</code></td><td>📚 Sólo documentación</td></tr>
<tr><td><code>refactor:</code></td><td>🔄 Reorganizar sin cambiar comportamiento</td></tr>
<tr><td><code>test:</code></td><td>🧪 Tests nuevos o cambios en suite</td></tr>
<tr><td><code>ux:</code></td><td>🎨 Mejoras de UX sin cambio lógico</td></tr>
<tr><td><code>debug:</code></td><td>🔍 Cambios temporales para diagnosticar</td></tr>
</tbody>
</table>

> 💡 **Cuerpo del commit**: el _por qué_, no el _qué_. El `git log` ya
> muestra el "qué".

---

## 🌿 Ramas

```
main  ← única rama estable. CI verde permanente.
       │
       └─ Para cambios grandes (sprints F1-F7, Q1-Q7, S1-S7):
          commits pequeños directos a main, cada uno verificado en
          local antes del push.
```

> 💡 No hay PR workflow estricto porque el proyecto tiene un único
> mantenedor. Si entrara un segundo dev, pasaríamos a feature
> branches + PR review.

---

## 🏷️ Tag de release

```bash
git tag -a v1.0.0-tfm -m "Versión presentada como Trabajo Final de Máster"
git push origin v1.0.0-tfm
```

Convención: **SemVer** + sufijo descriptivo cuando aplique.

---

## 🤖 Uso de IA en el desarrollo

> Esta sección documenta **cómo** se usa la IA en el día a día.
> El **por qué** y la justificación académica viven en:
>
> - [`docs/master/08-uso-de-ia-en-el-desarrollo.md`](../master/08-uso-de-ia-en-el-desarrollo.md)
> - [ADR-009](../adr/ADR-009-uso-de-ia-en-desarrollo.md)

### 🥇 Herramienta principal

**Claude Code** (Anthropic) con [`CLAUDE.md`](../../CLAUDE.md) en la
raíz del repo. El fichero contiene:

- 🎭 Rol que la IA debe asumir (desarrollador senior, arquitecto)
- 🧱 Contexto técnico del proyecto
- 📜 Principios obligatorios (Clean Architecture, SOLID, KISS, sin sobreingeniería)
- 🛠️ Workflows de auditoría disponibles
- 🛡️ Reglas de seguridad explícitas

### 🎨 Patrones de uso aplicados

#### 🅰️ Auditorías por módulo

```
Prompt extenso → IA inspecciona código → informe priorizado →
plan de acción aprobado → implementación en commits pequeños
```

Aplicado en: calidad, seguridad, arquitectura, documentación.

#### 🅱️ Implementación guiada

```
Descripción funcional → IA propone plan (modo plan) →
revisión humana → implementación commit a commit con tests entre cada paso
```

#### 🅲️ Refactor seguro

```
La IA propone → los tests garantizan que no se rompe nada →
si una refactorización deja un test rojo, se revierte
```

### 📜 Reglas de oro al usar IA

> 🔴 **Nunca commitear código que no se entienda**
> 🔴 **Cada cambio se valida con tests** antes del commit
> 🔴 Si la IA propone **sobreingeniería**, rechazar y simplificar
> 🔴 Si la IA crea tests pasando, revisar que **realmente prueban algo**
> 🔴 No subir prompts ni contexto de IA a logs ni telemetría

### 🚫 Lo que la IA NO sustituye

| Decisión | Por qué |
|---|---|
| 🏗️ Decisiones arquitectónicas | Van a ADR firmados |
| 🛡️ Revisión de seguridad final antes de release | Necesita ojos humanos |
| 🎯 Decidir si una feature merece la pena | Producto sobre tecnología |
| 🧪 Validar que un E2E refleja un flujo real | La IA puede escribir un test que pasa pero no prueba nada |

---

## ✅ Checks antes de subir cambios grandes

Manual rápido para tirar de un sprint:

```bash
# 🐍 Backend
cd buenchollo-api
pytest -q -m "not integration"   # 87 tests, ~1s
pip-audit -r requirements.txt    # 0 CVEs

# ⚛️ Frontend
cd ../buenchollo-web
npm run quality                  # lint + typecheck + 72 vitest
npm run test:e2e                 # 8 playwright (levanta dev server)
npm audit --omit=dev --audit-level=high   # 0 high+

# 📚 Documentos
# Verificar enlaces relativos en docs/ funcionan
```

> ✅ Si los 5 están en verde y el `git log --oneline -5` tiene mensajes
> limpios → **push y verificar CI**.

---

<p align="center">
  <a href="04-configuration.md">← Anterior: Configuración</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="06-testing-and-quality.md">Siguiente: Testing y calidad →</a>
</p>
