# 06 — Calidad, testing y refactorización

## Estrategia general

La calidad del proyecto se aborda en tres ejes coordinados:

1. **Testing automatizado** con pirámide clara (más unit, menos E2E).
2. **Coverage estratégico** sin perseguir 100% global ("vanity metric").
3. **Quality gates** automáticos en local (Husky) y en CI (GitHub Actions).

Estos tres ejes se apoyan en una filosofía:

> Los tests son la red de seguridad que permite refactorizar sin miedo.
> Si los tests son rígidos o frágiles, dejas de refactorizar. Si son
> útiles, refactorizas todo el tiempo.

## Pirámide de testing

```
              ┌─────────────┐
              │  E2E (8)    │    Playwright + chromium · ~6s
              └─────────────┘
        ┌──────────────────────┐
        │ Integration (13)     │  RTL + userEvent · ~0,7s
        └──────────────────────┘
   ┌──────────────────────────────────┐
   │  Unit (137 = 78 backend + 59 web) │ Vitest / pytest · ~1,1s
   └──────────────────────────────────┘
```

**Total automatizado**: 167 tests verdes en aproximadamente 13 segundos
(suma de todas las suites).

### Por qué esta proporción

| Capa | Coste por test | Valor que aporta |
|---|---|---|
| Unit | < 5 ms | Verifica lógica pura: validaciones, cálculos, type guards. **Si esta capa es robusta, el resto se simplifica**. |
| Integration | < 100 ms | Verifica que un componente real se comporta como espera el usuario. Mocks sólo en fronteras (auth, red). |
| E2E | < 1 s | Sólo flujos críticos: la app responde, el guard de admin funciona, la búsqueda redirige. **No reglas de negocio**. |

Un E2E que prueba "click en favorito guarda en BD" es un fallo de
pirámide: lo correcto es un unit test del guard, un integration test
del click + mock favoritesApi, y un E2E que sólo verifique que la app
no está rota.

## Coverage estratégico — 100/80/0

No se persigue 100% global. En su lugar, **100 / 80 / 0** por tier:

| Tier | % objetivo | Qué entra | Estado real |
|---|---|---|---|
| **CORE** | 90–100% | Funciones puras: validaciones, cálculos, type guards, transformaciones críticas | ✅ Threshold automático en `vitest.config.ts` |
| **IMPORTANT** | ~80% | Componentes visibles, formularios, flujos de navegación | 🟡 Cubierto parcialmente con integration tests |
| **INFRASTRUCTURE** | 0% | Tipos, constantes, configs, código generado, primitivos shadcn | ⛔ Excluido |

### CORE — código que si falla rompe el negocio

| Archivo | Coverage |
|---|---|
| `src/lib/errors.ts` | 100% |
| `src/lib/format.ts` | 96.07% |
| `src/lib/validation/deals.ts` | 100% |
| `src/lib/validation/alerts.ts` | 100% |
| `src/lib/utils.ts` | 100% |
| `src/lib/constants.ts` | 100% |
| `src/services/api/deals.ts` (type guard `isDuplicateDealError`) | ✅ tipado guard cubierto |

Threshold en `vitest.config.ts`:

```ts
thresholds: {
  "src/lib/**": { lines: 90, functions: 90, branches: 80, statements: 90 },
}
```

Si baja, CI rompe.

### IMPORTANT — visible al usuario

Cubierto con integration tests:

- `DealCard` (7 tests): título, precio, descuento, badge caducado, favorito.
- `Header` (6 tests): CTA acceder/perfil, badge unread, dropdown admin.

### INFRASTRUCTURE — excluido

- `src/components/ui/**` (shadcn upstream, ya testado).
- `src/routeTree.gen.ts` (generado por TanStack Router).
- `src/integrations/supabase/types.ts` (generado por Supabase CLI).
- `src/lib/query-client.ts` (config sin lógica).
- Todos los `*.config.*`.

### Por qué NO 100% global

Subir el porcentaje global escribiendo tests sobre `routeTree.gen.ts`
o sobre los primitivos shadcn **no mejora la calidad real**. Es una
métrica de vanidad. La métrica útil es **el coverage del código que
puede romper el negocio**.

