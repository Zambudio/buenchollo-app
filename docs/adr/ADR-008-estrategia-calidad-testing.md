# ADR-008 — Estrategia de calidad y testing 100/80/0

## Estado

**Aceptado** · 2026-06-02 · formaliza decisiones tomadas durante el
sprint Q1–Q7.

## Contexto

El backend disponía de pytest (87 tests verdes en una pirámide
adecuada), pero el frontend no tenía ningún test automatizado: ni
Vitest, ni Playwright, ni Husky, ni coverage. La calidad del frontend
descansaba exclusivamente en ESLint estricto + TypeScript strict.

Faltaba además una respuesta defendible a tres preguntas clásicas del
módulo de Calidad:

1. ¿Qué coverage perseguimos y por qué?
2. ¿Qué quality gates aplicamos y dónde?
3. ¿Qué métricas accionables monitorizamos para detectar regresiones?

## Decisión

Adoptar una estrategia de calidad articulada en cinco puntos:

### 1. Pirámide de testing con proporciones definidas

- **Unit**: 137 tests (78 pytest backend + 59 Vitest frontend). Cubren
  lógica pura. < 5 ms por test.
- **Integration**: 13 tests Vitest + Testing Library + userEvent.
  Cubren componentes user-centric con mocks sólo en fronteras
  (auth, red, sonner). < 100 ms por test.
- **E2E**: 8 tests Playwright + chromium. Sólo flujos críticos
  (shell carga, búsqueda redirige, guard de admin). < 1 s por test.

Total: **167 tests automatizados** que se ejecutan en ~13 segundos
sumando todas las suites.

### 2. Coverage estratégico 100/80/0

| Tier | % objetivo | Qué entra |
|---|---|---|
| **CORE** | 90–100% | Funciones puras del dominio: validaciones, cálculos, type guards, transformaciones críticas (`src/lib/**`). |
| **IMPORTANT** | ~80% | Componentes visibles, formularios, flujos de navegación. |
| **INFRASTRUCTURE** | 0% | Tipos, constantes, configs, código generado, primitivos shadcn. |

Threshold automático en `vitest.config.ts`:

```ts
thresholds: {
  "src/lib/**": { lines: 90, functions: 90, branches: 80, statements: 90 },
}
```

Si baja, CI rompe.

### 3. Quality gates en tres niveles

- **Pre-commit (Husky, ~10s)**: lint + typecheck.
- **Pre-push (Husky, ~3s)**: `npm run test:run` (72 Vitest unit + integration).
- **CI (GitHub Actions)**: 4 jobs en cada push y PR a `main`:
  - `backend` → `pytest -m "not integration"`.
  - `frontend` → typecheck + ESLint + `npm run test:coverage` con artifact.
  - `e2e` → Playwright chromium con webServer; artifact HTML report en fallo.
  - `security-audit` → `pip-audit`, `npm audit --omit=dev`, gitleaks.

### 4. Convenciones de tests user-centric

- Estilo AAA: Arrange · Act · Assert.
- Queries prioritarias en Testing Library: `getByRole` → `getByLabelText` → `getByText` → `getByTestId` (último recurso).
- `userEvent` (no `fireEvent`) para simular interacción realista.
- Mocks justificados sólo en fronteras (auth, red, librería externa).
- Patrón `vi.hoisted()` para evitar el clásico "Cannot access X before initialization" cuando `vi.mock` se hoistea.

### 5. Métricas accionables Tier 1 / Tier 2 / Tier 3

Con umbrales verde/amarillo/rojo y acción prescrita si entran en rojo
(detalle en
[`docs/master/06-calidad-testing-y-refactorizacion.md`](../master/06-calidad-testing-y-refactorizacion.md)
y [`docs/project/06-testing-and-quality.md`](../project/06-testing-and-quality.md)).

## Motivo

### Por qué pirámide y no testing trophy

- La pirámide minimiza coste por feedback: un unit roto se detecta en
  ~5 ms, un E2E roto en ~1 s.
- El **testing trophy** (heavy integration) suele responder a apps
  altamente acopladas. BuenCholloTech tiene `src/lib/` con lógica
  pura aislada que se beneficia más de unit tests baratos.

### Por qué 100/80/0 y no 100% global

- Subir coverage cubriendo `routeTree.gen.ts` o primitivos shadcn
  **no mejora la calidad real**. Es métrica de vanidad.
- El threshold automático sobre `src/lib/**` protege lo que **puede
  romper el negocio** (cálculo de descuentos, validaciones de
  formularios, type guards de errores).
