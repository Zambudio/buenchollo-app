---
description: crear-feature-siguiendo-clean-architecture
---

Implementa una nueva funcionalidad siguiendo la arquitectura del proyecto BuenCholloTech.

Antes de escribir código:
1. Analiza el requisito.
2. Identifica el módulo afectado.
3. Propón el diseño.
4. Lista archivos a crear o modificar.
5. Espera confirmación si el cambio es grande.

Reglas:
- No meter lógica de negocio en routers.
- Crear caso de uso en application cuando haya lógica.
- Usar schemas Pydantic para entrada/salida.
- Usar repositorios o adapters en infrastructure.
- Mantener dominio libre de frameworks.
- Añadir tests si hay lógica relevante.
- Actualizar README o documentación si cambia el uso del sistema.
- No romper endpoints existentes.

Al finalizar:
- resume cambios,
- indica cómo probar,
- indica comandos ejecutados,
- indica riesgos o pendientes.