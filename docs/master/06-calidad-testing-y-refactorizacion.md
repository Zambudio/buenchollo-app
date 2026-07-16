# 🧪 06 · Calidad, testing y refactorización

> **TL;DR** · Pirámide de testing clásica (más unit, menos E2E) con
> **224 tests verdes en menos de un minuto**. Coverage estratégico **100/80/0**
> en lugar de perseguir 100% global. Quality gates en **3 niveles**
> (pre-commit, pre-push, CI).

---

## 🧠 Filosofía de fondo

> _Los tests son la red de seguridad que permite refactorizar sin miedo._
>
> _Si los tests son rígidos o frágiles, dejas de refactorizar. Si son
> útiles, refactorizas todo el tiempo._

---

## 🔺 Pirámide de testing

```
                    ┌─────────────────────┐
                    │  🎭 E2E  (8 tests)  │   Playwright + chromium · ~6s
                    └─────────────────────┘
              ┌────────────────────────────────┐
              │  🔗 Integración backend (9)    │   pytest -m integration · Postgres real (local)
              └────────────────────────────────┘
       ┌──────────────────────────────────────────────┐
       │  ⚛️ Unit + RTL (207 = 116 pytest + 91 vitest) │   corren en CI en cada push
       └──────────────────────────────────────────────┘
```

📊 **Total**: **224 tests automatizados** (verificado 2026-07-16, pytest bajo Python 3.11).

### 🎯 Por qué esta proporción

| Capa | Coste por test | Valor que aporta |
|---|---|---|
| ⚛️ **Unit** | < 5 ms | Lógica pura. Si esta capa es robusta, el resto se simplifica. |
| 🔗 **Integration** | < 100 ms | Comportamiento user-centric con mocks sólo en fronteras. |
| 🎭 **E2E** | < 1 s | Sólo flujos críticos: la app responde, el guard de admin funciona. **No reglas de negocio**. |

> 💡 Un E2E que prueba "click en favorito guarda en BD" es un **fallo
> de pirámide**: lo correcto es unit del guard + integration del click
> con mock + E2E que sólo verifique que la app no está rota.

---

## 🎯 Coverage estratégico — `100/80/0`

> **No** se persigue 100% global. Esa es métrica de vanidad.

