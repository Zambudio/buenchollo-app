# 10 — Conclusiones

## Lo que se ha aprendido

El recorrido del proyecto cubre los cuatro grandes bloques del Máster
en Desarrollo con IA 2025 sobre un único producto real. Algunas
lecciones concretas, no genéricas, que el desarrollo de
BuenCholloTech ha consolidado:

**Sobre arquitectura.** El monolito modular sigue siendo la elección
correcta para el 80% de los proyectos. Microservicios es una opción
de escala, no un patrón de calidad. La Clean Architecture pragmática
(routers HTTP-only, casos de uso aislados, repositorios como único
acceso a BD) entrega los beneficios de la separación sin el coste de
un purismo dogmático. El proyecto ha demostrado en sus sprints que
extraer un servicio (`DealService`), formalizar un Protocol
(`ProductPreviewProvider`) o partir un router es barato cuando la
estructura está sana — y es esa "baratura del cambio" lo que
realmente define un buen diseño.

**Sobre calidad.** Coverage 100% global es una métrica de vanidad;
coverage 90%+ en la lógica de negocio es defensa real. La pirámide
de testing no es un esquema decorativo: cada nivel resuelve un
problema distinto. Husky con pre-commit/pre-push es la diferencia
entre "el código rompe en main" y "el código no llega a `git push`".
Las métricas accionables con umbrales verde/amarillo/rojo son el
puente entre "lo medimos" y "actuamos cuando algo se degrada".

**Sobre seguridad.** OWASP Top 10 funciona como check-list real, no
como teoría. La mayoría de los hallazgos del proyecto eran de
severidad media (CORS reflection, ausencia de Security Headers,
SSRF parcial) y se resolvieron con cambios pequeños y bien
justificados. No hizo falta WAF ni DAST automatizado para llegar a
un nivel defendible. La auditoría documentada — con cómo se
explota, cuál es el impacto y cuál es el cambio mínimo — es el
documento que da valor, no el "scan ZAP" sin contexto.

**Sobre IA en el desarrollo.** La IA acelera, no sustituye. La
estrategia que funciona es **auditorías por módulo con prompts
extensos**: rol claro, alcance acotado, formato de informe
estandarizado, plan de acción aprobado por humano antes de
implementar. Sin la supervisión humana en cada commit, la IA tiende a
sobreingeniería (factories, builders, abstracciones especulativas).
Con supervisión, multiplica por 5-10 la velocidad de auditoría y
documentación. Tres líneas defensivas (tests automáticos + revisión
humana + auditorías cruzadas) cubren los riesgos identificados.

## Qué demuestra el proyecto

| Bloque del máster | Cómo se demuestra en BuenCholloTech |
|---|---|
| **Arquitectura de software** | 9 ADRs firmados, Clean Architecture pragmática verificable módulo por módulo, separación de responsabilidades aplicada con ejemplos concretos. |
| **Calidad del software** | Pirámide de 167 tests (137 unit + 13 integration + 8 E2E), coverage estratégico 100/80/0 con threshold automático, métricas accionables Tier 1/2/3, quality gates Husky + CI. |
| **Seguridad** | Auditoría OWASP Top 10 completa con 10 hallazgos documentados, 6 fixes implementados, Security Headers + rate limiting + audit log + RLS + SSRF allowlist + CI con `pip-audit` + `npm audit` + `gitleaks`. |
| **Desarrollo con IA** | Uso supervisado de Claude Code con `CLAUDE.md` como configuración persistente, auditorías por módulo, validación obligatoria por tests + revisión humana, ADR-009 que formaliza la decisión. |
| **Buenas prácticas y diseño** | SOLID/DRY/KISS/YAGNI aplicados con ejemplos del código real, refactorizaciones documentadas, antipatrones evitados, deuda asumida con justificación. |
| **DevOps básico** | CI con 4 jobs (backend, frontend, e2e, security-audit), Dependabot semanal con grupos, despliegue Docker en NAS Synology, scheduler integrado, migraciones Alembic auto-aplicadas. |

## Cómo se han aplicado los contenidos del máster

Cada sprint del proyecto se ha alineado deliberadamente con un módulo
del máster:

