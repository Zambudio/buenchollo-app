# 🌱 01 · Introducción del proyecto

> **TL;DR** · BuenCholloTech es una plataforma web de comunidad para
> ofertas tecnológicas, construida sobre un **NAS doméstico** con
> arquitectura profesional. Combina curación humana del admin con
> alertas personalizadas, votación comunitaria y publicación
> automatizada a Telegram. Es **producto personal real** y a la vez
> **Trabajo Final del Máster en Desarrollo con IA 2025**.

---

## 🎯 Una frase

> Un Chollometro pequeño, curado, automatizado por IA y desplegado en
> mi NAS de casa.

---

## 🧭 El contexto

En España hay numerosos foros y canales de Telegram dedicados a
"chollos" tecnológicos. Los principales son:

| Tipo | Ejemplo | Problema |
|---|---|---|
| 🏟️ **Comunidad abierta** | Chollometro | El contenido depende del voto colectivo; muchas ofertas son ruido |
| 📺 **Canal vertical** | PCComponentes, MediaMarkt | Sólo una tienda, sin curación |
| 🤖 **Agregadores SEO** | Varios | Copian sin filtro, dependen de adsense |

**BuenCholloTech** se sitúa en un punto intermedio:

```
┌─────────────────────────────────────────────────┐
│  Comunidad abierta                              │
│  (vista pública para usuarios anónimos)         │
│                                                 │
│      + Curación humana del admin                │
│        (publica sólo lo que merece la pena)     │
│                                                 │
│      + Enriquecimiento automático con IA        │
│        (título, copy, imagen, categoría)        │
│                                                 │
│      + Distribución multi-canal                 │
│        (web + Telegram + alertas in-app)        │
└─────────────────────────────────────────────────┘
```

---

## 💡 ¿Por qué este proyecto?

### Motivación personal

El autor mantiene desde hace tiempo un **canal informal de Telegram**
donde comparte ofertas tecnológicas con un grupo reducido de personas.
Lo que empezó como mensajes ocasionales se convirtió en una rutina
manual:

```
🔍 Buscar manualmente en Amazon
✍️  Escribir el texto a mano
🖼️  Sacar la imagen y subirla
🧮  Calcular el descuento
📤  Enviar al canal
```

**Objetivo personal**: automatizar todo ese flujo manual para escalar
a una audiencia mayor y, en su caso, abrirlo como producto real con
dominio propio.

### Motivación académica

El máster cubre cuatro grandes bloques: **arquitectura**, **calidad**,
**seguridad** y **uso de IA**. BuenCholloTech permite ponerlos en
práctica simultáneamente sobre un único producto **real**, no sobre
un ejercicio académico desechable.

Cada decisión técnica está pensada para ser **defendible
profesionalmente**:

- 🗂️ Cada gran decisión vive en un **ADR firmado**.
- 📅 Cada sprint tiene una **bitácora cronológica** en
  [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md).
- 🎯 Cada bloque del máster tiene **un sprint dedicado**: F1–F7
  arquitectura, Q1–Q7 calidad, S1–S7 seguridad.

---

## 🔧 El problema que resuelve

<table>
<thead>
<tr>
  <th>Problema real</th>
  <th>Cómo lo aborda BuenCholloTech</th>
</tr>
</thead>
<tbody>
<tr>
  <td>Las ofertas tech buenas se pierden entre el ruido.</td>
  <td>✅ <strong>Curación humana</strong> del admin: sólo entra lo que el autor considera buen chollo.</td>
</tr>
<tr>
  <td>Buscar chollos manualmente es tedioso.</td>
  <td>🔔 <strong>Alertas personalizadas</strong> que disparan notificaciones in-app al matchear con un chollo nuevo.</td>
</tr>
<tr>
  <td>Reescribir publicaciones para cada canal consume tiempo.</td>
  <td>🤖 <strong>Autocompletado IA desde Amazon</strong>: pega la URL, el sistema genera título, imagen, precio, copy Telegram y ASIN automáticamente.</td>
</tr>
<tr>
  <td>Sin gráfica de precios no se sabe si la oferta es realmente buena.</td>
  <td>📈 Cada chollo enlaza a su <strong>gráfica Keepa</strong> por ASIN.</td>
</tr>
<tr>
  <td>Los agregadores genéricos son spam y no aportan contexto.</td>
  <td>🌡️ <strong>Curación + descripción técnica enriquecida + temperatura por votos comunitarios</strong>.</td>
</tr>
</tbody>
</table>

---

## 📦 Alcance del proyecto

El TFM cubre un **MVP funcional en producción** desplegado en NAS
Synology:

✅ Frontend público con feed, búsqueda y detalle de chollos
✅ Autenticación con **Google OAuth** (Supabase Auth)
✅ Funciones de usuario: votar, comentar, favoritos, alertas, notificaciones
✅ Panel administrativo con CRUD, autocomplete Amazon, publicación a Telegram
✅ Pipeline CI/CD con tests automáticos y auditoría de seguridad
✅ Documentación completa (la que estás leyendo)

> 🔭 **Lo que queda fuera del MVP** está documentado en
> [`09 · Limitaciones y mejoras futuras`](09-limitaciones-y-mejoras-futuras.md)
> con justificación de por qué se ha aplazado cada cosa.

---

## 🗺️ Cómo seguir leyendo

Si te interesa…

- **El producto y sus flujos** → [`03 · Análisis funcional`](03-analisis-funcional.md)
- **Las decisiones técnicas** → [`04 · Arquitectura`](04-arquitectura-y-decisiones-tecnicas.md) + [ADRs](../adr/00-index.md)
- **Cómo se garantiza la calidad** → [`06 · Calidad y testing`](06-calidad-testing-y-refactorizacion.md)
- **El papel de la IA en el desarrollo** → [`08 · Uso de IA`](08-uso-de-ia-en-el-desarrollo.md)
- **Cómo se ha aplicado seguridad** → [`07 · Seguridad`](07-seguridad.md)
- **Una versión rápida** → [`10 · Conclusiones`](10-conclusiones.md)

---

<p align="center">
  <a href="00-index.md">← Volver al índice</a> ·
  <a href="02-objetivos-y-alcance.md">Siguiente: Objetivos y alcance →</a>
</p>
