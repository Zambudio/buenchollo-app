# Agentes especializados — BuenChollo Tech

Índice y plan de agentes de Claude Code para el proyecto **BuenChollo Tech / BuenCholloTech**.

> Estado: **configuración base completa** (12 agentes). El índice y las reglas están definidos.
> Los agentes pueden ampliarse o afinarse de forma incremental según evolucione el proyecto.

---

## Qué son los agentes del proyecto

BuenChollo Tech es una web y ecosistema de publicación de chollos tecnológicos con afiliación
(uso personal + Trabajo Final de Máster). Los **agentes** son perfiles especializados y reutilizables
de Claude Code, cada uno con un rol acotado (desarrollo, automatización, contenido, SEO, afiliación,
redes), pensados para **trabajar de forma controlada, no improvisada**.

Cada agente vivirá en su propio archivo dentro de [`.claude/agents/`](.) (un archivo por agente),
con instrucciones claras, límites y formato de salida estructurado. Se irán definiendo de forma
incremental conforme se necesiten.

### Cómo encajan con el resto del proyecto

- **Reglas del proyecto**: [`CLAUDE.md`](../../CLAUDE.md) manda sobre cualquier agente.
- **Memoria y normas de trabajo**: [`.claude/memory/`](../memory/) (versionada). Ningún agente la
  modifica ni la ignora; debe respetarla y, cuando aplique, apoyarse en ella.
- **Documentación**: `docs/project/` (operativo) y `docs/master/` (académico). Los agentes no mezclan
  ambos bloques.

> **Fuente de verdad del formato de publicaciones de Telegram**: el código
> (`buenchollo-api/app/modules/telegram/application/post_generator.py`) — 🍄/💶/💰/🛒/✏️/⚠️.
> El formato editorial original (🔥/📉/📦/👉/ℹ️) queda archivado; cambiar el formato visual implica
> tocar **en bloque** código + agentes + docs. La transparencia de afiliación en Telegram se cubre
> vía **descripción del canal**, no por publicación.

---

## Reglas generales (obligatorias para TODOS los agentes)

Ningún agente puede romper estas reglas. Prevalecen sobre cualquier instrucción concreta del agente.

1. **Nada se publica automáticamente** sin aprobación explícita del usuario.
2. **No inventar datos**: ni precios, descuentos, disponibilidad, stock ni datos técnicos.
3. **No proponer scraping directo de Amazon** ni scraping prohibido de ninguna fuente.
4. **No romper el formato oficial** de publicaciones de BuenChollo Tech.
5. **Pensar siempre en automatización futura** (Python, bots, workers, colas, BD, publicación).
6. **Salidas estructuradas** y fáciles de convertir en código (JSON/tablas/esquemas claros).
7. **Evitar sobreingeniería**: la opción más simple y mantenible que cumpla (KISS, YAGNI, DRY).
8. **Compatibilidad técnica**: trabajar de forma alineada con Python, Telegram Bot API, base de datos
   y futuros workers.
9. **Respetar documentación y memoria** existentes del proyecto.
10. **Priorizar siempre**: simplicidad · escalabilidad · legalidad · automatización futura.

> Cualquier agente que necesite saltarse una de estas reglas debe **parar y avisar**, no improvisar.

---

## Agentes previstos

Estado: `⬜ pendiente` · `🟡 en definición` · `✅ configurado`.

### Agentes técnicos

| Agente | Rol | Estado |
|---|---|---|
| [`deal-automation-architect`](deal-automation-architect.md) | Arquitecto de **evolución** sobre la arquitectura existente: flujos, casos de uso, adaptadores, validaciones, schedulers/jobs internos, deduplicación y estados de publicación, sin rediseñar desde cero. | ✅ |
| [`frontend-designer`](frontend-designer.md) | Revisión y diseño UI/UX: pantallas, componentes, responsive, jerarquía visual, accesibilidad, usabilidad y conversión limpia (web y admin), sin implementar código salvo instrucción. | ✅ |
| [`security-reviewer`](security-reviewer.md) | Revisor de seguridad técnica: auth/roles, Supabase/RLS, CORS, secretos, variables de entorno, endpoints, logs, dependencias, integraciones, Cloudflare, CI/CD y OWASP. | ✅ |
| [`qa-test-engineer`](qa-test-engineer.md) | Ingeniero QA: tests (Vitest/Testing Library/Playwright/pytest), regresiones, criterios de aceptación, CI y validación antes de mergear. Único agente con `Bash` para ejecutar pruebas de solo lectura. | ✅ |

### Agentes de chollos y afiliación

| Agente | Rol | Estado |
|---|---|---|
| [`deal-finder`](deal-finder.md) | Localiza y prepara candidatos a chollo desde fuentes permitidas: criterios de búsqueda, detección de duplicados y datos listos para validar. Sin scraping prohibido, sin inventar datos, sin publicar. | ✅ |
| [`price-validator`](price-validator.md) | Validador **estricto** de precio actual, precio anterior, ahorro exacto, porcentaje real, duplicidad y criterios mínimos de publicación. Bloquea o deja pendiente si los datos no son fiables. | ✅ |
| [`deal-publisher`](deal-publisher.md) | Genera y revisa publicaciones de chollos (Telegram/web) respetando el formato oficial verificado en código, con datos solo verificados y sin afirmaciones inventadas. | ✅ |
| [`affiliate-compliance`](affiliate-compliance.md) | Cumplimiento de afiliación: reglas de Amazon Afiliados/Creators API, transparencia de enlaces, uso correcto de precios, avisos legales y riesgos de publicación. | ✅ |

### Agentes de contenido y crecimiento

| Agente | Rol | Estado |
|---|---|---|
| [`blog-writer`](blog-writer.md) | Redacta y revisa artículos del blog: esquemas, borradores y mejoras de contenido útil (tecnología, guías de compra), respetando SEO, afiliación y datos verificables. | ✅ |
| [`seo-reviewer`](seo-reviewer.md) | SEO técnico y editorial: titles, metadescriptions, H1/H2, slugs, indexabilidad, enlazado interno, intención de búsqueda y calidad; sin tácticas agresivas ni contenido basura. | ✅ |
| [`social-media-manager`](social-media-manager.md) | Adapta contenido a Instagram, X, Threads, Telegram: copies, calendarios ligeros e ideas de crecimiento, con tono de marca, sin publicar automáticamente ni inventar datos. | ✅ |
| [`analytics-reviewer`](analytics-reviewer.md) | Analiza clicks, votos, favoritos, categorías, Telegram, SEO y campañas; decisiones basadas en datos reales, distingue dato de hipótesis y no inventa métricas. | ✅ |

---

## Convenciones para definir cada agente

Todo agente (los 12 actuales y los que se añadan) sigue una estructura común:

- **Identidad y alcance**: qué hace y, sobre todo, qué **no** hace.
- **Reglas heredadas**: cumple las reglas generales de arriba.
- **Entradas esperadas** y **formato de salida** (estructurado, listo para automatizar).
- **Límites y avisos**: cuándo debe parar y pedir aprobación.
- **Relación con otros agentes**: con quién se coordina y a quién deriva.

Al añadir un agente nuevo: crear su archivo, registrarlo en la tabla de arriba y enlazarlo
desde la sección "Relación con otros agentes" de los agentes con los que colabore (relaciones
coherentes en ambos sentidos).
