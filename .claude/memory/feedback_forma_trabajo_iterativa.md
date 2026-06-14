---
name: feedback-forma-trabajo-iterativa
description: Pedro trabaja tarea-a-tarea con verificación manual y commit antes de pasar al siguiente punto. No batchear.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0e88ac1a-ad2a-46ab-8156-7723049be7b5
---

Forma de trabajar establecida en BuenChollo:

**Ciclo por tarea:** modificar → verificar (manual + tsc/pytest) → commit + push
→ marcar la tarea como completada en el plan → preguntar antes de pasar a la
siguiente.

**Why:** Pedro quiere control fino y poder probar la app entre cambios. Confirmó
varias veces que no quiere que se acumulen cambios sin probar. Comentario
literal: "primero modificamos, después verificamos probando, luego commit, se
marca la tarea y a por la siguiente".

**How to apply:**
- No agrupar varias tareas distintas en un commit (excepto micro-cambios
  triviales del mismo ámbito que sí se cierran juntos).
- **Confianza por defecto**: Pedro autoriza a avanzar sin pedir
  confirmación previa cuando la tarea ya está en el plan y es de bajo
  riesgo (docs, refactor mecánico, `git mv`, añadir tests, etc.). Quote:
  "para estas cosas ni preguntes, confío en ti como ingeniero senior".
- **Avisar antes de probar** sólo cuando el cambio afecte al runtime
  (código del backend que requiere reiniciar contenedor, cambios de schema,
  cambios visibles del frontend que necesite tocar el navegador). Decir
  qué probar y por qué.
- Cuando una tarea afecte a backend, recordarle a Pedro que reinicie el
  contenedor antes de probar.
- Mantener vivo el plan (PROJECT_STATUS.md o el plan documentado en docs/)
  marcando con [x] cada tarea cerrada.
- Tras cerrar una tarea, **anunciar brevemente la siguiente y arrancarla
  directamente** salvo que el usuario haya dicho explícitamente "para".