- **Sprint F1–F7 (hardening arquitectónico)** → módulo de
  Arquitectura. Documentación, Alembic, request_id, rate limiting,
  audit log, health checks, Sentry, API versionada, frontend
  pro-grade, CI/CD, cierre con SMOKE_TEST.

- **Sprint Q1–Q7 (calidad)** → módulo de Calidad del software.
  Vitest + Testing Library, unit tests CORE, integration tests,
  Husky, Playwright + 8 E2E, CI con coverage, documento QUALITY.md.

- **Sprint S1–S7 (seguridad)** → módulo de Seguridad. Auditoría
  OWASP completa, 6 fixes de severidad media, Security Headers,
  CORS, SSRF allowlist, audit security en CI, documento SECURITY.md.

- **Sprint de documentación (este)** → integración final con todos
  los módulos. Reorganización en `docs/project/` operativo y
  `docs/master/` para defensa, 9 ADRs firmados, README dual.

- **Uso de IA transversal a todos los sprints** → módulo de
  Desarrollo con IA. Claude Code como asistente principal,
  documentado en ADR-009 y en este capítulo 08 del bloque master.

## Qué valor tiene el proyecto

### Valor académico

- Un producto **completo y desplegado**, no un prototipo desechable.
- Decisiones técnicas **defendibles ante tribunal**, con ADRs
  firmados, métricas medibles y deuda asumida documentada.
- Aplicación práctica de los cuatro grandes bloques del máster
  sobre un único producto, lo que permite mostrar interrelaciones
  reales (la decisión de arquitectura afecta a la estrategia de
  testing, la estrategia de testing facilita el refactor seguro, el
  refactor seguro permite cerrar deuda de seguridad...).

### Valor profesional

- Demuestra capacidad de llevar un producto desde idea hasta
  producción **con criterio profesional senior**: lockfiles
  versionados, gates de calidad locales y en CI, auditorías OWASP,
  observabilidad con Sentry, rollback documentado.
- Código real publicado en GitHub bajo el repositorio
  `Zambudio/buenchollo-app`, **accesible a empleadores potenciales**.

### Valor de producto

- BuenCholloTech es **funcional y útil**: cada chollo publicado en
  el canal de Telegram representa minutos ahorrados al autor y a sus
  seguidores frente al flujo manual previo.
- La plataforma está **diseñada para escalar** sin reescritura:
  añadir un nuevo proveedor de productos, un nuevo canal de
  distribución o un nuevo tipo de notificación son cambios
  pequeños que no tocan el núcleo.

## Pasos futuros razonables

Documentados en detalle en
[`09-limitaciones-y-mejoras-futuras.md`](09-limitaciones-y-mejoras-futuras.md).
Lo más relevante por horizonte:

**Corto plazo (1–2 sprints)**:
- Email para notificaciones críticas con Resend.
- Refactor de `admin.chollos.tsx` con tests previos.
- Marcado individual de notificaciones.

**Medio plazo**:
- PWA con push notifications.
- Búsqueda semántica con embeddings.
- Vista de tienda y sistema de niveles.

**Largo plazo (si el producto valida tracción)**:
- App móvil con React Native + Expo.
- Multi-administrador y panel de moderación.
- Internacionalización.
- Monetización (afiliados ampliados, suscripción Premium).

## Reflexión final

> No basta con que la web funcione. Tiene que resistir uso malicioso,
> errores del usuario, abuso de APIs, exposición de datos,
> configuraciones inseguras y dependencias vulnerables.

Esta frase apareció textualmente en el prompt de la auditoría de
seguridad y se ha convertido en el principio de fondo del proyecto.
Aplica también a las otras áreas:

- "No basta con que el código compile. Tiene que poder cambiarse
  sin miedo."
- "No basta con que pase los tests. Los tests tienen que probar
  algo real."
- "No basta con que la IA genere código. El humano tiene que
  entenderlo y poder defenderlo."

BuenCholloTech se entrega como un proyecto que cumple esos cuatro
"no basta": funciona, se puede cambiar, está testado con propósito y
ha sido construido con IA bajo supervisión humana documentada.

El siguiente paso lo decide el tribunal.

---

*Pedro Zambudio · Máster en Desarrollo con IA 2025 · Junio 2026.*
