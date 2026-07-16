---
description: auditar-arquitectura
---

Audita el proyecto actual antes de seguir desarrollando.

Objetivo:
Comprobar si la estructura actual respeta Clean Architecture, monolito modular, buenas prácticas, seguridad, testing y mantenibilidad.

No modifiques código todavía.

Revisa:
- estructura de carpetas,
- separación dominio/aplicación/infraestructura/API,
- routers FastAPI,
- schemas Pydantic,
- modelos SQLAlchemy,
- migraciones Alembic,
- servicios y casos de uso,
- dependencias entre módulos,
- frontend React/TypeScript,
- servicios API del frontend,
- configuración,
- .env.example,
- seguridad,
- testing,
- README y documentación.

Devuelve el informe con este formato:

# Auditoría técnica - BuenCholloTech

## 1. Resumen ejecutivo
Indica si la base está sana o si conviene parar y reforzar cimientos.

## 2. Puntos correctos
Lista lo que está bien implementado.

## 3. Problemas detectados
Para cada problema indica:
- descripción,
- archivo o carpeta afectada,
- riesgo,
- prioridad: Alta / Media / Baja,
- propuesta de solución.

## 4. Code smells
Busca:
- lógica de negocio en routers,
- modelos mezclados con schemas,
- funciones largas,
- duplicación,
- imports cruzados,
- acoplamiento excesivo,
- nombres poco claros,
- hardcoding,
- sobreingeniería.

## 5. Seguridad
Revisa:
- secretos,
- variables de entorno,
- CORS,
- errores expuestos,
- validación,
- autenticación/autorización,
- riesgos OWASP básicos.

## 6. Testing
Indica qué tests existen, qué falta y qué sería lo mínimo recomendable.

## 7. Plan de refactorización
Propón fases pequeñas:
- Fase 1: crítico,
- Fase 2: arquitectura,
- Fase 3: testing,
- Fase 4: documentación.

## 8. Decisión recomendada
Indica si debemos:
A) seguir desarrollando,
B) parar y refactorizar cimientos,
C) corregir solo puntos concretos y continuar.

No apliques cambios hasta que te lo confirme.