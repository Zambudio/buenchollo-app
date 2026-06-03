# 🤖 08 · Uso de IA en el desarrollo

> **TL;DR** · **Claude Code** como asistente principal, configurado con
> `CLAUDE.md` persistente. Tres patrones de uso: **auditorías por
> módulo**, **implementación guiada** y **refactor seguro**. Tres
> líneas defensivas de validación. **Cada commit lo aprueba un
> humano**. La IA no sustituye el criterio — lo multiplica.

---

## 🧰 Herramientas utilizadas

### 🥇 Principal — Claude Code (Anthropic)

```
┌──────────────────────────────────────────────────┐
│  Claude Code (CLI integrada con el repo)        │
│                                                 │
│  📖  Lee el código con búsqueda y edición       │
│  ⚙️  Ejecuta comandos (tests, builds, lint)     │
│  🧠  Razona sobre los resultados                │
│  ✏️  Aplica cambios con autorización explícita  │
│  📝  Hace commits con convenciones documentadas │
└──────────────────────────────────────────────────┘
```

**Modelo**: Claude **Opus 4.7** (razonamiento profundo sobre código
grande), con caídas eventuales a **Haiku 4.5** para tareas rápidas
(lecturas, comprobaciones).

**Configuración persistente** en
[`CLAUDE.md`](../../CLAUDE.md):

- Rol que la IA debe asumir (desarrollador senior, arquitecto)
- Contexto técnico del proyecto (stack, ADRs, decisiones)
- Principios obligatorios (Clean Architecture, SOLID, KISS, sin sobreingeniería)
- Reglas de seguridad explícitas (no introducir vulnerabilidades OWASP)
- Forma de trabajar (cambios grandes → plan + confirmación)

> 💡 Se carga **automáticamente** en cada conversación.

### 🥈 Secundarias

- **GitHub Copilot** para autocompletado en VSCode (momentos puntuales)
- **ChatGPT** y **Gemini** consultados ocasionalmente como segunda opinión

---

## 🎨 Patrones de uso aplicados

### 🅰️ Patrón A — Auditorías por módulo

> _El patrón con más impacto del proyecto._

```
                ┌─────────────────────────┐
                │ 1. ✏️  Pedro escribe    │
                │    prompt extenso       │
                │    (200–400 líneas)     │
                │    rol · alcance ·      │
                │    fases · formato      │
                └──────────┬──────────────┘
                           ▼
                ┌─────────────────────────┐
                │ 2. 🤖  IA realiza       │
                │    auditoría completa   │
                │    lee · ejecuta ·      │
                │    produce informe      │
                │    priorizado           │
                └──────────┬──────────────┘
                           ▼
                ┌─────────────────────────┐
                │ 3. 👀  Pedro revisa     │
                │    y aprueba el plan    │
                └──────────┬──────────────┘
                           ▼
                ┌─────────────────────────┐
                │ 4. ⚙️  IA implementa   │
                │    en commits pequeños  │
                │    + verificación local │
                └──────────┬──────────────┘
                           ▼
                ┌─────────────────────────┐
                │ 5. ✅  CI valida        │
                └─────────────────────────┘
```

#### 📚 Ejemplos reales del proyecto

| Sprint | Cuándo | Qué hizo |
|---|---|---|
| **F1–F7** (arquitectura) | mayo 2026 | 30 tareas: docs, Alembic, request_id, rate limiting, audit log, health, Sentry, /v1, frontend pro-grade, CI/CD, smoke test |
| **Q1–Q7** (calidad) | mayo 2026 | Vitest + Playwright + Husky + coverage thresholds + métricas |
| **S1–S7** (seguridad) | junio 2026 | Auditoría OWASP completa + 6 fixes medios + CI security-audit |
| **Documentación** | junio 2026 | Reorganización en `docs/project/` operativa y `docs/master/` académica |

### 🅱️ Patrón B — Implementación guiada de features

```
1. 📋 Pedro describe el caso de uso funcionalmente
        │
        ▼
2. 🗺️ IA entra en modo PLAN (EnterPlanMode)
        │
        ├─ Cambios en backend (modelos, repo, servicio, router, schemas)
        ├─ Cambios en frontend (componentes, hooks, rutas)
        ├─ Migración Alembic si aplica
        └─ Tests a añadir
        │
        ▼
3. 👀 Pedro revisa el plan, pide ajustes, aprueba
        │
        ▼
4. ⚙️ IA implementa en commits pequeños con tests entre cada paso
```

