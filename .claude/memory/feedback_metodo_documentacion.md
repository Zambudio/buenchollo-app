---
name: feedback_metodo_documentacion
description: Normas permanentes de documentación de BuenChollo — docs/project operativo + ADRs en docs/adr, código manda sobre docs viejas, README entrada, índices, ADRs solo relevantes, sin carpeta de histórico, IA como apoyo supervisado, revisar al cambiar arquitectura/seguridad/testing/despliegue.
metadata:
  type: feedback
---

Modo de trabajo cuando Pedro pida revisar/crear/reorganizar **documentación** de BuenChollo. Complementa [[feedback_metodo_revision_auditoria]].

**Why:** la doc sirve para **mantener y evolucionar BuenChollo como producto real en producción**. Debe ser clara, útil, coherente, honesta y mantenible. Nada inflado, genérico ni de postureo. BuenChollo es el proyecto personal de Pedro y **seguirá creciendo** (visión: comunidad fuerte de chollos tecnológicos).

**How to apply:**

1. **Analizar antes de tocar.** Inventario de `.md`, verificar estructura/enlaces/coherencia con el código, diagnóstico, y solo entonces corregir lo seguro. Lo superado se elimina (git conserva el histórico) tras mover lo vigente al documento canónico; duplicados → fusionar en el doc correcto (una única fuente de verdad por tema).
2. **Documentación viva sin duplicar:** `docs/project/` = operativa (instalar, configurar, ejecutar, mantener, evolucionar), clara, directa, con comandos reales; `docs/adr/` = decisiones de arquitectura relevantes. No se mantiene carpeta de histórico: la cronología vive en `PROJECT_STATUS.md`.

3. **Estructura real (taxonomía a mantener):** raíz = `README.md` (entrada), `CLAUDE.md`, `SECURITY.md`, `PROJECT_STATUS.md` (bitácora viva). `docs/project/` (01–13 + 00-index), `docs/adr/` (ADR-001…019 + index), `docs/guides/` (runbooks: Cloudflare, NAS-SSH, LOCAL-ENV, MIGRATIONS, SMOKE-TEST, afiliación; con README). `.claude/memory/` = memoria de trabajo del asistente (versionada en el repo).

4. **El código manda sobre la doc antigua.** Si un doc contradice el código/estado actual, prioriza la realidad y corrige el doc. **No inventar** funcionalidades, tecnologías ni decisiones. Lo no verificable → marcarlo. Las **mejoras futuras** se marcan como futuras, NUNCA como implementadas.

5. **README** = punto de entrada: orienta a `docs/project/` y `docs/adr/`, comandos que coinciden con `package.json` (npm), sin secretos, sin funcionalidades no implementadas, estado real del proyecto. Los `00-index.md` de `docs/project/` y `docs/adr/` son los índices de cada bloque. Mantener enlaces internos sin romper (verificar tras mover archivos).

6. **ADRs solo para decisiones relevantes** (no decorativos), formato claro (Estado/Contexto/Decisión/Motivo/Alternativas/Consecuencias), enlazados desde `docs/adr/00-index.md`. BuenChollo ya tiene ADR-001…009.

7. **Uso de IA** (ADR-009): explicar la IA como **apoyo supervisado**, no sustituto del criterio; decisiones validadas, código revisado, auditorías iterativas con prompts; responsabilidad final del desarrollador.

8. **Seguridad documental:** ningún doc expone secretos reales (enmascarar si aparecen + recomendar rotación); `.env.example` con valores ficticios.

9. **Revisar la doc cada vez que cambie** arquitectura, seguridad, testing, despliegue o funcionalidades principales. La infra Cloudflare vive en `docs/guides/Cloudflare.md` (fuente de verdad); `docs/project/08-deployment.md` apunta a ella en vez de duplicarla.

10. **Entregable de una revisión real:** informe "Revisión de Documentación - BuenChollo" con resumen ejecutivo, inventario (tabla Archivo/Ruta/Tipo/Estado/Acción), estructura final, coherencia con código, duplicados/archivados, seguridad documental, enlaces, cambios aplicados, próximos pasos (imprescindible/recomendable/opcional/norma futura) y checklist de entrega.

Ver [[feedback_metodo_revision_auditoria]] y el estado vigente en docs/project/11-current-state.md.
