# 08 — Uso de IA en el desarrollo

> Este documento se redacta con un cuidado particular: el módulo de
> **Desarrollo con IA** del máster exige justificar el papel que la IA
> ha tenido en el proyecto. La respuesta honesta es **mucho, pero
> siempre bajo supervisión humana con validación obligatoria**.

## Herramientas utilizadas

### Principal — Claude Code (Anthropic)

Claude Code es el asistente principal del proyecto. Funciona como una
CLI integrada con el repositorio que:

- Lee el código existente con herramientas de búsqueda y edición.
- Ejecuta comandos (tests, builds, lint) y razona sobre los
  resultados.
- Aplica cambios al código directamente, con autorización explícita.
- Hace commits siguiendo convenciones documentadas.

**Versión usada**: Claude Opus 4.7 como modelo principal (capacidad de
razonamiento profundo sobre código grande), con caídas eventuales a
Haiku 4.5 para tareas rápidas (lecturas, comprobaciones).

**Configuración persistente**: el fichero
[`CLAUDE.md`](../../CLAUDE.md) en la raíz del repositorio define el
rol que la IA debe asumir, el contexto técnico, los principios
obligatorios y las reglas de oro. Se carga automáticamente en cada
conversación.

### Secundarias

- **GitHub Copilot** para autocompletado en VSCode en momentos
  puntuales (no para diseñar arquitectura).
- **ChatGPT** y **Gemini** consultados ocasionalmente para validar
  decisiones contra un segundo modelo.

## Patrones de uso aplicados

### 1. Auditorías por módulo

El patrón más impactante del proyecto. Para cada bloque del máster
(arquitectura, calidad, seguridad, documentación), el flujo fue:

1. **Pedro escribe un prompt extenso** (200–400 líneas) con el rol que
   debe asumir la IA, el alcance de la auditoría, las fases concretas
   a ejecutar, las reglas de oro y el formato del informe esperado.
2. **La IA realiza la auditoría completa** del proyecto: lee código,
   ejecuta comandos (pip-audit, npm audit, grep de patrones
   peligrosos), produce un informe priorizado con hallazgos en
   formato estandarizado (severidad, archivo, evidencia, riesgo,
   recomendación, cambio mínimo).
3. **Pedro revisa el informe** y aprueba el plan de acción.
4. **La IA implementa los cambios** en commits pequeños siguiendo
   el orden de prioridad. Cada commit incluye verificación local
   (pytest, npm run quality) antes del push.
5. **CI valida** que ningún cambio rompe nada.

Ejemplos reales del proyecto:

- **Sprint F1–F7** (hardening arquitectónico, 30 tareas, mayo 2026).
- **Sprint Q1–Q7** (calidad y testing, instalación de Vitest +
  Playwright + Husky + coverage thresholds + métricas, mayo 2026).
- **Sprint S1–S7** (seguridad, auditoría OWASP completa + 6 fixes
  medios + CI security-audit, junio 2026).
- **Sprint de documentación** (este propio sprint que genera la
  documentación que estás leyendo).

### 2. Implementación guiada de features

Para cada feature nueva (alertas, notificaciones, deduplicación por
ASIN, gráfica Keepa, etc.) el flujo fue:

1. **Pedro describe el caso de uso** funcionalmente.
2. **La IA entra en modo plan** (`EnterPlanMode`) y propone:
   - Cambios en backend (modelos, repositorio, servicio, router,
     schemas).
   - Cambios en frontend (componentes, hooks, rutas).
   - Migración Alembic si hay cambio de esquema.
   - Tests a añadir.
3. **Pedro revisa el plan**, pide ajustes, y aprueba.
4. **La IA implementa en commits pequeños** con tests entre cada
   paso.

### 3. Refactor seguro

Cuando se detecta deuda, el patrón aplicado es:

1. **Verificar que los tests cubren el comportamiento actual**. Si
   no, añadir tests **antes** del refactor.
2. **Refactorizar**.
3. **Tests siguen verdes** → commit.

La IA aplica este patrón consistentemente, no toca código sin verificar
que está cubierto. Si una refactorización deja un test rojo, se
revierte el cambio y se replantea.

### 4. Documentación generativa con supervisión

Este documento (y la mayoría de los del directorio `docs/`) se
genera con la IA a partir del código real del proyecto. **No se
inventan funcionalidades**: cada afirmación se contrasta contra el
estado real del repositorio. Si la IA propone documentar algo que no
existe en el código, se rechaza.

## Cómo se valida cada respuesta de IA

Tres líneas defensivas, aplicadas en cada commit:

### Línea 1 — tests automatizados

```bash
# Local antes del commit
npm run quality              # lint + typecheck + 72 vitest
pytest -q -m "not integration"   # 78 pytest

# En CI tras el push
4 jobs: backend, frontend, e2e, security-audit
```

Si la IA genera código que rompe un test, el commit no se hace o el CI
lo bloquea.

### Línea 2 — revisión humana

Pedro **lee cada commit** antes de pushear. Aunque la IA genera el
código, Pedro:

- Comprueba que entiende lo que el commit hace.
- Verifica que el mensaje del commit refleja la realidad.
- Rechaza commits con sobreingeniería evidente.
- Pide simplificación cuando el cambio parece más complejo de lo
  necesario.

### Línea 3 — auditorías cruzadas

Los sprints de seguridad y calidad fueron **auditorías
contra-críticas**: la propia IA actuó como auditor de los sprints
anteriores. Una IA aplicada a auditar el trabajo previo de la misma IA
detecta inconsistencias, falsos positivos en tests, smells acumulados
o decisiones contradictorias.

## Riesgos del uso de IA y mitigaciones aplicadas

### Riesgo 1 — Sobreingeniería

**Riesgo**: la IA tiende a sugerir patrones (Factory, Strategy,
Observer) y abstracciones aunque el caso no lo justifique.

**Mitigación aplicada**:

- `CLAUDE.md` declara explícitamente:
  > "Sin sobreingeniería. Sin abstracciones para un único uso. No
  > añadir manejo de errores, validaciones ni features que no se han
  > pedido."
- Pedro rechaza commits con patrones innecesarios. Ejemplo: cuando la
  IA propuso un `DealServiceFactory`, se rechazó: el constructor
  basta.

### Riesgo 2 — Código aparentemente correcto pero inseguro

**Riesgo**: la IA puede generar código que compila y pasa lint pero
es vulnerable (CORS abierto, SQL concatenado, secrets en logs).

**Mitigación aplicada**:

- Auditoría dedicada de seguridad (sprint S1–S7) que revisó **todo**
  el código sospechoso (CORS, SQL, logs, headers).
- CI con `security-audit` que corre `pip-audit`, `npm audit`,
  `gitleaks` en cada push.
- Política explícita en `CLAUDE.md`:
  > "Be careful not to introduce security vulnerabilities such as
  > command injection, XSS, SQL injection, and other OWASP top 10
  > vulnerabilities."

### Riesgo 3 — Dependencias innecesarias

**Riesgo**: la IA propone librerías para resolver problemas que no
las necesitan ("usa lodash para esto", "instala date-fns").

**Mitigación aplicada**:

- Verificación obligatoria contra dependencias existentes antes de
  añadir nuevas.
- `package.json` y `requirements.txt` revisados periódicamente.
- Ejemplo: la IA propuso `axios` para llamadas HTTP. Se rechazó:
  `fetch` nativo basta y reduce bundle.

### Riesgo 4 — Errores sutiles (alucinaciones)

**Riesgo**: la IA inventa nombres de funciones, parámetros o APIs que
no existen, o usa versiones obsoletas.

**Mitigación aplicada**:

- TypeScript strict + Pydantic strict detectan inmediatamente cuando
  una función no existe.
- Tests detectan cuando una API se llama mal.
- ESLint con `no-explicit-any` evita que la IA "escape" con `any`.
- Hooks de Husky bloquean el commit si lint o tests fallan.

### Riesgo 5 — Documentación inflada

**Riesgo**: la IA tiende a generar documentación verbosa con muchas
secciones decorativas.

**Mitigación aplicada**:

- Reglas explícitas en `CLAUDE.md`:
  > "Your responses should be short and concise. (...) Default to
  > writing no comments. Only add one when the WHY is non-obvious."
- Revisión humana del tono: si un documento suena a "informe
  corporativo", se reescribe.
- Estructura de carpetas que **limita el número total** de
  documentos (9 en `/project`, 11 en `/master`, no 40).

### Riesgo 6 — Decisiones técnicas no defendibles

**Riesgo**: la IA propone una decisión que pasa el lint y tests pero
no se podría defender en una entrevista o tribunal porque está
desactualizada o copiada de patrones populares pero inadecuados.

**Mitigación aplicada**:

- Decisiones importantes van a **ADR firmados** con contexto,
  alternativas y consecuencias documentadas.
- Pedro hace la pregunta "¿podría defender esto ante un tribunal?"
  antes de cerrar cada ADR.

## Lo que la IA NO sustituye