### 🅲️ Patrón C — Refactor seguro

```
1. ✅ Verificar tests cubren comportamiento actual
   │
   └─ ❌ Si no, AÑADIR TESTS antes del refactor
   │
   ▼
2. 🛠️ Refactorizar
   │
   ▼
3. ✅ Tests siguen verdes → commit
```

> 🚨 Si una refactorización deja un test rojo, **se revierte** y se replantea.

---

## 🛡️ Cómo se valida cada respuesta de IA

> Tres líneas defensivas, aplicadas en cada commit.

### 🔵 Línea 1 — Tests automatizados

```bash
# Local antes del commit
npm run quality                    # lint + typecheck + 72 vitest
pytest -q -m "not integration"     # 78 pytest

# En CI tras el push
4 jobs: backend, frontend, e2e, security-audit
```

> 🚨 Si la IA genera código que rompe un test, el commit no se hace
> o el CI lo bloquea.

### 🟢 Línea 2 — Revisión humana

> Pedro **lee cada commit** antes de pushear.

- ✅ Comprueba que **entiende** lo que el commit hace
- ✅ Verifica que el **mensaje del commit refleja la realidad**
- ❌ Rechaza commits con **sobreingeniería evidente**
- ❌ Pide simplificación cuando el cambio parece más complejo de lo necesario

### 🟡 Línea 3 — Auditorías cruzadas

Los sprints de seguridad y calidad fueron **auditorías
contra-críticas**: la propia IA actuó como auditor del trabajo previo
de la misma IA.

> 💡 Detecta inconsistencias, falsos positivos en tests, smells
> acumulados o decisiones contradictorias.

---

## ⚠️ Riesgos del uso de IA y mitigaciones

<table>
<thead>
<tr><th>Riesgo</th><th>Por qué ocurre</th><th>Cómo se mitiga</th></tr>
</thead>
<tbody>
<tr>
  <td>🏗️ <strong>Sobreingeniería</strong></td>
  <td>La IA tiende a sugerir patrones (Factory, Strategy, Observer) aunque el caso no lo justifique</td>
  <td><code>CLAUDE.md</code> declara: <em>"Sin abstracciones para un único uso"</em>. Pedro rechaza commits con patrones innecesarios</td>
</tr>
<tr>
  <td>🚪 <strong>Código aparentemente correcto pero inseguro</strong></td>
  <td>La IA puede generar código que pasa lint pero es vulnerable (CORS abierto, SQL concatenado, secrets en logs)</td>
  <td>Auditoría dedicada de seguridad (S1–S7) + CI con <code>security-audit</code> + política explícita en <code>CLAUDE.md</code></td>
</tr>
<tr>
  <td>📦 <strong>Dependencias innecesarias</strong></td>
  <td>"Usa lodash para esto" · "Instala date-fns"</td>
  <td>Verificación obligatoria contra deps existentes. Ejemplo: IA propuso <code>axios</code>, rechazado: <code>fetch</code> nativo basta</td>
</tr>
<tr>
  <td>👻 <strong>Alucinaciones</strong></td>
  <td>Inventa nombres de funciones, parámetros, APIs</td>
  <td>TS strict + Pydantic + ESLint detectan inmediatamente. ESLint con <code>no-explicit-any</code> evita escape con <code>any</code></td>
</tr>
<tr>
  <td>📚 <strong>Documentación inflada</strong></td>
  <td>Genera prosa verbosa con muchas secciones decorativas</td>
  <td>Reglas en <code>CLAUDE.md</code>: <em>"short and concise"</em>. Estructura limita número total de documentos</td>
</tr>
<tr>
  <td>🎯 <strong>Decisiones técnicas no defendibles</strong></td>
  <td>Propone algo que pasa lint pero está desactualizado o copiado de patrones populares pero inadecuados</td>
  <td>Decisiones importantes van a <strong>ADR firmados</strong> con contexto, alternativas y consecuencias</td>
</tr>
</tbody>
</table>

---

## 🚫 Lo que la IA NO sustituye

| Decisión | Por qué la sigue tomando Pedro |
|---|---|
| 📐 Arquitectura final | Necesita visión a medio plazo del producto |
| ✅ Aprobación de commits a `main` | La IA propone, Pedro aprueba |
| 🎨 Diseño de UX | La IA no sabe qué frustra a los usuarios reales |
| 🔬 Validación contra el código real | Pedro contrasta cada respuesta con lo que el repo ejecuta |
| 🧱 Elección de stack | Decisión humana basada en familiaridad y mantenibilidad |
| 💰 Pricing y decisiones de negocio | Fuera del alcance de la IA |
| 🎯 Decidir si una feature merece la pena | Producto sobre tecnología |
| 🧪 Validar que un test refleja un flujo real | La IA puede escribir un test que pasa pero no prueba nada útil |

