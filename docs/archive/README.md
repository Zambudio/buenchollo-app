# 🗄️ Archivo histórico

> **TL;DR** · Documentos antiguos preservados sin eliminar. Cada
> entrada indica **por qué se archivó** y **dónde vive ahora la
> información viva**. Si llegaste aquí buscando algo concreto, usa
> la tabla del final.

---

## 📜 Política del archivo

> 🔴 **No se elimina** documentación útil. Si está aquí, es porque
> algún día fue válida y aporta contexto histórico.

> 🔴 **No se actualiza** lo que está aquí. Es congelado tal cual
> estaba al archivarse. Para información actual, ir al destino
> indicado en cada entrada.

> 🔴 Cuando algo de aquí **entra en contradicción con el código
> actual** o con la documentación viva, **prevalece la documentación
> viva**.

---

## 📚 Inventario

### 🕰️ Documentos histórico-cronológicos (no se fusionaron)

| Documento | Fecha | Motivo de archivo |
|---|---|---|
| 📋 [`TODO.md`](TODO.md) | 2026-05-19 | Roadmap superado. La mayoría de tareas (CI/CD, Alembic, votos, favoritos, Telegram migrado) ya estaban hechas al cerrar el sprint F1–F7. Estado actual del proyecto: [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md). |
| 📝 [`CambiosAlertasCodex.md`](CambiosAlertasCodex.md) | 2026-05-24 | Bitácora detallada de un único sprint (alertas + notificaciones + home feed infinito). Valor histórico — describe decisiones concretas tomadas con Codex como asistente. Documentación viva equivalente en [`docs/master/03-…`](../master/03-analisis-funcional.md). |

### 🔄 Documentos fusionados en la nueva estructura

<table>
<thead>
<tr><th>Documento</th><th>Movido por</th><th>Información viva en</th></tr>
</thead>
<tbody>
<tr>
  <td>📥 <a href="SETUP.md">SETUP.md</a></td>
  <td>C1 (sprint documentación)</td>
  <td><a href="../project/02-installation-and-setup.md">docs/project/02-installation-and-setup.md</a> — corregido (npm, no pnpm; puerto 8080)</td>
</tr>
<tr>
  <td>🚀 <a href="LAUNCH_CHECKLIST.md">LAUNCH_CHECKLIST.md</a></td>
  <td>C1</td>
  <td><a href="../project/08-deployment.md">docs/project/08-deployment.md</a> — actualizado (slowapi ya integrado)</td>
</tr>
<tr>
  <td>🔐 <a href="SUPABASE_SETUP.md">SUPABASE_SETUP.md</a></td>
  <td>C1</td>
  <td><a href="../project/02-installation-and-setup.md">project/02 §4 Supabase</a> + <a href="../project/08-deployment.md">project/08</a></td>
</tr>
<tr>
  <td>🎨 <a href="UI_SYSTEM.md">UI_SYSTEM.md</a></td>
  <td>C1</td>
  <td><a href="../project/03-project-structure.md">docs/project/03 §Sistema de UI</a></td>
</tr>
<tr>
  <td>🐳 <a href="DEPLOY_NAS.md">DEPLOY_NAS.md</a></td>
  <td>C1 (estaba en buenchollo-api/)</td>
  <td><a href="../project/08-deployment.md">docs/project/08-deployment.md</a></td>
</tr>
<tr>
  <td>🏗️ <a href="NAS_DEPLOYMENT_ARCHITECTURE.md">NAS_DEPLOYMENT_ARCHITECTURE.md</a></td>
  <td>C1 (estaba en buenchollo-api/docs/)</td>
  <td><a href="../project/08-deployment.md">docs/project/08 §Arquitectura actual</a> — actualizado (python:3.11-slim, no 3.12)</td>
</tr>
</tbody>
</table>

### 🔀 Documentos divididos entre /project y /master

<table>
<thead>
<tr><th>Documento</th><th>Información viva en</th></tr>
</thead>
<tbody>
<tr>
  <td>🧪 <a href="QUALITY.md">QUALITY.md</a></td>
  <td>
    • Operativa → <a href="../project/06-testing-and-quality.md">project/06</a><br>
    • Académica → <a href="../master/06-calidad-testing-y-refactorizacion.md">master/06</a><br>
    • Formalización como ADR → <a href="../adr/ADR-008-estrategia-calidad-testing.md">ADR-008</a>
  </td>
</tr>
<tr>
  <td>🛡️ <a href="SECURITY-old.md">SECURITY-old.md</a></td>
  <td>
    • Política breve en raíz → <a href="../../SECURITY.md">SECURITY.md</a><br>
    • Operativa → <a href="../project/07-security.md">project/07</a><br>
    • Académica → <a href="../master/07-seguridad.md">master/07</a><br>
    • Referencia → <a href="../reference/SECURITY_AUDIT.md">reference/SECURITY_AUDIT.md</a>
  </td>
</tr>
</tbody>
</table>

---

## 🎯 Si llegaste aquí buscando algo

| Buscas... | Ve a... |
|---|---|
| 📥 **Cómo instalar** | [`project/02-installation-and-setup.md`](../project/02-installation-and-setup.md) |
| 🚀 **Cómo desplegar al NAS** | [`project/08-deployment.md`](../project/08-deployment.md) |
| 🔐 **Configuración Supabase** | [`project/02 §4`](../project/02-installation-and-setup.md) |
| 🧪 **Estrategia de testing** | [`project/06`](../project/06-testing-and-quality.md) o [`master/06`](../master/06-calidad-testing-y-refactorizacion.md) |
| 🛡️ **Seguridad** | [`project/07`](../project/07-security.md) o [`master/07`](../master/07-seguridad.md) |
| 📊 **Estado actual del proyecto** | [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md) |
| 🔍 **Auditoría OWASP** | [`reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md) |
| 🎨 **Sistema de UI** | [`project/03`](../project/03-project-structure.md) |
| 🗺️ **Roadmap** | No existe roadmap "vivo". Mejoras futuras → [`master/09`](../master/09-limitaciones-y-mejoras-futuras.md) |

---

> 📅 *Archivo creado el 2026-06-03 durante el sprint de reorganización
> documental. Si el proyecto evoluciona y un documento aquí guardado
> se reactivara, hay que sacarlo de archive y actualizarlo en su
> nueva ubicación.*

---

<p align="center">
  <a href="../project/00-index.md">📘 Operativa</a> ·
  <a href="../master/00-index.md">🎓 Bloque académico</a> ·
  <a href="../adr/00-index.md">📋 ADRs</a> ·
  <a href="../reference/">📚 Referencias</a>
</p>