## Quality gates

### Pre-commit (Husky, ~10 s)

```bash
npm run lint        # ESLint estricto
npm run typecheck   # tsc --noEmit con strict + noUncheckedIndexedAccess
```

Si falla, el commit se aborta.

### Pre-push (Husky, ~3 s)

```bash
npm run test:run    # Vitest run (72 unit + integration)
```

Si falla, el push se aborta. Los E2E NO entran como gate local: tardan
~10 s y dependen del build de Vite; corresponden a CI.

### Bypass legítimo `--no-verify`

Sólo en emergencia y con justificación en el mensaje del commit:

```bash
git commit --no-verify -m "fix(prod): rollback urgente — bypass gate"
git push --no-verify
```

Reglas:

- Nunca en `main` con otros desarrolladores activos.
- El siguiente commit debe restaurar el estado verde.

### CI — `.github/workflows/ci.yml`

4 jobs en cada `push` a `main` y cada `pull_request`:

| Job | Comprueba | Artifact |
|---|---|---|
| `backend` | pytest -m "not integration" (78 unit) | — |
| `frontend` | typecheck + ESLint + Vitest con coverage threshold | `coverage/` siempre |
| `e2e` | Playwright chromium con webServer | HTML report + traces en fallo |
| `security-audit` | pip-audit, npm audit --omit=dev, gitleaks | — |

Si cualquier job falla, el commit aparece rojo y no se mergea.

## Métricas accionables

### Tier 1 — revisión frecuente (cada PR / cada día)

| Métrica | 🟢 Verde | 🟡 Amarillo | 🔴 Rojo | Acción si rojo |
|---|---|---|---|---|
| Test Success Rate | 100% | 95–99% | < 95% | Bloquear merge, investigar |
| Build Success Rate (main, semanal) | 100% | 90–99% | < 90% | Hotfix prioritario |
| Lint errors | 0 | 0 | ≥ 1 | Pre-commit bloquea |
| E2E pasando | 8/8 | 7/8 | < 7/8 | Revertir cambio sospechoso |

### Tier 2 — revisión por hito (release / milestone)

| Métrica | 🟢 | 🟡 | 🔴 |
|---|---|---|---|
| Duración test:run | < 5 s | 5–15 s | > 15 s |
| Duración CI completa | < 5 min | 5–10 min | > 10 min |
| MTTR fallo CI en main | < 4 h | 4–24 h | > 24 h |

### Tier 3 — revisión periódica (mensual / pre-release)

| Métrica | 🟢 | 🟡 | 🔴 |
|---|---|---|---|
| CORE coverage | ≥ 90% | 80–89% | < 80% |
| TODO / FIXME en `src/` | ≤ 5 | 6–15 | > 15 |
| Smells críticos ESLint + SonarLint | 0 | 1–3 | > 3 |
| Dependencias desactualizadas (Dependabot) | 0 major | 1–3 | > 3 |

### Métricas que NO se persiguen

- Líneas de código.
- Número de commits.
- Coverage global sin contexto.
- Número de features.

Estas son métricas de vanidad. Aumentar líneas no es valor; aumentar
coverage global cubriendo `types.ts` es ruido; "más features" sin
justificación es scope creep.

## Refactor seguro

La estrategia de testing **permite refactorizar con confianza**. Cada
sprint del proyecto incluyó refactors significativos sin que ningún
test rojo se quedara en main:

- **Refactor F-03 (frontend)**: split de hooks gigantes en
  `features/<dominio>/hooks/` con TanStack Query.
- **Refactor B-02 (backend)**: extraer `DealService` del router, con
  `AlertMatcher` por DI.
- **Refactor B-03**: helper `_base_deal_query()` para centralizar
  `selectinload` repetido.
- **Refactor B-04**: `matches_alert()` extraído del repositorio a
  función pura testeable.
- **Refactor B-05**: `_safe_run()` para el cleaner, eliminando el
  patrón triple try/except idéntico.

**El proceso aplicado en cada uno**:

1. Verificar que los tests cubren el comportamiento actual.
2. Si no, añadir tests **antes** de refactorizar.
3. Refactorizar.
4. Tests siguen verdes → commit.

