---
name: feedback_metodo_arquitectura
description: Cómo trabajar al revisar/auditar/proponer arquitectura en BuenChollo — entender antes de proponer, arquitecto senior pragmático, monolito modular + Clean/Hexagonal parciales, criterios, fases, formato ARQ-XX e informe.
metadata:
  type: feedback
---

Modo de trabajo permanente cuando Pedro pida **revisar, auditar o proponer mejoras de arquitectura** en BuenChollo. Complementa [[feedback_metodo_revision_auditoria]]; no aplica a ejecución directa ya acordada.

**Why:** que la arquitectura quede **clara, mantenible, coherente, segura y defendible** ante el tribunal, **adecuada al tamaño real (MVP/TFM)** y sin sobreingeniería. Arquitectura = decisiones duraderas, no dibujar cajas; no existe "la mejor", sino la adecuada al contexto.

**How to apply:**

1. **Entender antes de proponer.** Nunca modificar código al revisar arquitectura. Primero: árbol de carpetas, stack, identificar frontend/backend/BD/auth/servicios externos, organización de módulos, estilo arquitectónico actual, riesgos reales y plan priorizado. Solo modificar si Pedro lo pide tras el análisis.

2. **Rol:** arquitecto senior + revisor de TFM + analista de mantenibilidad/evolución + asesor **pragmático** (no generar capas porque sí). No imponer arquitectura ideal; ayudar a que sea clara, mantenible, defendible y adecuada al tamaño.

3. **Estilo recomendado por defecto** (salvo que el código demuestre otra cosa): **monolito modular** bien organizado, separación por **dominios funcionales**, **Clean Architecture parcial y razonable**, **Hexagonal/Ports&Adapters solo donde aporte valor**. SIN microservicios prematuros, SIN Event-Driven innecesario, SIN arquitectura empresarial exagerada. Coincide con **ADR-001** (monolito modular) y **ADR-002** (API Gateway / separar negocio) ya vigentes — ver [[project_estado_2026-06]].

4. **Criterios de evaluación:**
   - **Modularidad/estructura:** módulos por dominio (auth/users, deals/products, categories, comments/votes/favorites, notifications/alerts, admin, shared); responsabilidades claras; sin dependencias cruzadas innecesarias ni acceso a internos de otro módulo; riesgo de big ball of mud; ¿entra otro dev sin caos?
   - **Separación de responsabilidades:** no mezclar UI, negocio, validación, datos, infraestructura, config, efectos. Componentes/páginas sin lógica de negocio compleja.
   - **Clean con criterio (no dogmático):** dominio protegido; reglas no dependen de framework/UI/router/BD/APIs; dependencias hacia dentro; capa de aplicación/casos de uso; infra con adaptadores; DTOs entrada/salida; modelos de BD no filtrados por toda la app; `env`/`process.env` solo en config/infra. Violaciones típicas: imports de infra en dominio/aplicación, negocio en componentes, acceso a BD desde UI, casos de uso acoplados al framework, entidades internas expuestas en vistas, env vars repartidas.
   - **Hexagonal donde aporte valor:** puerto + adaptador solo si mejora testabilidad/sustitución/claridad (bien: `DealRepository` + `SupabaseDealRepository`; mal: negocio dependiendo directo de Supabase/fetch/localStorage). No puertos para todo.
   - **Casos de uso:** crear/editar/publicar/votar oferta, favorito, alerta, registro/login, validar admin; separados de UI/infra; reciben/devuelven DTOs; errores controlados; no acoplados a Request/Response/router/ORM. Si no hay, valorar si hacen falta o bastan servicios simples (no convertirlos en mini-controladores).
   - **Dominio/VOs:** detectar primitive obsession, reglas dispersas, invariantes sin validar, estados inválidos, entidades anémicas, enums enormes, condicionales en cascada. VOs simples (Email, Precio, Descuento, URL, Estado, Rol, Slug, expiración) **solo si aportan claridad/evitan errores reales**, no ruido.
   - **Comunicación entre módulos:** directa/interfaces/eventos/HTTP; contratos claros; sin dependencias circulares ni acoplamiento excesivo; asincronía solo si aporta; preferir llamada síncrona simple si basta.
   - **Composition Root / DI:** punto claro de construcción de dependencias; config centralizada; inyectar adaptadores en casos de uso donde aporte; evitar singletons globales innecesarios; fakes/in-memory en tests; wiring explícito. No DI compleja si basta composición simple.

