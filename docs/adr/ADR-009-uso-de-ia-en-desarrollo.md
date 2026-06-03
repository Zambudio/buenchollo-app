# ADR-009 — Uso de IA como apoyo supervisado al desarrollo

## Estado

**Aceptado** · 2026-06-02 · formaliza la práctica aplicada de forma
consistente durante todo el desarrollo del proyecto.

## Contexto

El Máster en Desarrollo con IA 2025 exige que la IA sea **parte
explícita** del proceso de desarrollo. Pero "usar IA" puede significar
desde "pegar prompts a ChatGPT y copiar la salida" hasta "vibe coding
sin revisar". Ninguno de los dos extremos es defendible
profesionalmente.

El proyecto necesitaba una decisión documentada sobre:

1. Qué herramienta de IA usar como asistente principal.
2. Qué patrones de uso aplicar (no "úsala para todo").
3. Cómo validar las respuestas de la IA antes de commitear.
4. Qué decisiones siguen siendo exclusivamente humanas.
5. Qué riesgos asume el uso de IA y cómo se mitigan.

Esta decisión necesitaba quedar firmada como ADR para defender
públicamente ante tribunal el papel que la IA ha tenido en
BuenCholloTech.

## Decisión

Adoptar **Claude Code (Anthropic)** como asistente principal del
proyecto, configurado con `CLAUDE.md` en la raíz del repositorio, y
aplicar tres patrones de uso supervisados con validación obligatoria
en cada commit.

### 1. Herramienta principal: Claude Code con `CLAUDE.md`

Claude Code es una CLI integrada que lee el repositorio, ejecuta
comandos (tests, builds, lint), razona sobre los resultados y aplica
cambios al código con autorización explícita. Modelo: Claude Opus 4.7.

**Configuración persistente** en
[`CLAUDE.md`](../../CLAUDE.md):

- Rol que la IA debe asumir (desarrollador senior, arquitecto).
- Contexto técnico del proyecto (stack, ADRs, decisiones).
- Principios obligatorios (Clean Architecture, SOLID, KISS, sin
  sobreingeniería).
- Reglas de seguridad explícitas (no introducir vulnerabilidades
  OWASP, validar input en frontera).
- Forma de trabajar (cambios grandes → plan + confirmación; cambios
  pequeños → ejecutar; siempre indicar archivos modificados y cómo
  probar).

Se carga automáticamente en cada conversación.

### 2. Patrones de uso aplicados

**Patrón A — Auditorías por módulo del máster.**

Para cada bloque (arquitectura, calidad, seguridad, documentación) se
ejecuta:

1. Pedro escribe un prompt extenso (200–400 líneas) con rol,
   contexto, fases a ejecutar y formato de informe.
2. La IA realiza la auditoría completa: lee código, ejecuta
   comandos de inspección (pip-audit, npm audit, grep peligroso),
   produce informe priorizado.
3. Pedro revisa y aprueba el plan de acción.
4. La IA implementa cambios en commits pequeños con verificación
   local antes de cada push.
5. CI valida.

**Patrón B — Implementación guiada de features.**

1. Pedro describe el caso de uso funcionalmente.
2. IA entra en modo plan (`EnterPlanMode`) y propone cambios en
   backend (modelos, repos, servicio, router, schemas), frontend
   (componentes, hooks, rutas), migración Alembic si aplica, y
   tests a añadir.
3. Pedro aprueba; IA implementa con tests entre cada paso.

**Patrón C — Refactor seguro.**

1. Verificar que los tests cubren el comportamiento actual; si no,
   añadir tests **antes** del refactor.
2. Refactorizar.
3. Tests siguen verdes → commit.

### 3. Validación obligatoria en cada commit

Tres líneas defensivas:

- **Línea 1 — Tests automatizados**: `npm run quality`
  (lint + typecheck + 72 Vitest) y `pytest -m "not integration"`
  (78 unit) en local antes del commit; 4 jobs de CI tras el push.
- **Línea 2 — Revisión humana**: Pedro lee cada commit antes de
  pushear, verifica que entiende lo que hace y rechaza
  sobreingeniería.
- **Línea 3 — Auditorías cruzadas**: una IA auditando trabajo
  previo de la misma IA detecta inconsistencias, falsos positivos en
  tests y decisiones contradictorias acumuladas.

### 4. Lo que la IA NO sustituye

Decisiones que siguen siendo exclusivamente humanas:

- Aprobación de PRs y commits a `main`.
- Arquitectura final (la IA propone, los ADRs los firma Pedro).
- Diseño de UX.
- Elección de stack (basada en familiaridad y mantenibilidad).
- Decidir si una feature merece la pena.
- Validar que un test refleja un flujo real del usuario.
- Decisiones de producto y negocio.

### 5. Riesgos identificados y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Sobreingeniería | `CLAUDE.md` declara "sin abstracciones para un único uso"; Pedro rechaza commits con patrones innecesarios |
| Código aparentemente correcto pero inseguro | Auditoría dedicada (sprint S1–S7); CI con `security-audit` (pip-audit, npm audit, gitleaks) |
| Dependencias innecesarias | Verificación obligatoria contra deps existentes antes de añadir |
| Alucinaciones (APIs inexistentes) | TS strict + Pydantic + ESLint detectan inmediatamente; Husky bloquea commits con lint/test rojo |
| Documentación inflada | Reglas en `CLAUDE.md` ("short and concise"); estructura limita número total de documentos |
| Decisiones no defendibles | Decisiones importantes van a ADR firmados con alternativas evaluadas |

