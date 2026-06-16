---
name: feedback_recordar_deuda_tecnica
description: Recordar la deuda técnica pendiente cada vez que se cambia de tarea.
metadata:
  type: feedback
---

Al **cambiar de tarea** (cuando se cierra algo y se pasa a otra cosa), recordar brevemente
a Pedro que hay deuda técnica pendiente y apuntar a [`docs/project/10-technical-debt.md`].

**Why:** quiere corregir la deuda sin enredarse con los pormenores ahora; necesita tenerla
presente al retomar el proyecto tras el TFM, sin que se olvide entre tareas.

**How to apply:** no interrumpir a mitad de una tarea; el recordatorio va en la transición
entre una tarea terminada y la siguiente. Mantener el registro vivo: al cerrar un item,
borrarlo de `docs/project/10-technical-debt.md` y anotar el cierre (fecha + commit) en
`PROJECT_STATUS.md`. Ver [[buenchollo-final-review-2026-06]] para el detalle de la deuda
detectada en la auditoría final.