- El 80% de IMPORTANT se cumple en la práctica con los 13 integration
  tests, sin gate automático que obligue a tests inútiles.
- El 0% de INFRASTRUCTURE evita escribir tests sobre constantes (que
  serían tautológicos).

### Por qué Husky + CI (defensa en dos capas)

- Husky **evita que código roto llegue al remoto**. Cuesta 10 s al
  developer pero ahorra builds en rojo en CI.
- CI **evita que código roto llegue a main**. Es la última red de
  seguridad antes del merge.
- La combinación es defensa en profundidad: dos capas independientes
  donde un fallo de una no implica fallo de la otra.

## Alternativas consideradas

### A1: 100% coverage global como objetivo

**Rechazada**. Llevaría a:
- Escribir tests sobre `routeTree.gen.ts` (generado, no tiene lógica).
- Escribir tests sobre primitivos shadcn (ya testados upstream).
- Tests inflacionarios sin valor real ("snapshot del componente").
Coste alto, valor cero.

### A2: Sólo unit tests, sin integration ni E2E

**Rechazada**. La unit-only no cubre que los componentes integren
bien. Un componente con todos sus métodos unitarios verdes puede
estar roto al renderizarse.

### A3: Testing trophy (muchos integration tests)

**Rechazada**. Integration tests son ~20x más lentos que unit. Para
167 tests, la suite pasaría de 13 segundos a 4-5 minutos, lo que
rompería el ciclo de feedback rápido necesario en Husky pre-push.

### A4: Sin quality gates locales, sólo CI

**Rechazada**. Sin Husky, el developer descubre que rompió el build
**después** de pushear, esperando 3 minutos de CI. Con Husky, se entera
en 3 segundos al hacer commit. La fricción se queda en el desarrollo,
no se externaliza al CI.

### A5: SonarQube / SonarCloud

**Rechazada**. ESLint estricto + TS strict + auditorías manuales con
IA cubren lo que SonarJS detectaría. Añadir SonarCloud sería duplicar
herramientas sin valor incremental para un proyecto del tamaño actual.

### A6: Mutation testing con `mutmut` / `cosmic-ray`

**Aplazada** como mejora futura. Tiene valor real pero coste alto de
configuración inicial. Documentado en
`docs/master/09-limitaciones-y-mejoras-futuras.md`.

### A7: Visual regression con `toHaveScreenshot`

**Rechazada para el MVP**. Brittleness alta (cambios CSS sin defecto
rompen tests), valor bajo en una UI que aún itera. Aplazada como
deuda asumida.

## Consecuencias

### Ventajas

- **Suite rápida** (13 s total) permite ciclo de feedback de minutos.
- **Coverage threshold automático** detecta regresiones de cobertura
  en CORE sin esfuerzo manual.
- **Husky pre-push** garantiza que main siempre arranca de un estado
  verde.
- **CI con 4 jobs independientes** identifica claramente dónde falla
  (backend / frontend / E2E / security).
- **Métricas accionables** permiten conversaciones objetivas sobre
  calidad sin recurrir a métricas de vanidad.

### Inconvenientes

- **Falsos positivos posibles** en E2E con SSR de TanStack Start
  (`page.route` no intercepta llamadas server-side). Mitigado limitando
  los E2E a shell + rutas + guards.
- **Husky pre-commit añade ~10 s** a cada commit. Mitigable con
  `--no-verify` en emergencias documentadas.
- **Tests integración no corren en CI** (requieren Postgres real,
  Supabase no levantable en GitHub Actions). Mitigado con marker
  `@pytest.mark.integration` y ejecución manual antes de release.

### Efectos futuros

- Si el proyecto crece, **mantener la pirámide** es prioridad. La
  tentación de "todo E2E" crecerá con la presión por validación
  end-to-end; resistirla.
- Si se añade un módulo de pagos o cualquier feature de alto riesgo,
  **subir el coverage threshold de su `src/lib/<feature>/**`** a 95%
  o 100%.
- **Mutation testing** y **visual regression** se reevalúan cuando el
  proyecto pase a producción con usuarios externos.

## Documentación relacionada

- [`docs/project/06-testing-and-quality.md`](../project/06-testing-and-quality.md) — Operativa (comandos, scripts, gates).
- [`docs/master/06-calidad-testing-y-refactorizacion.md`](../master/06-calidad-testing-y-refactorizacion.md) — Defensa académica.
- [`docs/reference/SMOKE_TEST.md`](../reference/SMOKE_TEST.md) — Checklist manual pre-release.
