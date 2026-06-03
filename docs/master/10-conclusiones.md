# 🏁 10 · Conclusiones

> **TL;DR** · BuenCholloTech demuestra los cuatro grandes bloques del
> máster sobre un único producto real, desplegado y en uso. Cada
> decisión está documentada, cada test contribuye, cada hallazgo de
> seguridad está resuelto o aceptado con justificación, y el uso de
> IA está supervisado y limitado. El siguiente paso lo decide el
> futuro del propio producto.

---

## 🎓 Lo que se ha aprendido

> _Cuatro lecciones concretas, no genéricas, que el desarrollo de
> BuenCholloTech ha consolidado._

### 📐 Sobre arquitectura

> El monolito modular sigue siendo la elección correcta para el 80% de
> los proyectos. Microservicios es una opción de escala, no un patrón
> de calidad. La **Clean Architecture pragmática** (routers HTTP-only,
> casos de uso aislados, repositorios como único acceso a BD) entrega
> los beneficios de la separación sin el coste de un purismo dogmático.

El proyecto ha demostrado en sus sprints que **extraer un servicio**
(`DealService`), **formalizar un Protocol** (`ProductPreviewProvider`)
o **partir un router** es barato cuando la estructura está sana — y
es esa _baratura del cambio_ lo que realmente define un buen diseño.

### 🧪 Sobre calidad

> Coverage 100% global es una métrica de vanidad; coverage 90%+ en la
> lógica de negocio es defensa real.

- La **pirámide de testing** no es un esquema decorativo: cada nivel
  resuelve un problema distinto
- **Husky con pre-commit/pre-push** es la diferencia entre _"el código
  rompe en main"_ y _"el código no llega a git push"_
- Las **métricas accionables** con umbrales verde/amarillo/rojo son el
  puente entre _"lo medimos"_ y _"actuamos cuando algo se degrada"_

### 🛡️ Sobre seguridad

> OWASP Top 10 funciona como check-list real, no como teoría.

La mayoría de los hallazgos del proyecto eran de severidad media
(CORS reflection, ausencia de Security Headers, SSRF parcial) y se
resolvieron con **cambios pequeños y bien justificados**. No hizo
falta WAF ni DAST automatizado para llegar a un nivel sólido.

> La **auditoría documentada** — con cómo se explota, cuál es el
> impacto y cuál es el cambio mínimo — es el documento que da valor,
> no el _"scan ZAP"_ sin contexto.

### 🤖 Sobre IA en el desarrollo

> La IA acelera, no sustituye.

La estrategia que funciona es **auditorías por módulo con prompts
extensos**: rol claro, alcance acotado, formato de informe
estandarizado, plan de acción aprobado por humano antes de
implementar.

| Sin supervisión | Con supervisión |
|---|---|
| ❌ Sobreingeniería (factories, builders, abstracciones especulativas) | ✅ Velocidad multiplicada por 5–10 en auditorías y documentación |

**Tres líneas defensivas** (tests automáticos + revisión humana +
auditorías cruzadas) cubren los riesgos identificados.

---

## 🎯 Qué demuestra el proyecto

<table>
<thead>
<tr><th>Bloque del máster</th><th>Cómo se demuestra en BuenCholloTech</th></tr>
</thead>
<tbody>
<tr>
  <td>📐 <strong>Arquitectura de software</strong></td>
  <td>9 ADRs firmados · Clean Architecture pragmática verificable módulo por módulo · separación de responsabilidades con ejemplos concretos</td>
</tr>
<tr>
  <td>🧪 <strong>Calidad del software</strong></td>
  <td>Pirámide de 167 tests (137 unit + 13 integration + 8 E2E) · coverage estratégico 100/80/0 con threshold automático · métricas accionables Tier 1/2/3 · quality gates Husky + CI</td>
</tr>
<tr>
  <td>🛡️ <strong>Seguridad</strong></td>
  <td>Auditoría OWASP Top 10 completa con 10 hallazgos documentados · 6 fixes implementados · Security Headers · rate limiting · audit log · RLS · SSRF allowlist · CI con <code>pip-audit</code> + <code>npm audit</code> + <code>gitleaks</code></td>
</tr>
<tr>
  <td>🤖 <strong>Desarrollo con IA</strong></td>
  <td>Uso supervisado de Claude Code con <code>CLAUDE.md</code> persistente · auditorías por módulo · validación obligatoria por tests + revisión humana · ADR-009</td>
</tr>
<tr>
  <td>✨ <strong>Buenas prácticas y diseño</strong></td>
  <td>SOLID/DRY/KISS/YAGNI aplicados con ejemplos del código real · refactorizaciones documentadas · antipatrones evitados · deuda asumida con justificación</td>