5. **Posturas firmes:**
   - **Microservicios:** NO en MVP/TFM; no separar sin autonomía real; evitar monolito distribuido; priorizar monolito modular. Mencionar solo como evolución futura si crece mucho con módulos calientes separables.
   - **Event-Driven:** no forzar. Evaluar valor (oferta publicada/aprobada, alerta coincide, notificación, expiración, voto…); si no hay eventos puede estar bien. Si los hay: hechos en pasado, payload claro, id/timestamp/correlationId/version solo si se justifica.

6. **Transversales:** **Seguridad** (auth, autorización, validación de entrada en servidor, roles user≠admin, secretos fuera del repo, env vars, CORS, rate limiting, errores seguros — Security by Design/Default); **Rendimiento** (paginación, búsquedas, índices, evitar cargas inútiles, caché si tiene sentido, imágenes); **Resiliencia** (errores, timeouts, reintentos en llamadas externas, estados de carga/fallo, fallo parcial no rompe todo); **Datos** (propiedad clara de tablas, migraciones versionadas, persistencia vs dominio si aplica, evitar consultas cruzadas caóticas y DTOs de BD filtrados); **Observabilidad/evolución** (logs útiles, errores trazables, auditoría en acciones admin, versionado de API, migraciones, compatibilidad hacia atrás, rollback/despliegue, feature flags solo si aportan). Nada complejo si no se necesita.

7. **Documentación/ADRs:** comprobar README con arquitectura, diagrama simple, ADRs de decisiones, justificación de estilo y tecnologías, env vars documentadas, flujos y modelo de datos, plan de evolución. Proponer ADRs útiles para defensa (001 monolito modular, 002 separar negocio de UI/infra, 003 auth/autorización, 004 persistencia/acceso a datos, 005 eventos/notificaciones futuras si aplica). BuenChollo ya tiene ADR-001…009 en `docs/adr/`.

8. **Metodología por fases (auditoría de arquitectura):** F1 Entender (árbol, stack, front/back/BD/auth/externos, organización, estilo aparente) → F2 Evaluar (separación, modularidad, aislamiento de dominio, dependencias entre capas, infra, comunicación, datos, evolución) → F3 Comparar con objetivo razonable (monolito modular, dominio funcional, casos de uso, puertos donde haya externos, UI separada, sin micro/EDA prematuros) → F4 Detectar problemas (formato ARQ-XX) → F5 Arquitectura objetivo realista (estilo, carpetas, límites, casos de uso, puertos que sí, qué NO tocar) → F6 Informe.

9. **Formato de problema `[ARQ-XX]`:** Título · Severidad (Crítica/Alta/Media/Baja) · Área (Modularidad/Clean/Hexagonal/Datos/Seguridad/Observabilidad/Comunicación/Testing/Documentación) · Archivo(s)/carpeta(s) · Evidencia · Por qué es problema · Principio del máster relacionado · Impacto actual · Impacto futuro si crece · Propuesta · Riesgo de cambiarlo · Prioridad.

10. **Formato de informe** ("Auditoría de Arquitectura de Software - BuenChollo"): (1) Resumen ejecutivo (estado, cumplimiento Alto/Medio/Bajo, estilo actual, estilo recomendado, riesgos, recomendación); (2) Puntos fuertes; (3) Problemas (ARQ-XX); (4) Comparativa actual vs recomendada (tabla Aspecto/Actual/Recomendado/Prioridad); (5) Estructura de carpetas propuesta (sin inflar); (6) ADRs para la entrega (Título/Contexto/Decisión/Consecuencias/Estado); (7) Plan de acción (imprescindible / recomendable / opcional-futuro / **NO tocar** para evitar sobreingeniería); (8) Defensa ante tribunal (por qué no micro, por qué monolito modular, qué aplica Clean/Hexagonal, cómo evoluciona, decisiones con criterio).

11. **Testing desde arquitectura:** evaluar si permite unit de dominio, casos de uso con fakes, contrato de adaptadores, integración, E2E/smoke de flujos críticos; si dificulta testear, explicar por qué. No auditar testing en profundidad salvo que se pida.

12. **Forma de responder:** clara, directa, ordenada, técnica pero entendible, sin relleno ni inventar; separar hechos confirmados de recomendaciones; señalar incertidumbre; ordenar cambios por impacto y riesgo; priorizar pequeños, seguros y defendibles. Prioridad final: **simplicidad → claridad → mantenibilidad → seguridad → evolución → defensa sólida**. Nunca perfección artificial ni capas sin razón real. Ver [[feedback_no_continuar_con_critico]] y [[feedback_forma_trabajo_iterativa]].
