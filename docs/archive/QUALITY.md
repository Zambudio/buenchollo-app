# Quality Strategy — BuenCholloTech

> Documento de calidad del software del proyecto. Cubre estrategia de
> testing, coverage estratégico, quality gates, métricas accionables y
> deuda asumida.
>
> *Última actualización: 2026-05-30 (cierre del sprint de Calidad QA).*

---

## 1. Estrategia de testing — pirámide

```
                       ┌─────────────┐
                       │  E2E (8)    │   Playwright + chromium
                       │  ~ 6 s      │   Flujos críticos del usuario
                       └─────────────┘
                ┌──────────────────────────┐
                │   Integration (13)       │   RTL + userEvent
                │   ~ 0,7 s                │   Componentes user-centric
                └──────────────────────────┘
        ┌──────────────────────────────────────────┐
        │  Unit (59 web + 78 backend = 137)        │   Vitest / pytest
        │  ~ 0,1 s                                 │   Lógica pura
        └──────────────────────────────────────────┘
```

Suite total: **158 tests automáticos verdes** (137 unit + 13 integration + 8 E2E).

### Reglas de cada capa

| Nivel | Coste | Función | Lo que NO hace |
|---|---|---|---|
| **Unit** | < 5 ms / test | Funciones puras: cálculos, validaciones, type guards | Tocar DOM real, red, BD |
| **Integration** | < 100 ms / test | Renderizado de componentes con interacción del usuario | Subir el router completo / Backend real |
| **E2E** | < 1 s / test | "La app no está rota": page loads, navegación, guards | Cubrir reglas de negocio (eso es unit/integration) |

### Convenciones de código de tests

- **AAA**: cada test estructurado en *Arrange / Act / Assert*.
- **User-centric** (RTL): preferimos `getByRole`, `getByLabelText`,
  `getByText`. `getByTestId` queda como último recurso.
- **Sin `fireEvent`** salvo casos especiales: `userEvent` simula la
  interacción más fielmente.
- **Mocks justificados**: sólo se mockean fronteras (red, auth, librería
  externa). Si un test necesita más de 3 mocks, probablemente está
  testeando la cosa equivocada.
- **Tests en español**: nombres descriptivos, coherentes con el resto
  del código del proyecto.

---

## 2. Coverage estratégico

No perseguimos 100% global por postureo — esa métrica es ruido. Aplicamos
el principio **100 / 80 / 0**.

| Tier | % objetivo | Qué entra | Estado |
|---|---|---|---|
| **CORE** | 90-100% | Lógica pura del negocio: validaciones, cálculos, transformaciones críticas | ✅ Threshold `vitest.config.ts` |
| **IMPORTANT** | ~80% | Componentes visibles, formularios, flujos de navegación | 🟡 Cubierto parcialmente |
| **INFRASTRUCTURE** | 0% | Tipos, constantes, configs, código generado, primitivos shadcn | ⛔ Excluido |

### CORE — código que si falla rompe el negocio

| Archivo | Tier | Coverage real |
|---|---|---|
| [`src/lib/format.ts`](../../buenchollo-web/src/lib/format.ts) | CORE | 96.07% |
| [`src/lib/errors.ts`](../../buenchollo-web/src/lib/errors.ts) | CORE | 100% |
| [`src/lib/validation/deals.ts`](../../buenchollo-web/src/lib/validation/deals.ts) | CORE | 100% |
| [`src/lib/validation/alerts.ts`](../../buenchollo-web/src/lib/validation/alerts.ts) | CORE | 100% |
| [`src/lib/utils.ts`](../../buenchollo-web/src/lib/utils.ts) | CORE | 100% |
| [`src/lib/constants.ts`](../../buenchollo-web/src/lib/constants.ts) | CORE | 100% |
| [`src/services/api/deals.ts`](../../buenchollo-web/src/services/api/deals.ts) → `isDuplicateDealError` | CORE | ✅ tipado guard |