</tr>
<tr>
  <td>🚀 <strong>DevOps básico</strong></td>
  <td>CI con 4 jobs · Dependabot semanal con grupos · despliegue Docker en NAS · scheduler integrado · migraciones Alembic auto-aplicadas</td>
</tr>
</tbody>
</table>

---

## 🗺️ Cómo se han aplicado los contenidos del máster

Cada sprint del proyecto se ha alineado deliberadamente con un módulo
del máster:

```
┌──────────────────────────────────────────────────────────────┐
│  Sprint F1–F7  →  Módulo de Arquitectura                     │
│  (hardening · Alembic · request_id · rate limit · audit · …) │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Sprint Q1–Q7  →  Módulo de Calidad del software             │
│  (Vitest · Testing Library · Playwright · Husky · CI · …)    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Sprint S1–S7  →  Módulo de Seguridad                        │
│  (OWASP · 6 fixes · Security Headers · CORS · SSRF · …)      │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Sprint docs   →  Integración final con todos los módulos    │
│  (docs/project · docs/master · 9 ADRs · README dual)         │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Uso de IA transversal  →  Módulo de Desarrollo con IA       │
│  (Claude Code · CLAUDE.md · auditorías por módulo · ADR-009) │
└──────────────────────────────────────────────────────────────┘
```

---

## 💎 Qué valor tiene el proyecto

### 🎓 Valor académico

- Un producto **completo y desplegado**, no un prototipo desechable
- Decisiones técnicas **explicadas y documentadas**, con ADRs firmados
- Aplicación práctica de los cuatro grandes bloques del máster sobre
  un único producto

### 💼 Valor profesional

- Demuestra capacidad de llevar un producto desde idea hasta
  producción **con criterio profesional senior**: lockfiles
  versionados, gates de calidad locales y en CI, auditorías OWASP,
  observabilidad con Sentry, rollback documentado
- Código real publicado en GitHub bajo el repositorio
  `Zambudio/buenchollo-app`, **accesible a empleadores potenciales**

### 🚀 Valor de producto

- BuenCholloTech es **funcional y útil**: cada chollo publicado en el
  canal de Telegram representa minutos ahorrados al autor y a sus
  seguidores frente al flujo manual previo
- La plataforma está **diseñada para escalar** sin reescritura:
  añadir un nuevo proveedor de productos, un nuevo canal de
  distribución o un nuevo tipo de notificación son cambios pequeños
  que no tocan el núcleo

---

## 🌅 Pasos futuros razonables

> Documentados en detalle en
> [`09 · Limitaciones y mejoras futuras`](09-limitaciones-y-mejoras-futuras.md).
> Lo más relevante por horizonte:

| Horizonte | Mejoras priorizadas |
|---|---|
| 📅 **Corto plazo** (1–2 sprints) | 📧 Email para notificaciones · 🪨 Refactor de `admin.chollos.tsx` · ✅ Marcado individual de notificaciones |
| 📆 **Medio plazo** | 🔔 PWA con push · 🧠 Búsqueda semántica · 🏪 Vista de tienda · 🏆 Sistema de niveles |
| 🌅 **Largo plazo** | 📱 App móvil React Native · 👥 Multi-administrador · 🌍 Internacionalización · 💰 Monetización |

---

## 💬 Reflexión final

> _No basta con que la web funcione. Tiene que resistir uso malicioso,
> errores del usuario, abuso de APIs, exposición de datos,
> configuraciones inseguras y dependencias vulnerables._

Esta frase apareció textualmente en el prompt de la auditoría de
seguridad y se convirtió en el principio de fondo del proyecto.
Aplica también a las otras áreas:

```
🏗️  "No basta con que el código compile.
     Tiene que poder cambiarse sin miedo."

🧪  "No basta con que pase los tests.
     Los tests tienen que probar algo real."

🤖  "No basta con que la IA genere código.
     El humano tiene que entenderlo y poder explicarlo."
```

BuenCholloTech se entrega como un proyecto que cumple esos cuatro
"no basta":

- ✅ **Funciona**
- ✅ **Se puede cambiar**
- ✅ **Está testado con propósito**
- ✅ **Ha sido construido con IA bajo supervisión humana documentada**

---

<p align="center">
  <strong>Pedro Zambudio</strong><br>
  Máster en Desarrollo con IA · 2025
</p>

<p align="center">
  <a href="09-limitaciones-y-mejoras-futuras.md">← Anterior: Limitaciones y mejoras</a> ·
  <a href="00-index.md">Índice</a>
</p>