| Decisión | Por qué la sigue tomando Pedro |
|---|---|
| Arquitectura final | Necesita visión a medio plazo del producto, no sólo del código actual |
| Aprobación de PRs / commits a `main` | La IA propone, Pedro aprueba |
| Diseño de UX | La IA no sabe qué frustra a los usuarios reales |
| Validación contra el código real (no las apariencias) | Pedro contrasta cada respuesta de la IA con lo que el repo ejecuta |
| Elección de stack | Decisión humana basada en familiaridad y mantenibilidad |
| Pricing del producto y decisiones de negocio | Quedan fuera del alcance de la IA |
| Decidir si una feature merece la pena | Producto sobre tecnología |
| Validar que un test refleja un flujo real | La IA puede escribir un test que pasa pero no prueba nada útil |

## Ejemplos de uso responsable

### Caso 1: rechazo de sobreingeniería

La IA propuso convertir el `DealCleanerService` en un sistema de
"task workers" con cola de mensajes, retries exponencial, dead letter
queue y métricas Prometheus para "preparar el sistema para escala".

Decisión humana: **rechazado**. El cleaner se ejecuta cada 5 minutos,
no procesa nada crítico y APScheduler basta. Si crece, se cambia.
Patrón `_safe_run()` cubre la única necesidad real (que un job que
revienta no tire al resto).

### Caso 2: validación contra realidad

La IA propuso documentar que el frontend usa **pnpm** porque en el
`buenchollo-web/README.md` lo decía. Decisión humana: **verificado en
el código** que en realidad usamos `npm` (Husky está configurado con
`package.json` root + `prepare: husky`). README desactualizado se
arregla, no se respeta como verdad.

### Caso 3: aceptación con escepticismo

La IA propuso el patrón `vi.hoisted()` para los mocks de Vitest.
Decisión humana: **probado en un test**, confirmado que es la
solución estándar de Vitest (no es invención), aceptado y
generalizado al resto de tests.

### Caso 4: refactor con red de seguridad

La IA propuso refactorizar `admin.chollos.tsx` (940 líneas) en
varios sub-componentes. Decisión humana: **rechazado por ahora**. Los
tests integration no cubren toda la lógica interactiva. Documentado
como deuda asumida con justificación. Cuando haya tests más completos,
se hará.

## Defensa ante el tribunal

### ¿Qué herramientas de IA se han usado?

**Claude Code** (Anthropic) como asistente principal, configurado con
`CLAUDE.md` que define rol, contexto, principios obligatorios y
reglas. Modelo Opus 4.7 (capacidad de razonamiento profundo). En
menor medida, GitHub Copilot para autocompletado en VSCode, y
consultas puntuales a ChatGPT y Gemini para validar contra un segundo
modelo.

### ¿Qué partes ayudó a desarrollar?

Prácticamente todas, con grados distintos de intervención:

- **Auditorías completas por bloque** (arquitectura, calidad,
  seguridad, documentación): la IA hace el análisis profundo,
  Pedro aprueba el plan.
- **Implementación de features**: planificación, código, tests y
  documentación.
- **Refactorizaciones seguras** con red de tests.
- **Generación de documentación** a partir del código real.

### ¿Cómo se validaron sus respuestas?

Tres líneas defensivas: tests automatizados (167 tests + 4 jobs CI),
revisión humana de cada commit, y auditorías cruzadas (la propia IA
revisa el trabajo previo).

### ¿Qué riesgos tiene usar IA?

Identificados y mitigados: sobreingeniería, código aparentemente
correcto pero inseguro, dependencias innecesarias, alucinaciones,
documentación inflada, decisiones no defendibles. Cada riesgo tiene
una mitigación concreta documentada arriba.

### ¿Cómo se aplicó supervisión humana?

Pedro lee cada commit antes de pushear, revisa que entiende lo que
hace, rechaza sobreingeniería, exige tests, y mantiene `CLAUDE.md`
actualizado con reglas que la IA debe respetar. Las decisiones
arquitectónicas y de producto siguen siendo de Pedro.

### Conclusión sobre el uso de IA

La IA no ha reemplazado a Pedro: lo ha multiplicado. Trabajos que
manualmente habrían exigido semanas (auditoría OWASP completa con
fixes, instalación de Vitest + Playwright + Husky + métricas, sprint
de hardening F1–F7 con 30 tareas) se han cerrado en sesiones de horas
o días, **manteniendo la calidad y la responsabilidad humana en cada
decisión que importa**.

El proyecto es defendible precisamente porque el uso de IA está
documentado, supervisado y limitado: la IA acelera la ejecución, la
revisión humana garantiza que el resultado es correcto.