Threshold automático en `vitest.config.ts`:

```ts
thresholds: {
  "src/lib/**": { lines: 90, functions: 90, branches: 80, statements: 90 },
}
```

Si baja, CI falla.

### IMPORTANT — visible al usuario

Cubiertos con integration tests:

- `DealCard` (7 tests): título, precio, descuento, badge caducado, favorito.
- `Header` (6 tests): CTA acceder/perfil, badge unread, dropdown admin.

### INFRASTRUCTURE — excluido del cómputo

- `src/components/ui/**` (shadcn primitives, ya testados upstream)
- `src/routeTree.gen.ts` (generado por TanStack Router)
- `src/integrations/supabase/types.ts` (generado por Supabase CLI)
- `src/lib/query-client.ts` (config sin lógica)
- Todos los `*.config.*`

---

## 3. Quality gates

### Pre-commit (Husky)

Configurado en [`.husky/pre-commit`](../../.husky/pre-commit). Tarda ~10 s.

```sh
cd buenchollo-web
npm run lint        # ESLint estricto (no-explicit-any, exhaustive-deps)
npm run typecheck   # tsc --noEmit con strict + noUncheckedIndexedAccess
```

Si falla, el commit se aborta.

### Pre-push (Husky)

Configurado en [`.husky/pre-push`](../../.husky/pre-push). Tarda ~3 s.

```sh
cd buenchollo-web
npm run test:run    # Vitest run (72 unit + integration)
```

Los E2E NO entran como gate local — son responsabilidad de CI por dos
razones: tardan ~10 s (no infinito, pero suma fricción al push); y
dependen del build de Vite, que puede pifiar por entorno.

### Bypass legítimo

Sólo en emergencia y con justificación en el mensaje del commit:

```sh
git commit --no-verify -m "fix(prod): rollback parche urgente — bypass gate"
git push --no-verify
```

Reglas:
- Nunca en main directo si la rama está abierta a otros desarrolladores.
- El siguiente commit debe restaurar el estado verde.

### CI (GitHub Actions)

Workflow [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml). 4 jobs
en cada `push` a `main` y cada `pull_request`:

| Job | Qué corre | Artifact |
|---|---|---|
| `backend` | pytest -m "not integration" (78 tests) | — |
| `frontend` | typecheck + lint + Vitest con coverage (72 tests) | `coverage/` siempre |
| `e2e` | Playwright chromium (8 tests) | `playwright-report/` en fallo |

Si cualquier job falla, el commit aparece rojo y no se debe mergear.

---

## 4. Métricas accionables

No perseguimos métricas de vanidad (líneas de código, número de commits,
coverage global sin contexto). Estas son las que monitorizamos.

### Tier 1 — revisión frecuente (cada PR / cada día)

| Métrica | Cómo se mide | 🟢 Verde | 🟡 Amarillo | 🔴 Rojo | Acción si rojo |
|---|---|---|---|---|---|
| Test Success Rate | tests verdes / tests totales en CI | 100% | 95-99% | < 95% | Bloquear merge, investigar |
| Build Success Rate | builds verdes en main / total semanal | 100% | 90-99% | < 90% | Hotfix prioritario |
| Lint errors | `eslint .` exit code | 0 errores | 0 errores | ≥ 1 error | Pre-commit bloquea |
| E2E pasando | playwright report | 8/8 | 7/8 | < 7/8 | Revertir cambio sospechoso |

### Tier 2 — revisión por hito (release / milestone)

| Métrica | Cómo se mide | 🟢 | 🟡 | 🔴 |
|---|---|---|---|---|
| Duración test:run | suite Vitest completa | < 5 s | 5-15 s | > 15 s |
| Duración CI completa | de checkout a deploy | < 5 min | 5-10 min | > 10 min |
| MTTR fallo CI | tiempo medio rojo→verde en main | < 4 h | 4-24 h | > 24 h |

