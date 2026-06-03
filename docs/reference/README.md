# 📚 Referencias técnicas

> **TL;DR** · Documentos densos que no son ni operativa diaria
> ([`../project/`](../project/00-index.md)) ni explicación académica
> ([`../master/`](../master/00-index.md)), pero que mantienen valor
> como **referencia técnica** y se enlazan desde ambos bloques.

---

## 📖 Documentos

<table>
<thead>
<tr><th>Documento</th><th>Contenido</th><th>Estado</th></tr>
</thead>
<tbody>
<tr>
  <td><a href="PLAN_ARQUITECTURA.md">📐 PLAN_ARQUITECTURA.md</a></td>
  <td>Plan vivo del sprint de hardening arquitectónico F1–F7 con las 30 tareas completadas</td>
  <td>✅ Cerrado · referencia histórica</td>
</tr>
<tr>
  <td><a href="SECURITY_AUDIT.md">🛡️ SECURITY_AUDIT.md</a></td>
  <td>Auditoría OWASP Top 10 completa con 10 hallazgos priorizados (SEC-01 a SEC-10) y plan de fix detallado</td>
  <td>✅ Resuelto en sprint S1–S7</td>
</tr>
<tr>
  <td><a href="SMOKE_TEST.md">🧪 SMOKE_TEST.md</a></td>
  <td>Checklist manual exhaustivo pre-release (10 secciones · ~50 puntos)</td>
  <td>✅ Vigente · ejecutar antes de cada tag</td>
</tr>
</tbody>
</table>

---

## 🎯 Cuándo consultar cada documento

### 📐 `PLAN_ARQUITECTURA.md`

> 💡 Si quieres **entender cómo se llevó al proyecto al estado
> actual** (sprint completo de hardening) o si vas a **planificar un
> sprint similar** en otro proyecto y quieres ver cómo se estructuró.

### 🛡️ `SECURITY_AUDIT.md`

> 💡 Si vas a hacer una **auditoría OWASP de tu propio proyecto**,
> este sirve como **plantilla extensa** con el formato de cada
> hallazgo:
>
> - 🚨 Severidad
> - 🏷️ Categoría OWASP
> - 📁 Archivos afectados
> - 🔍 Evidencia
> - ⚠️ Riesgo
> - 🦹 Cómo se explota
> - 💥 Impacto
> - 🔧 Recomendación
> - ✏️ Cambio mínimo
> - ✅ Validación

También es el insumo del que se destila
[`../master/07-seguridad.md`](../master/07-seguridad.md).

### 🧪 `SMOKE_TEST.md`

> ⚠️ **Antes de cada release**. Es el checklist que cubre los flujos
> críticos que los tests E2E automatizados no pueden cubrir:
>
> - 🔐 Interacciones con OAuth de Google real
> - ✈️ Publicación a Telegram con copy generado
> - 📋 Audit log post-acción
> - Etc.

---

## 💡 Por qué este directorio existe

> La documentación operativa de [`../project/`](../project/00-index.md)
> debe ser **corta y directa**: comandos, ejemplos, tabla de errores
> comunes.
>
> La documentación académica de
> [`../master/`](../master/00-index.md) debe ser **explicativa y
> justificativa**: por qué se tomó cada decisión.
>
> Pero algunos documentos técnicos son **largos y densos sin caber en
> ninguno de los dos modos**: una auditoría OWASP detallada de 500
> líneas no es operativa diaria ni es el formato académico final.
>
> 📦 Vive aquí, en `reference/`, y se enlaza desde donde corresponda.

---

<p align="center">
  <a href="../project/00-index.md">📘 Operativa</a> ·
  <a href="../master/00-index.md">🎓 Bloque académico</a> ·
  <a href="../adr/00-index.md">📋 ADRs</a> ·
  <a href="../archive/">🗄️ Histórico</a>
</p>