<table>
<thead>
<tr><th>Tier</th><th>% objetivo</th><th>Qué entra</th><th>Estado</th></tr>
</thead>
<tbody>
<tr>
  <td>🔴 <strong>CORE</strong></td>
  <td>90–100%</td>
  <td>Lógica pura: validaciones, cálculos, type guards, transformaciones críticas (<code>src/lib/**</code>)</td>
  <td>✅ Threshold automático</td>
</tr>
<tr>
  <td>🟡 <strong>IMPORTANT</strong></td>
  <td>~80%</td>
  <td>Componentes visibles, formularios, flujos de navegación</td>
  <td>🟡 Cubierto parcialmente con integration tests</td>
</tr>
<tr>
  <td>⚫ <strong>INFRASTRUCTURE</strong></td>
  <td>0%</td>
  <td>Tipos, constantes, configs, código generado, primitivos shadcn</td>
  <td>⛔ Excluido del cómputo</td>
</tr>
</tbody>
</table>

### 🔴 CORE — código que si falla, rompe el negocio

| Archivo | Coverage |
|---|---|
| `src/lib/errors.ts` | **100%** |
| `src/lib/format.ts` | 96.07% |
| `src/lib/validation/deals.ts` | **100%** |
| `src/lib/validation/alerts.ts` | **100%** |
| `src/lib/utils.ts` | **100%** |
| `src/lib/constants.ts` | **100%** |

#### Threshold automático en `vitest.config.ts`

```ts
thresholds: {
  "src/lib/**": { lines: 90, functions: 90, branches: 80, statements: 90 },
}
```

> 🚨 Si baja, CI rompe.

### 🟡 IMPORTANT — visible al usuario

Cubierto con integration tests:

- **`DealCard`** (7 tests): título, precio, descuento, badge caducado, favorito
- **`Header`** (6 tests): CTA acceder/perfil, badge unread, dropdown admin

### ⚫ INFRASTRUCTURE — excluido

```
src/components/ui/**                  (shadcn upstream)
src/routeTree.gen.ts                  (TanStack auto-generated)
src/integrations/supabase/types.ts    (Supabase CLI generated)
src/lib/query-client.ts               (config sin lógica)
**/*.config.*
```

### 💡 Por qué NO 100% global

> Subir coverage cubriendo `routeTree.gen.ts` o primitivos shadcn
> **no mejora la calidad real**. Es métrica de vanidad.
>
> La métrica útil es **coverage del código que puede romper el negocio**.

---

## 🚪 Quality gates

```
                              git commit                              git push
                                  │                                      │
                                  ▼                                      ▼
                          ┌───────────────┐                      ┌───────────────┐
                          │ 🪝 Pre-commit │                      │ 🪝 Pre-push   │
                          │   (Husky)     │                      │   (Husky)     │
                          │   ~10s        │                      │   ~3s         │
                          │   lint + tsc  │                      │   vitest run  │
                          └───────────────┘                      └───────────────┘
                                                                          │
                                                                          ▼
                                                                  ┌───────────────┐
                                                                  │ ⚙️ CI (GitHub)│
                                                                  │   4 jobs:     │
                                                                  │   - backend   │
                                                                  │   - frontend  │
                                                                  │   - e2e       │
                                                                  │   - security  │
                                                                  └───────────────┘
```

### 🪝 Pre-commit (Husky, ~10s)

```bash
npm run lint        # ESLint estricto
npm run typecheck   # tsc --noEmit (strict + noUncheckedIndexedAccess)
```

> 🚨 Si falla, el commit se aborta.

### 🪝 Pre-push (Husky, ~3s)

```bash
npm run test:run    # Vitest run (72 unit + integration)
```

> 🚨 Si falla, el push se aborta. Los E2E **no** entran como gate
> local (tardan ~10s y dependen del build).

### 🚨 Bypass legítimo `--no-verify`

> ⚠️ **Sólo en emergencia** con justificación en el mensaje del commit:

```bash
git commit --no-verify -m "fix(prod): rollback urgente — bypass gate"
git push --no-verify
```

📜 **Reglas**:

- ❌ Nunca en `main` con otros desarrolladores activos
- ✅ El siguiente commit debe restaurar el estado verde

### ⚙️ CI — `.github/workflows/ci.yml`

4 jobs en cada `push` a `main` y cada `pull_request`:

| Job | Comprueba | Artifact |
|---|---|---|
| 🐍 `backend` | `pytest -m "not integration"` (78 unit) | — |
| ⚛️ `frontend` | typecheck + ESLint + Vitest con coverage threshold | `coverage/` siempre |
| 🎭 `e2e` | Playwright chromium con webServer | HTML report + traces en fallo |
| 🛡️ `security-audit` | `pip-audit`, `npm audit --omit=dev`, `gitleaks` | — |

> 🚨 Si **cualquier job** falla, el commit aparece rojo y no se mergea.

---

## 📊 Métricas accionables

### 🟢 Tier 1 — revisión frecuente (cada PR / cada día)

| Métrica | 🟢 Verde | 🟡 Amarillo | 🔴 Rojo | Acción si rojo |
|---|---|---|---|---|
| Test Success Rate | 100% | 95–99% | < 95% | Bloquear merge, investigar |
| Build SR (main, semanal) | 100% | 90–99% | < 90% | Hotfix prioritario |
| Lint errors | 0 | 0 | ≥ 1 | Pre-commit bloquea |
| E2E pasando | 8/8 | 7/8 | < 7/8 | Revertir cambio sospechoso |

### 🟡 Tier 2 — revisión por hito (release / milestone)

| Métrica | 🟢 | 🟡 | 🔴 |
|---|---|---|---|
| Duración `test:run` | < 5s | 5–15s | > 15s |
| Duración CI completa | < 5 min | 5–10 min | > 10 min |
| MTTR fallo CI en main | < 4h | 4–24h | > 24h |

### 🔵 Tier 3 — revisión periódica (mensual / pre-release)

| Métrica | 🟢 | 🟡 | 🔴 |
|---|---|---|---|
| CORE coverage | ≥ 90% | 80–89% | < 80% |
| TODO/FIXME en `src/` | ≤ 5 | 6–15 | > 15 |
| Smells críticos ESLint + SonarLint | 0 | 1–3 | > 3 |
| Deps desactualizadas (Dependabot) | 0 major | 1–3 | > 3 |

### ❌ Métricas que NO se persiguen

> _Estas son métricas de vanidad. No las medimos._

- Líneas de código
- Número de commits
- Coverage global sin contexto
- Número de features

---

## 🛡️ Refactor seguro

La estrategia de testing **permite refactorizar con confianza**. Cada
sprint del proyecto incluyó refactors sin dejar tests rojos en `main`:

| Refactor | Qué se mejoró |
|---|---|
| **F-03** (frontend) | Split de hooks gigantes en `features/<dominio>/hooks/` con TanStack Query |
| **B-02** (backend) | Extraer `DealService` del router, con `AlertMatcher` por DI |
| **B-03** | Helper `_base_deal_query()` centralizando `selectinload` repetido |
| **B-04** | `matches_alert()` extraído del repositorio a función pura testeable |
| **B-05** | `_safe_run()` para el cleaner, eliminando triple try/except idéntico |

### 🔄 Proceso aplicado en cada refactor

```
1. ✅ Verificar que los tests cubren el comportamiento actual
       │
       └─ ❌ Si no, AÑADIR TESTS antes del refactor
       │
       ▼
2. 🛠️ Refactorizar
       │
       ▼
3. ✅ Tests siguen verdes → commit
```

---

## 🚨 Code smells detectados y resueltos

<table>
<thead>
<tr><th>Smell</th><th>Dónde estaba</th><th>Resolución</th></tr>
</thead>
<tbody>
<tr>
  <td>📏 <strong>Long Method</strong></td>
  <td><code>DealService.create_deal()</code> con 40+ líneas mezclando slug, FK check, AlertMatcher</td>
  <td>Extraído a <code>_check_external_id_unique</code> + helpers</td>
</tr>
<tr>
  <td>🔁 <strong>Duplicate Code</strong></td>
  <td><code>selectinload(category, subcategory, store)</code> en 6 queries</td>
  <td><code>_base_deal_query()</code> centraliza</td>
</tr>
<tr>
  <td>🔢 <strong>Magic Numbers</strong></td>
  <td><code>200</code>, <code>100</code> thresholds temperatura · <code>30</code>, <code>5</code> rate limits</td>
  <td>Constantes con nombre</td>
</tr>
<tr>
  <td>📦 <strong>Primitive Obsession</strong></td>
  <td>Strings para status de chollos</td>
  <td><code>DealStatus</code> literal type + <code>DEAL_STATUS_OPTIONS as const</code></td>
</tr>
<tr>
  <td>📋 <strong>Long Parameter List</strong></td>
  <td><code>search()</code> con 5+ params</td>
  <td>Object pattern <code>{category_id, store_id, search, limit, offset}</code></td>
</tr>
<tr>
  <td>🔓 <strong>Inappropriate Intimacy</strong></td>
  <td>Frontend consultando Supabase directamente</td>
  <td>ADR-002: ningún <code>supabase.from()</code> en frontend</td>
</tr>
</tbody>
</table>

---

## 📋 Deuda asumida (con justificación)

| Item | Por qué se asume |
|---|---|
| 📷 **Visual regression** (`toHaveScreenshot`) | Brittleness sin valor — cambios CSS sin defecto rompen tests |
| 🎭 **Page Object Model elaborado** | Con 8 E2E, helpers ad-hoc son más legibles |
| 🎯 **MSW (Mock Service Worker)** | `page.route` + Vitest mocks bastan; MSW tendría sentido con docenas de tests |
| 🛠️ **Tests E2E del admin completos** | OAuth Google requiere mocks complejos; cubierto con integration + smoke manual |
| 🧪 **Tests integración en CI** | Requiere Postgres real; Supabase no levantable en CI |
| 🪨 **Refactor `admin.chollos.tsx`** (940 líneas) | God Component conocido; partir tiene alto riesgo |
| 🔍 **SonarJS / SonarQube** | ESLint estricto + TS strict ya cubren lo que detectaría |

---

## 🎯 Performance budget

| Métrica | Objetivo | Cómo se mide |
|---|---|---|
| 🚀 **LCP** (Largest Contentful Paint) | < 2.5s en 3G fast | Lighthouse manualmente en cada release |
| 📐 **CLS** (Cumulative Layout Shift) | < 0.1 | Lighthouse |
| 🖱️ **INP** (Interaction to Next Paint) | < 200ms | Lighthouse |
| 📦 **Bundle inicial gzip** | < 250 KB | `npm run build` + visualizer |

> 🔭 **Lighthouse-CI automatizado** aplazado como mejora futura
> (ver [`09 · Limitaciones y mejoras futuras`](09-limitaciones-y-mejoras-futuras.md)).

---

<p align="center">
  <a href="05-buenas-practicas-y-principios-de-diseno.md">← Anterior: Buenas prácticas</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="07-seguridad.md">Siguiente: Seguridad →</a>
</p>
