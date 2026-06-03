# 🎓 Bloque académico — entrega del Máster

<p align="center">
  <strong>Documentación de entrega de <code>BuenCholloTech</code></strong><br>
  <em>Máster en Desarrollo con IA · 2025</em>
</p>

---

> 📖 **¿Qué encontrarás aquí?**
> Diez capítulos numerados que explican **qué se ha construido**, **por
> qué se ha construido así**, y **cómo se han aplicado los cuatro grandes
> bloques del máster** sobre un único producto real.
>
> Si lo que buscas es **cómo instalar o ejecutar** BuenCholloTech, eso
> vive en [`docs/project/`](../project/00-index.md). Aquí se explican
> las decisiones, no los comandos.

---

## 🗺️ Recorrido sugerido

Si tienes 5 minutos → lee `01` + `10` (introducción + conclusiones).
Si tienes 15 minutos → añade `04` (arquitectura).
Si tienes una hora → léelo todo.

```
┌─ 01 · Introducción       ─── Qué es y por qué existe
├─ 02 · Objetivos          ─── A dónde queremos llegar
├─ 03 · Análisis funcional ─── Usuarios y flujos reales
├─ 04 · Arquitectura       ─── Decisiones técnicas con ADRs
├─ 05 · Buenas prácticas   ─── SOLID, DRY, KISS, YAGNI aplicados
├─ 06 · Calidad y testing  ─── Pirámide + coverage 100/80/0
├─ 07 · Seguridad          ─── OWASP Top 10 sobre el proyecto
├─ 08 · Uso de IA          ─── Claude Code supervisado
├─ 09 · Limitaciones       ─── Lo que conscientemente NO se hizo
└─ 10 · Conclusiones       ─── Lectura final
```

---

## 📚 Índice completo

| # | Capítulo | Tema | Lectura aprox. |
|---|---|---|---:|
| [01](01-introduccion-del-proyecto.md) | 🌱 **Introducción del proyecto** | Contexto, motivación, problema | ~5 min |
| [02](02-objetivos-y-alcance.md) | 🎯 **Objetivos y alcance** | Qué se entrega y qué queda fuera | ~5 min |
| [03](03-analisis-funcional.md) | 👥 **Análisis funcional** | Usuarios, funcionalidades, flujos | ~10 min |
| [04](04-arquitectura-y-decisiones-tecnicas.md) | 📐 **Arquitectura y decisiones técnicas** | Monolito modular + API Gateway + ADRs | ~15 min |
| [05](05-buenas-practicas-y-principios-de-diseno.md) | ✨ **Buenas prácticas y principios de diseño** | SOLID, DRY, KISS, YAGNI con ejemplos del código | ~15 min |
| [06](06-calidad-testing-y-refactorizacion.md) | 🧪 **Calidad, testing y refactorización** | Pirámide 167 tests · coverage estratégico | ~10 min |
| [07](07-seguridad.md) | 🛡️ **Seguridad** | Security by Design + OWASP Top 10 + hallazgos | ~15 min |
| [08](08-uso-de-ia-en-el-desarrollo.md) | 🤖 **Uso de IA en el desarrollo** | Claude Code, patrones, supervisión humana | ~15 min |
| [09](09-limitaciones-y-mejoras-futuras.md) | 🔭 **Limitaciones y mejoras futuras** | Deuda asumida con justificación | ~10 min |
| [10](10-conclusiones.md) | 🏁 **Conclusiones** | Lectura final | ~5 min |

---

## 🧭 Mapa por bloque del máster

Para que puedas saltar directamente al material relevante de cada
bloque cursado:

<table>
<thead>
<tr><th>Bloque del máster</th><th>Documentos clave</th></tr>
</thead>
<tbody>
<tr>
  <td>📐 <strong>Arquitectura de Software</strong></td>
  <td>
    <a href="04-arquitectura-y-decisiones-tecnicas.md">04 · Arquitectura</a> ·
    <a href="05-buenas-practicas-y-principios-de-diseno.md">05 · Buenas prácticas</a> ·
    <a href="../adr/00-index.md">9 ADRs firmados</a>
  </td>
</tr>
<tr>
  <td>🧪 <strong>Calidad del Software</strong></td>
  <td>
    <a href="06-calidad-testing-y-refactorizacion.md">06 · Calidad y testing</a> ·
    <a href="../project/06-testing-and-quality.md">guía operativa</a> ·
    <a href="../adr/ADR-008-estrategia-calidad-testing.md">ADR-008</a>
  </td>
</tr>
<tr>
  <td>🛡️ <strong>Seguridad</strong></td>
  <td>
    <a href="07-seguridad.md">07 · Seguridad</a> ·
    <a href="../reference/SECURITY_AUDIT.md">auditoría OWASP completa</a> ·
    <a href="../../SECURITY.md">SECURITY.md raíz</a>
  </td>
</tr>
<tr>
  <td>🤖 <strong>Desarrollo con IA</strong></td>
  <td>
    <a href="08-uso-de-ia-en-el-desarrollo.md">08 · Uso de IA</a> ·
    <a href="../adr/ADR-009-uso-de-ia-en-desarrollo.md">ADR-009</a> ·
    <a href="../../CLAUDE.md">CLAUDE.md (configuración del asistente)</a>
  </td>
</tr>
<tr>
  <td>📝 <strong>Cierre / Conclusiones</strong></td>
  <td>
    <a href="01-introduccion-del-proyecto.md">01</a> ·
    <a href="09-limitaciones-y-mejoras-futuras.md">09</a> ·
    <a href="10-conclusiones.md">10</a>
  </td>
</tr>
</tbody>
</table>

---

## 📎 Documentación complementaria

| Carpeta | Para qué |
|---|---|
| [`../adr/`](../adr/00-index.md) | **9 ADRs** firmados y datados (decisiones arquitectónicas) |
| [`../reference/`](../reference/) | Referencias densas: plan de hardening, auditoría OWASP completa, smoke test |
| [`../project/`](../project/00-index.md) | Operativa del repositorio (cómo instalar, ejecutar, desplegar) |
| [`../../PROJECT_STATUS.md`](../../PROJECT_STATUS.md) | Bitácora viva del proyecto con cronología completa de sprints |
| [`../archive/`](../archive/) | Documentación histórica preservada con índice de motivos |

---

<p align="center">
  <em>Pedro Zambudio · Máster en Desarrollo con IA · 2025</em>
</p>
