# 🧪 06 · Testing y calidad

> **TL;DR** · **208 tests automatizados** verdes en menos de un minuto.
> Pirámide unit/integration/E2E. Coverage estratégico 100/80/0 con
> threshold automático en `src/lib/**`. Gates en 3 niveles
> (pre-commit, pre-push, CI).
>
> 🎓 La estrategia académica y justificación viven en
> [`docs/master/06-…`](../master/06-calidad-testing-y-refactorizacion.md).

---

## 📊 Suite total

```
                    ┌──────────────────────┐
                    │  🎭 E2E (8)          │   Playwright + chromium
                    └──────────────────────┘
              ┌──────────────────────────────────┐
              │  🔗 Integración backend (9)      │   pytest -m integration · Postgres real (local)
              └──────────────────────────────────┘
       ┌────────────────────────────────────────────────┐
       │  ⚛️ Unit + RTL (191 = 100 pytest + 91 vitest)   │   corren en CI en cada push
       └────────────────────────────────────────────────┘

  Total: 208 tests (verificado 2026-07-16 · pytest bajo Python 3.11)
```

---

## 🚀 Comandos

### 🐍 Backend (`buenchollo-api/`)

```bash
pytest                              # toda la suite (necesita Postgres real para integración)
pytest -q -m "not integration"      # 87 unitarios, rápido, sin BD
pytest app/tests/test_deal_service.py -v   # un fichero concreto
pytest -k "duplicate"               # tests cuyo nombre incluye "duplicate"
```

### ⚛️ Frontend (`buenchollo-web/`)

```bash
npm run test                        # vitest watch (desarrollo)
npm run test:run                    # 72 tests one-shot
npm run test:coverage               # + reporte HTML en coverage/
npm run test:e2e                    # 8 playwright (levanta dev server)
npm run test:e2e:ui                 # modo UI interactivo
npx playwright show-report          # último HTML report
```

### 🎯 Gates compuestos

```bash
npm run quality                     # lint + typecheck + test:run (pre-commit/pre-push)
npm run quality:full                # + test:e2e (gate completo)
```

---

## 🎯 Coverage estratégico — `100/80/0`

<table>
<thead>
<tr><th>Tier</th><th>% objetivo</th><th>Qué entra</th></tr>
</thead>
<tbody>
<tr>
  <td>🔴 <strong>CORE</strong></td>
  <td>90–100%</td>
  <td>Funciones puras: validaciones, cálculos, type guards, transformaciones críticas</td>
</tr>
<tr>
  <td>🟡 <strong>IMPORTANT</strong></td>
  <td>~80%</td>
  <td>Componentes visibles, formularios, flujos de navegación</td>
</tr>
<tr>
  <td>⚫ <strong>INFRASTRUCTURE</strong></td>
  <td>0%</td>
  <td>Tipos, constantes, configs, código generado, primitivos shadcn</td>
</tr>
</tbody>
</table>

### 🔴 CORE — threshold automático

En `vitest.config.ts`:

```ts
thresholds: {
  "src/lib/**": { lines: 90, functions: 90, branches: 80, statements: 90 },
}
```

> 🚨 Si baja, CI rompe.

#### Estado real por archivo

| Archivo | Coverage |
|---|---|
| `src/lib/errors.ts` | **100%** |
| `src/lib/format.ts` | 96.07% |
| `src/lib/validation/deals.ts` | **100%** |
| `src/lib/validation/alerts.ts` | **100%** |
| `src/lib/utils.ts` | **100%** |
| `src/lib/constants.ts` | **100%** |

### ⚫ INFRASTRUCTURE — excluido

`vitest.config.ts → coverage.exclude`:

```
src/routeTree.gen.ts                   (TanStack auto-generated)
src/router.tsx
src/integrations/supabase/types.ts     (Supabase CLI generated)
src/components/ui/**                   (shadcn primitives)
src/lib/query-client.ts                (config sin lógica)
**/*.config.*
vitest.setup.ts
```

---

## 📝 Convenciones de tests

### 🅰️🅰️🅰️ AAA — Arrange, Act, Assert

```ts
it("rechaza title con menos de 3 caracteres", () => {
  // Arrange
  const input = { ...valido, title: "ab" };

  // Act
  const result = dealFormSchema.safeParse(input);

  // Assert
  expect(result.success).toBe(false);
  if (!result.success) {
    expect(result.error.issues[0]?.message).toBe("Mínimo 3 caracteres");
  }
});
```

