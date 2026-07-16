---
description: refactorizar-sin-romper-funcionalidad
---

Refactoriza el código indicado sin cambiar el comportamiento funcional.

Antes de modificar:
1. Explica qué problema tiene el código actual.
2. Indica qué principio incumple: SRP, DIP, DRY, KISS, Clean Architecture, etc.
3. Propón una refactorización pequeña y segura.
4. Identifica tests afectados.

Reglas:
- No hacer refactor masivo innecesario.
- No cambiar nombres públicos de endpoints salvo que se apruebe.
- No cambiar contratos API sin avisar.
- Mantener compatibilidad.
- Ejecutar o proponer tests.
- El resultado debe ser más simple, no más complejo.

Al terminar:
- lista archivos modificados,
- explica qué ha mejorado,
- indica cómo validar que no se ha roto nada.