## Motivo

### Por qué Claude Code y no GitHub Copilot solo

- Copilot es excelente para autocompletado línea-a-línea, pero **no
  razona sobre arquitectura ni audita módulos completos**.
- Claude Code lee y modifica el repo entero, ejecuta tests, razona
  sobre resultados y mantiene contexto entre interacciones.
- Para auditorías por módulo (el patrón con más impacto del
  proyecto), Copilot no aplica.

### Por qué Opus 4.7 y no un modelo más pequeño

- La capacidad de razonamiento profundo sobre código grande es la
  diferencia clave: un modelo pequeño da respuestas plausibles pero
  superficiales sobre arquitectura.
- Para autorrefactor o autoreview, el coste por hora del modelo
  pequeño es marginalmente menor que el coste por hora de un
  desarrollador re-haciendo el trabajo.

### Por qué `CLAUDE.md` y no prompts ad-hoc

- Sin `CLAUDE.md`, la IA llega "fría" a cada conversación y exige
  re-explicar el contexto. El asistente acaba aplicando patrones
  genéricos que no encajan con el proyecto (microservicios, sistemas
  de plugins, sobreingeniería).
- Con `CLAUDE.md` cargado automáticamente, la IA respeta los
  principios del proyecto desde el primer turno.

### Por qué tres líneas defensivas

- Tests automáticos son **necesarios pero insuficientes**: pueden
  validar que el código hace algo, no que **es lo correcto**.
- Revisión humana es **insuficiente sin tests**: el ojo humano no
  detecta regresiones sutiles consistentemente.
- Auditorías cruzadas detectan **deuda acumulada** que ni tests ni
  revisión turn-by-turn capturan.

### Por qué documentar todo esto

- Defensa ante tribunal: "¿qué papel ha tenido la IA?" tiene una
  respuesta concreta con evidencia (CLAUDE.md, commits, ADRs,
  documentos).
- Reproducibilidad: alguien puede leer este ADR y replicar el método
  en su propio proyecto.

## Alternativas consideradas

### A1: No usar IA, demostrar capacidad sin asistente

**Rechazada**. Es **ignorar el contenido del máster**, que se llama
explícitamente "Desarrollo con IA". Además, no usar IA en un proyecto
de 2026 es elegir conscientemente ser menos productivo.

### A2: Vibe coding (IA genera, Pedro pega sin entender)

**Rechazada**. Es la práctica peligrosa que el módulo de IA del máster
busca evitar. Genera código que aparenta funcionar pero el
desarrollador no puede defender ni mantener.

### A3: IA sólo para autocompletado (Copilot only)

**Rechazada**. Desaprovecha la capacidad de razonamiento profundo.
Las auditorías por módulo (el patrón con más impacto del proyecto)
no serían posibles con autocompletado solo.

### A4: Múltiples IA en paralelo sin coordinación

**Rechazada**. Mezclar Claude + ChatGPT + Gemini sin un sistema de
configuración persistente genera código incoherente. ChatGPT y
Gemini se usan **ocasionalmente** como segundo opinión, no como
asistentes principales.

### A5: Documentar sin formalizar como ADR

**Rechazada**. La decisión sobre el uso de IA es **arquitectónica**
(afecta cómo se desarrolla y mantiene el sistema), por lo tanto
merece ADR firmado.

## Consecuencias

### Ventajas

- **Velocidad multiplicada**: auditorías que manualmente exigirían
  semanas se cierran en sesiones de horas o días.
- **Documentación consistente**: la IA mantiene tono, formato y
  referencias cruzadas a lo largo de todo el proyecto.
- **Defensa académica explícita**: cada decisión sobre uso de IA está
  documentada.
- **Replicabilidad**: el método puede aplicarse en proyectos futuros.

### Inconvenientes

- **Dependencia de una herramienta externa** (Claude Code, Anthropic).
  Si el servicio cae o cambia de modelo, el método actual se ve
  afectado.
- **Coste económico**: el modelo Opus 4.7 tiene coste por token.
  Para un proyecto académico es asumible; para producción a gran
  escala habría que evaluar.
- **Curva de aprendizaje** en escribir prompts efectivos. Un prompt
  vago genera respuestas vagas; un prompt bien estructurado genera
  trabajo de calidad. La habilidad de "escribir prompts" se convierte
  en habilidad profesional medible.

### Efectos futuros

- Cuando aparezca un modelo mejor (Opus 4.8, Sonnet 5...), migrar es
  trivial: cambiar el modelo en la configuración y verificar que
  `CLAUDE.md` sigue siendo aplicable.
- Si el proyecto incorpora un segundo desarrollador, `CLAUDE.md` se
  convierte en **onboarding doc** para ambos: humano y IA.
- Los patrones de uso documentados aquí (auditorías por módulo,
  implementación guiada, refactor seguro) son aplicables a cualquier
  proyecto futuro del autor.

## Documentación relacionada

- [`docs/master/08-uso-de-ia-en-el-desarrollo.md`](../master/08-uso-de-ia-en-el-desarrollo.md) — Capítulo de defensa académica.
- [`docs/project/05-development-workflow.md`](../project/05-development-workflow.md) — Operativa diaria.
- [`CLAUDE.md`](../../CLAUDE.md) — Configuración persistente de la IA.
- [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md) — Bitácora de sprints (cada sección 3.bis…3.sexies muestra el patrón en acción).