## Code smells detectados y resueltos

| Smell | Dónde estaba | Resolución |
|---|---|---|
| **Long Method** | `DealService.create_deal()` con 40+ líneas mezclando slug, FK check, AlertMatcher | Extraído a `_check_external_id_unique`, ajuste de FK en helper |
| **Duplicate Code** | `selectinload(category, subcategory, store)` en 6 queries | `_base_deal_query()` centraliza |
| **Magic Numbers** | `200`, `100` thresholds de temperatura, `30`, `5` rate limits | Constantes con nombre |
| **Primitive Obsession** | Strings para status de chollos | `DealStatus` literal type + `DEAL_STATUS_OPTIONS as const` |
| **Long Parameter List** | `search()` con 5+ params | Object pattern `{category_id, store_id, search, limit, offset}` |
| **Inappropriate Intimacy** | Frontend consultando Supabase directamente | ADR-002: ningún `supabase.from()` en frontend |

## Deuda asumida (con justificación)

| Item | Por qué se asume |
|---|---|
| **Visual regression** con `toHaveScreenshot` | Brittleness sin valor — cambios CSS sin defecto rompen tests |
| **Page Object Model elaborado** | Con 8 E2E, helpers ad-hoc son más legibles |
| **MSW (Mock Service Worker)** | Playwright `page.route` + Vitest mocks bastan; MSW tendría sentido con docenas de tests |
| **Tests E2E completos del admin** | OAuth Google requiere mocks complejos; cubierto con integration tests + smoke manual |
| **Tests integración en CI** | Requiere Postgres real; en CI no levantamos BD |
| **Refactor `admin.chollos.tsx`** (940 líneas) | God Component conocido; partir tiene alto riesgo de regresión |
| **SonarJS / SonarQube** | ESLint estricto + TS strict ya cubren lo que SonarJS detectaría |

## Defensa ante el tribunal

### ¿Por qué no se busca 100% global de coverage?

Porque sería una métrica de vanidad. Aplicamos **100/80/0**: 90–100%
en CORE (lógica de negocio), ~80% en componentes visibles, 0% en
infraestructura (tipos, configs, generado, primitivos).

El threshold automático del CI (`vitest.config.ts`) sólo gatea
`src/lib/**`. Subir el porcentaje global escribiendo tests sobre
`routeTree.gen.ts` no mejora la calidad real.

### ¿Cómo se controla la deuda técnica?

- **Documentada explícitamente** en `PROJECT_STATUS.md §4`, en este
  documento y en `docs/SECURITY.md`. Cada item tiene justificación y
  coste futuro estimado.
- **Métricas Tier 3** monitorizadas: TODO/FIXME en `src/`, smells
  críticos ESLint, dependencias desactualizadas (Dependabot weekly).
- **Política Boy Scout Rule**: cada PR deja el código tocado algo más
  limpio que como estaba.
- **Refactor seguro**: tenemos red de 167 tests antes de tocar
  cualquier lógica crítica.

### ¿Cómo se asegura que los flujos críticos funcionan?

Tres redes complementarias:

1. **Tests automáticos en CI**: el merge a `main` exige verde en
   backend + frontend + E2E + security-audit. Cualquier ruptura es
   detectada antes de llegar a producción.
2. **Husky pre-push**: imposible pushear código que no pasa el suite
   Vitest sin `--no-verify` explícito.
3. **Smoke test manual antes de cada release**: 10 secciones,
   ~50 checks, documentado en
   [`docs/reference/SMOKE_TEST.md`](../reference/SMOKE_TEST.md). Se
   ejecuta antes de cada tag.

### ¿Cómo se usan métricas accionables y no de vanidad?

Tres tiers (§ Métricas accionables):

- **T1** se revisa **cada PR** y dispara acción inmediata.
- **T2** se revisa **por hito**, identifica regresiones de tiempo y
  estabilidad.
- **T3** se revisa **mensualmente** o pre-release, vigila la salud a
  medio plazo.

Cada métrica tiene umbrales verde/amarillo/rojo concretos y una
acción prescrita si entra en rojo. No medimos "líneas de código" ni
"número de commits".