### Tier 3 — revisión periódica (mensual / pre-release)

| Métrica | Cómo se mide | 🟢 | 🟡 | 🔴 |
|---|---|---|---|---|
| CORE coverage | threshold en `vitest.config.ts` | ≥ 90% | 80-89% | < 80% |
| TODO / FIXME en `src/` | `grep -rEn "TODO\|FIXME\|HACK\|XXX" src/` | ≤ 5 | 6-15 | > 15 |
| Smells críticos | ESLint + SonarLint IDE | 0 | 1-3 | > 3 |
| Dependencias desactualizadas | Dependabot weekly | 0 major pendientes | 1-3 | > 3 |

---

## 5. Performance budget

Documentado, no automatizado todavía. Vite + lazy routing por defecto
nos da margen para alcanzarlo.

| Métrica | Objetivo | Cómo medir |
|---|---|---|
| LCP (Largest Contentful Paint) | < 2.5 s en 3G fast | Lighthouse / Chrome DevTools |
| CLS (Cumulative Layout Shift) | < 0.1 | Lighthouse |
| INP (Interaction to Next Paint) | < 200 ms | Lighthouse |
| Bundle inicial gzip | < 250 KB | `npm run build` + `vite-bundle-visualizer` |
| Imágenes principales | WebP, dimensiones reservadas | inspección manual / SMOKE_TEST |

Si la métrica empeora más del 10% entre releases, se documenta como
deuda y se aborda en el siguiente sprint.

---

## 6. Deuda técnica asumida

Decisiones explícitas de NO hacer ahora. Justificadas.

| Item | Por qué se asume | Coste futuro |
|---|---|---|
| Visual regression con `toHaveScreenshot` | Añade brittleness (cambios CSS rompen tests sin defecto real) en una UI que aún itera. | Bajo — se puede añadir más adelante con `playwright update-snapshots`. |
| Page Object Model elaborado | Con 8 E2E, helpers ad-hoc en cada spec son más legibles. | Bajo — refactor cuando lleguemos a 20+ E2E. |
| MSW para mocks API | Playwright route + Vitest mocks bastan. Añadir MSW duplicaría capas. | Bajo. |
| Test E2E del flujo admin completo | Requiere mockear OAuth de Google: complejidad alta para escaso retorno. El admin se cubre con integration tests + smoke manual. | Medio — añadir cuando tengamos staging real. |
| Lighthouse-CI automatizado | Performance budget documentado arriba; ejecutamos manualmente en hitos. | Bajo. |
| Refactor de `admin.chollos.tsx` (940 líneas) | God Component conocido. Partir conlleva alto riesgo de regresión en una zona crítica. Documentado en `PROJECT_STATUS.md §3.bis F-03`. | Medio — mejora futura. |
| Tests E2E para `admin.chollos.tsx` (dialog duplicado, autocompletar Amazon) | Dependen de respuestas del backend (Amazon Creators API) que no se mockean limpiamente desde Playwright SSR. Cubierto manualmente en `docs/SMOKE_TEST.md`. | Bajo. |

---

## 7. Comandos útiles

```bash
# Ciclo rápido (en buenchollo-web/)
npm run test               # watch mode — desarrollo
npm run test:run           # one-shot
npm run test:coverage      # one-shot + reporte HTML en coverage/

# Gates manuales
npm run quality            # lint + typecheck + test:run (lo que verifica Husky)
npm run quality:full       # quality + test:e2e

# E2E
npm run test:e2e           # corre los 8 specs
npm run test:e2e:ui        # modo UI interactivo (debug)
npx playwright show-report # abre el último HTML report

# Backend
cd ../buenchollo-api && pytest -q -m "not integration"   # unit
cd ../buenchollo-api && pytest -q                        # todos (incluye integración con BD real)
```

---

*Mantenedor: Pedro Zambudio — pjzambudio@gmail.com*
