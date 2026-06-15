---
name: feedback_metodo_documentacion
description: Normas permanentes de documentación de BuenChollo — dos bloques (docs/project operativo + docs/master académico), código manda sobre docs viejas, README entrada, índices, ADRs solo relevantes, archive para histórico, IA como apoyo supervisado, revisar al cambiar arquitectura/seguridad/testing/despliegue.
metadata:
  type: feedback
---

Modo de trabajo cuando Pedro pida revisar/crear/reorganizar **documentación** de BuenChollo. Complementa [[feedback_metodo_revision_auditoria]].

**Why:** la doc sirve para DOS cosas a la vez — **mantener/evolucionar BuenChollo como producto real** y **defenderlo como TFM**. Debe ser clara, útil, coherente, honesta y mantenible. Nada inflado, genérico ni de postureo. BuenChollo es proyecto personal real + TFM y **seguirá creciendo** tras la entrega (visión: comunidad fuerte de chollos tecnológicos).

**How to apply:**

1. **Analizar antes de tocar.** Inventario de `.md`, verificar estructura/enlaces/coherencia con el código, diagnóstico, y solo entonces corregir lo seguro. No borrar sin archivar; doc obsoleta pero útil → `docs/archive/`; duplicados → fusionar en el doc correcto (una única fuente de verdad por tema).

2. **Dos bloques separados, NO mezclar:**
   - **`docs/project/`** = operativo (instalar, configurar, ejecutar, mantener, evolucionar). Clara, directa, con comandos reales.
   - **`docs/master/`** = académico (defensa ante tribunal: decisiones, arquitectura, buenas prácticas, calidad, seguridad, uso de IA, limitaciones, mejoras futuras, conclusiones). Formal pero natural, de alumno avanzado, sin vender humo, reconociendo limitaciones.

3. **Estructura real (taxonomía a mantener):** raíz = `README.md` (entrada), `CLAUDE.md`, `SECURITY.md`, `PROJECT_STATUS.md` (bitácora viva). `docs/project/` (01–09 + 00-index), `docs/master/` (00-index + 01–10), `docs/adr/` (ADR-001…009 + index), `docs/reference/` (PLAN_ARQUITECTURA, SECURITY_AUDIT, SMOKE_TEST), `docs/guides/` (Cloudflare.md = guía operativa viva de infra; MIGRATIONS.md), `docs/archive/` (histórico con índice). `.claude/memory/` = memoria de trabajo del asistente (versionada en el repo).

4. **El código manda sobre la doc antigua.** Si un doc contradice el código/estado actual, prioriza la realidad y corrige el doc. **No inventar** funcionalidades, tecnologías ni decisiones. Lo no verificable → marcarlo. Las **mejoras futuras** se marcan como futuras, NUNCA como implementadas.

5. **README** = punto de entrada: orienta a `docs/project/` y `docs/master/`, comandos que coinciden con `package.json` (npm), sin secretos, sin funcionalidades no implementadas, estado real del proyecto. **`docs/master/00-index.md`** = índice de entrega (enlaza los 10 docs). Mantener enlaces internos sin romper (verificar tras mover archivos).

6. **ADRs solo para decisiones relevantes** (no decorativos), formato claro (Estado/Contexto/Decisión/Motivo/Alternativas/Consecuencias), enlazados desde el máster. BuenChollo ya tiene ADR-001…009.

7. **Uso de IA** (`docs/master/08` + ADR-009): explicar la IA como **apoyo supervisado**, no sustituto del criterio; decisiones validadas, código revisado, auditorías iterativas con prompts; responsabilidad final del desarrollador.

8. **Seguridad documental:** ningún doc expone secretos reales (enmascarar si aparecen + recomendar rotación); `.env.example` con valores ficticios.

9. **Revisar la doc cada vez que cambie** arquitectura, seguridad, testing, despliegue o funcionalidades principales. La infra Cloudflare vive en `docs/guides/Cloudflare.md` (fuente de verdad); `docs/project/08-deployment.md` apunta a ella en vez de duplicarla.

10. **Entregable de una revisión real:** informe "Revisión de Documentación - BuenChollo" con resumen ejecutivo, inventario (tabla Archivo/Ruta/Tipo/Estado/Acción), estructura final, coherencia con código, duplicados/archivados, seguridad documental, enlaces, cambios aplicados, próximos pasos (imprescindible/recomendable/opcional/norma futura) y checklist de entrega.

Ver [[project_estado_2026-06]] (estado de producción) y [[feedback_metodo_revision_auditoria]].