### 👤 User-centric (Testing Library)

> 💡 Prioridad de queries:

```
1️⃣  getByRole         ← primer recurso
2️⃣  getByLabelText    ← formularios
3️⃣  getByText         ← contenido visible
4️⃣  getByTestId       ← último recurso
```

### 🖱️ userEvent en vez de fireEvent

```ts
const user = userEvent.setup();
await user.click(screen.getByRole("button", { name: /guardar/i }));
```

### 🪝 Mocks con `vi.hoisted`

Para que `vi.mock(...)` (que se hoistea al top del módulo) pueda
referenciar variables:

```ts
const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  toast: { error: vi.fn() },
}));

vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));
vi.mock("sonner", () => ({ toast: mocks.toast }));
```

### 🐘 Tests de integración del backend

Marcados con `pytestmark = pytest.mark.integration` a nivel de módulo.

> ⚠️ Excluidos del CI (`pytest -m "not integration"`) porque requieren
> **PostgreSQL real**. Se ejecutan en local antes de cada release y
> vía [`docs/reference/SMOKE_TEST.md`](../reference/SMOKE_TEST.md).

---

## 🚪 Quality gates

```
                 git commit                              git push
                     │                                      │
                     ▼                                      ▼
             ┌───────────────┐                      ┌───────────────┐
             │ 🪝 Pre-commit │                      │ 🪝 Pre-push   │
             │  (Husky)      │                      │  (Husky)      │
             │  ~10s         │                      │  ~3s          │
             │  lint + tsc   │                      │  vitest run   │
             └───────────────┘                      └───────────────┘
                                                            │
                                                            ▼
                                                    ┌───────────────┐
                                                    │ ⚙️ CI         │
                                                    │   4 jobs:     │
                                                    │   - backend   │
                                                    │   - frontend  │
                                                    │   - e2e       │
                                                    │   - security  │
                                                    └───────────────┘
```

### 🪝 Pre-commit (Husky, ~10s)

```sh
npm run lint && npm run typecheck
```

### 🪝 Pre-push (Husky, ~3s)

```sh
npm run test:run
```

### 🚨 Bypass legítimo

> Sólo en emergencia con justificación en el mensaje del commit:

```bash
git commit --no-verify -m "fix(prod): rollback urgente — bypass gate"
git push --no-verify
```

### ⚙️ CI — `.github/workflows/ci.yml`

| Job | Comprueba |
|---|---|
| 🐍 `backend` | `pytest -m "not integration"` (78 unit) |
| ⚛️ `frontend` | typecheck + ESLint + Vitest con coverage threshold |
| 🎭 `e2e` | Playwright chromium con webServer |
| 🛡️ `security-audit` | `pip-audit`, `npm audit --omit=dev`, `gitleaks` |

> 🚨 Si **cualquier job** falla, el commit aparece rojo y no se debe mergear.

---

## 📊 Métricas accionables

Tres tiers documentados con umbrales verde/amarillo/rojo:

| Tier | Frecuencia | Métricas |
|---|---|---|
| 🟢 **T1** | Cada PR / día | Test SR, Build SR, Lint errors, E2E pasando |
| 🟡 **T2** | Por hito / release | Duración suite, duración CI, MTTR fallo CI |
| 🔵 **T3** | Mensual / pre-release | CORE coverage, TODO/FIXME en `src/`, smells críticos, deps desactualizadas |

> 📚 Detalle completo con umbrales numéricos en
> [`docs/master/06-…`](../master/06-calidad-testing-y-refactorizacion.md).

---

## 📋 Deuda asumida (documentada)

| Item | Por qué se asume |
|---|---|
| 📷 Visual regression (`toHaveScreenshot`) | Brittleness sin valor en una UI que aún itera |
| 🎭 Page Object Model elaborado | Con 8 E2E, helpers ad-hoc son más legibles |
| 🛠️ Tests E2E completos del admin | OAuth Google requiere mocks complejos |
| 🧪 Tests integración en CI | Requiere Postgres real |
| 🪨 Refactor `admin.chollos.tsx` (940 líneas) | God Component conocido; partir tiene alto riesgo |

---

<p align="center">
  <a href="05-development-workflow.md">← Anterior: Flujo de desarrollo</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="07-security.md">Siguiente: Seguridad →</a>
</p>