---

## 📖 Ejemplos de uso responsable

### 🔍 Caso 1 — Rechazo de sobreingeniería

> **IA propuso**: convertir `DealCleanerService` en un sistema de
> "task workers" con cola de mensajes, retries exponencial, dead letter
> queue y métricas Prometheus para "preparar el sistema para escala".

**Decisión humana**: ❌ **Rechazado**. El cleaner se ejecuta cada 5
minutos, no procesa nada crítico y APScheduler basta. Si crece, se
cambia. Patrón `_safe_run()` cubre la única necesidad real.

### 🔍 Caso 2 — Validación contra realidad

> **IA propuso**: documentar que el frontend usa **pnpm** porque en el
> `README` lo decía.

**Decisión humana**: ✅ **Verificado en el código** que en realidad
usamos `npm` (Husky está configurado con `package.json` root +
`prepare: husky`). README desactualizado se arregla, no se respeta
como verdad.

### 🔍 Caso 3 — Aceptación con escepticismo

> **IA propuso**: el patrón `vi.hoisted()` para los mocks de Vitest.

**Decisión humana**: ✅ **Probado en un test**, confirmado que es la
solución estándar de Vitest (no es invención), aceptado y generalizado
al resto de tests.

### 🔍 Caso 4 — Refactor con red de seguridad

> **IA propuso**: refactorizar `admin.chollos.tsx` (940 líneas) en
> varios sub-componentes.

**Decisión humana**: ❌ **Rechazado por ahora**. Los tests integration
no cubren toda la lógica interactiva. Documentado como deuda asumida
con justificación. Cuando haya tests más completos, se hará.

---

## 📜 Resumen del uso de IA

### ¿Qué herramientas se usaron?

**Claude Code** (Anthropic) como asistente principal, configurado con
`CLAUDE.md` que define rol, contexto, principios obligatorios y
reglas. Modelo Opus 4.7. En menor medida, GitHub Copilot para
autocompletado, y consultas puntuales a ChatGPT y Gemini para validar
contra un segundo modelo.

### ¿Qué partes ayudó a desarrollar?

Prácticamente todas, con grados distintos de intervención:

- 🔍 **Auditorías completas por bloque** (arquitectura, calidad, seguridad, documentación)
- 🛠️ **Implementación de features** (planificación, código, tests, documentación)
- 🔄 **Refactorizaciones seguras** con red de tests
- 📚 **Generación de documentación** a partir del código real

### ¿Cómo se validaron sus respuestas?

Tres líneas defensivas: **tests automatizados** (167 tests + 4 jobs CI),
**revisión humana** de cada commit, **auditorías cruzadas**.

### ¿Qué riesgos tiene usar IA?

Identificados y mitigados: sobreingeniería, código inseguro pero
aparentemente correcto, dependencias innecesarias, alucinaciones,
documentación inflada, decisiones no defendibles. **Cada riesgo tiene
una mitigación concreta documentada**.

### ¿Cómo se aplicó supervisión humana?

Pedro lee cada commit antes de pushear, revisa que entiende lo que
hace, rechaza sobreingeniería, exige tests, y mantiene `CLAUDE.md`
actualizado con reglas que la IA debe respetar.

---

## 🎯 Conclusión sobre el uso de IA

> **La IA no ha reemplazado a Pedro: lo ha multiplicado.**
>
> Trabajos que manualmente habrían exigido semanas (auditoría OWASP
> completa con fixes, instalación de Vitest + Playwright + Husky +
> métricas, sprint de hardening F1–F7 con 30 tareas) se han cerrado
> en sesiones de horas o días, **manteniendo la calidad y la
> responsabilidad humana en cada decisión que importa**.
>
> El proyecto es sólido precisamente porque el uso de IA está
> **documentado, supervisado y limitado**: la IA acelera la
> ejecución, la revisión humana garantiza que el resultado es
> correcto.

---

<p align="center">
  <a href="07-seguridad.md">← Anterior: Seguridad</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="09-limitaciones-y-mejoras-futuras.md">Siguiente: Limitaciones y mejoras →</a>
</p>
