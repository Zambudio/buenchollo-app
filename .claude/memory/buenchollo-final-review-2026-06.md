---
name: buenchollo-final-review-2026-06
description: Veredicto de la auditoría final de TFM (jun 2026), falsos positivos a no repetir y cifras de tests pendientes de fijar.
metadata:
  type: project
---

Auditoría final extrema (tribunal TFM) realizada el 2026-06-15 sobre el monorepo.

**Veredicto:** proyecto senior/producción. Nota actual estimada **8,7–9,0/10**, potencial **9,5–10**.
No hay bloqueantes técnicos; lo que separa del 10 son incoherencias documentales menores y un par
de smells de diseño. Ver [[project_estado_2026-06]].

**Dos falsos positivos detectados por subagentes Explore — NO volver a alarmar:**
- "`.env` con secretos commiteado" es FALSO. `git ls-files` solo muestra `*.env.example` (con
  placeholders). `.env` está en `.gitignore:5` y nunca estuvo en el historial; el CI corre
  `gitleaks` con `fetch-depth: 0`. Los secretos viven solo en el árbol local (normal). Riesgo real
  único: entregar el proyecto como ZIP de carpeta en vez de clon/`git archive` (documentado ya en
  `docs/project/07-security.md`).
- "No existe CI/CD" es FALSO. Hay `.github/workflows/ci.yml` (4 jobs: backend pytest, frontend
  typecheck+lint+coverage, E2E Playwright, security-audit con pip-audit+npm audit+gitleaks) y
  `.github/dependabot.yml`. El subagente miró dentro de `buenchollo-web/` en vez de la raíz.

**Pendiente real (no resuelto en la auditoría): cifras de tests incoherentes.**
- Verificado por mí: frontend = **72 vitest** (`npx vitest list`) + **8 E2E** (3 specs).
- Backend: NO pude correr pytest en local porque mi entorno tiene **Python 3.14** y pydantic-settings
  falla al parsear `cors_origins` (el proyecto/CI usan **3.11**, donde funciona — no es bug del
  proyecto). Conteo bruto = 106 `def test_` (≈97 excluyendo integración).
- Las docs dicen 167 total (= 87 backend + 72 web + 8 E2E) pero el badge de `buenchollo-api/README.md`
  dice 97 y el conteo bruto apoya ~97 backend → total real podría ser ~177. **Hay que correr bajo
  Python 3.11**: `cd buenchollo-api && pytest -q` y `pytest -q -m "not integration"`, fijar UNA cifra
  y propagarla a: `README.md` (badge L21 + `docs/project/06` L3/L23/L26 + `docs/master/06` L4/L29/L33
  + `buenchollo-api/README.md` badge L11). NO editar a ciegas: meter un número equivocado en el TFM
  es peor que la deriva. Ver [[feedback_metodo_calidad]].

**Recomendaciones para subir a 10 (no aplicadas, requieren decisión):**
- `buenchollo-web/src/routes/admin.chollos.tsx` (986 líneas, God Component): documentar como deuda
  consciente en `PROJECT_STATUS.md`/`docs/master/09` o extraer hooks (`useAdminDeals`, `useDealForm`).
- 8 `console.error` en rutas frontend: enrutar a logger o justificar por qué se dejan.
- Deuda `CORS_ORIGINS`: el validator existe pero pydantic-settings pre-parsea campos lista como JSON
  antes del validator, así que una cadena CSV plana falla igual → la deuda de CLAUDE.md sigue vigente.
