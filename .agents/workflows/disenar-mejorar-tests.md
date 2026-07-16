---
description: disenar-mejorar-tests
---

Diseña o mejora tests siguiendo la pirámide de testing.

Prioridad:
1. Tests unitarios para lógica pura.
2. Tests de integración para endpoints y repositorios.
3. E2E solo para flujos críticos.

Reglas:
- Tests rápidos.
- Tests aislados.
- Tests repetibles.
- No depender de servicios externos reales.
- Mockear Amazon, Telegram y APIs externas.
- Usar datos de prueba claros.
- No testear detalles internos innecesarios.
- Testear comportamiento esperado.

Devuelve:
- tests existentes,
- tests faltantes,
- propuesta mínima para MVP,
- archivos a crear,
- comandos para ejecutar.