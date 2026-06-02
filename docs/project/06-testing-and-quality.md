# 06 — Testing y calidad

> Vista operativa: comandos, scripts, gates. La estrategia y defensa
> académica viven en [`docs/master/06-calidad-testing-y-refactorizacion.md`](../master/06-calidad-testing-y-refactorizacion.md).

## Suite total

| Capa | Cantidad | Stack | Duración |
|---|---|---|---|
| Backend unit | 78 | pytest + AsyncMock | ~1 s |
| Backend integración | 9 | pytest + Postgres real (Supabase) | ~5 s (local) |
| Frontend unit | 59 | Vitest + jsdom | ~0,5 s |
| Frontend integration | 13 | Vitest + Testing Library + userEvent | ~0,7 s |
| E2E | 8 | Playwright + chromium | ~6 s |
| **Total automatizado** | **167** | | **~13 s** |

## Comandos

### Backend (`buenchollo-api/`)

```bash
pytest                              # toda la suite (necesita .env con DB real para integración)
pytest -q -m "not integration"      # 87 unitarios, rápido, sin BD
pytest app/tests/test_deal_service.py -v   # un fichero concreto
pytest -k "duplicate"               # tests cuyo nombre incluye "duplicate"
```

### Frontend (`buenchollo-web/`)

```bash
npm run test                        # vitest watch (desarrollo)
npm run test:run                    # 72 tests one-shot
npm run test:coverage               # + reporte HTML en coverage/
npm run test:e2e                    # 8 playwright (levanta dev server)
npm run test:e2e:ui                 # modo UI interactivo (debug)
npx playwright show-report          # último HTML report
```

### Gates compuestos

```bash
npm run quality                     # lint + typecheck + test:run (lo que valida pre-commit/pre-push)
npm run quality:full                # quality + test:e2e (gate completo)
```

## Coverage estratégico — 100/80/0

| Tier | % objetivo | Qué entra |
|---|---|---|
| **CORE** | 90–100% | Lógica pura del negocio: validaciones, cálculos, type guards, transformaciones críticas |
| **IMPORTANT** | ~80% | Componentes visibles, formularios, flujos de navegación |
| **INFRASTRUCTURE** | 0% | Tipos, constantes, configs, código generado, primitivos shadcn |

### CORE — threshold automático

En `vitest.config.ts`:

```ts
thresholds: {
  "src/lib/**": { lines: 90, functions: 90, branches: 80, statements: 90 },
}
```

Estado real por archivo:

| Archivo | Coverage |
|---|---|
| `src/lib/errors.ts` | 100% |
| `src/lib/format.ts` | 96.07% |
| `src/lib/validation/deals.ts` | 100% |
| `src/lib/validation/alerts.ts` | 100% |
| `src/lib/utils.ts` | 100% |
| `src/lib/constants.ts` | 100% |

### INFRASTRUCTURE — excluido del cómputo

`vitest.config.ts → coverage.exclude`:

- `src/routeTree.gen.ts` (generado por TanStack Router)
- `src/router.tsx`
- `src/integrations/supabase/types.ts` (generado por Supabase CLI)
- `src/components/ui/**` (shadcn primitives)
- `src/lib/query-client.ts` (config sin lógica)
- `**/*.config.*`, `vitest.setup.ts`

## Convenciones de tests

### AAA — Arrange, Act, Assert

```ts
it("rechaza title con menos de 3 caracteres", () => {
  const result = dealFormSchema.safeParse({ ...valido, title: "ab" });
  expect(result.success).toBe(false);
  if (!result.success) {
    expect(result.error.issues[0]?.message).toBe("Mínimo 3 caracteres");
  }
});
```

### User-centric (Testing Library)

Prioridad de queries:

1. `getByRole` — primer recurso.
2. `getByLabelText` — formularios.
3. `getByText` — contenido visible.
4. `getByTestId` — último recurso, sólo cuando los anteriores no llegan.

### userEvent en vez de fireEvent

```ts
const user = userEvent.setup();
await user.click(screen.getByRole("button", { name: /guardar/i }));
```

### Mocks con `vi.hoisted`

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

### Tests de integración del backend

Marcados con `pytestmark = pytest.mark.integration` a nivel de módulo.
Excluidos del CI (`pytest -m "not integration"`) porque requieren
PostgreSQL real. Se ejecutan en local antes de cada release y vía
[`docs/reference/SMOKE_TEST.md`](../reference/SMOKE_TEST.md).

## Quality gates

### Pre-commit (Husky, ~10 s)

```sh
npm run lint && npm run typecheck
```

### Pre-push (Husky, ~3 s)

```sh
npm run test:run
```

### CI — `.github/workflows/ci.yml`

4 jobs en cada push y PR a `main`:

| Job | Comprueba |
|---|---|
| `backend` | `pytest -m "not integration"` (78 unit) |
| `frontend` | typecheck + ESLint + Vitest con coverage threshold + sube `coverage/` como artifact |
| `e2e` | Playwright chromium con webServer; sube HTML report en fallo |
| `security-audit` | `pip-audit --strict`, `npm audit --omit=dev --audit-level=high`, gitleaks |

Si cualquier job falla, el commit aparece rojo y no se debe mergear.

## Métricas accionables

Tres tiers documentados con umbrales verde/amarillo/rojo:

| Tier | Frecuencia | Métricas |
|---|---|---|
| T1 | Cada PR / cada día | Test Success Rate, Build SR, Lint errors, E2E pasando |
| T2 | Por hito / release | Duración suite, Duración CI, MTTR fallo CI |
| T3 | Mensual / pre-release | CORE coverage, TODO/FIXME en `src/`, smells críticos, deps desactualizadas |

Detalle completo con umbrales numéricos en
[`docs/master/06-calidad-testing-y-refactorizacion.md`](../master/06-calidad-testing-y-refactorizacion.md).

## Deuda asumida (documentada)

| Item | Por qué se asume |
|---|---|
| Visual regression (`toHaveScreenshot`) | Brittleness sin valor en una UI que aún itera |
| Page Object Model elaborado | Con 8 E2E, helpers ad-hoc son más legibles |
| Tests E2E completos del admin | OAuth de Google requiere mocks complejos; el admin se cubre con integration tests + smoke manual |
| Tests integración en CI | Requiere Postgres real; en CI no levantamos BD (Supabase es opaco) |
| Refactor `admin.chollos.tsx` (940 líneas) | God Component conocido; partir tiene alto riesgo |
