# 👥 03 · Análisis funcional

> **TL;DR** · Tres perfiles de usuario (anónimo, registrado, admin) con
> permisos crecientes. La funcionalidad estrella es el flujo de
> publicación: el admin pega una URL de Amazon, el sistema enriquece
> con IA y publica en web + Telegram simultáneamente con alertas a
> usuarios suscritos.

---

## 👤 Perfiles de usuario

```
                            ┌──────────────┐
                            │  Anónimo     │
                            │              │
                            │  Ver feed    │
                            │  Ver detalle │
                            │  Buscar      │
                            └──────┬───────┘
                                   │  +login Google
                                   ▼
                            ┌──────────────┐
                            │  Registrado  │
                            │              │
                            │  + votar     │
                            │  + comentar  │
                            │  + favoritos │
                            │  + alertas   │
                            └──────┬───────┘
                                   │  +rol admin
                                   ▼
                            ┌──────────────┐
                            │  Admin       │
                            │              │
                            │  + CRUD      │
                            │  + IA copy   │
                            │  + Telegram  │
                            │  + audit log │
                            └──────────────┘
```

---

### 👀 Usuario anónimo

> _Acceso público sin cuenta. El visitante casual que llega por buscador
> o por enlace compartido en Telegram._

**Puede hacer**:

| Acción | Dónde |
|---|---|
| 📰 Navegar el feed de chollos | Home |
| 🔍 Buscar y filtrar | `/explorar` |
| 📄 Ver el detalle de un chollo (precio, descuento, Keepa, comentarios) | `/chollo/{slug}` |
| 🛒 Abrir el enlace afiliado (ir a Amazon) | Detalle |
| 💬 Acceder al canal de Telegram | Footer |
| 🔐 Iniciar sesión con Google | Header |

**NO puede hacer** (cualquier intento muestra "Inicia sesión para…"):

- ❌ Votar
- ❌ Comentar
- ❌ Marcar favoritos
- ❌ Crear alertas

---

### 🔑 Usuario registrado

> _Autenticado con Google OAuth (Supabase Auth). El miembro activo de
> la comunidad._

**Además de lo anterior**:

<table>
<thead>
<tr><th>Acción</th><th>Detalle técnico</th></tr>
</thead>
<tbody>
<tr>
  <td>👍 <strong>Votar chollos</strong> con <code>up</code> / <code>down</code></td>
  <td>Toggle: votar lo mismo dos veces lo retira. Recalcula temperatura. Rate limit 30/min.</td>
</tr>
<tr>
  <td>💬 <strong>Comentar</strong> con hilos anidados</td>
  <td>Por <code>parent_id</code>. Cada usuario sólo borra los suyos (ownership check server-side).</td>
</tr>
<tr>
  <td>👍 <strong>Votar comentarios</strong></td>
  <td>Sistema simétrico al de chollos.</td>
</tr>
<tr>
  <td>❤️ <strong>Marcar y desmarcar favoritos</strong></td>
  <td>Lista accesible en <code>/favoritos</code>.</td>
</tr>
<tr>
  <td>🔔 <strong>Crear alertas personalizadas</strong></td>
  <td>Uno o varios criterios: palabra clave · categoría · tienda · marca · precio máximo · descuento mínimo.</td>
</tr>
<tr>
  <td>⚙️ <strong>Gestionar sus alertas</strong></td>
  <td>Listar, activar/desactivar, borrar en <code>/alertas</code>.</td>
</tr>
<tr>
  <td>📬 <strong>Ver bandeja de notificaciones</strong></td>
  <td>Badge en el header (TanStack Query + <code>refetchOnWindowFocus</code>).</td>
</tr>
<tr>
  <td>👤 <strong>Editar perfil</strong></td>
  <td>Nombre público y bio en <code>/perfil</code>.</td>
</tr>
<tr>
  <td>🚪 <strong>Cerrar sesión</strong></td>
  <td>Invalida la sesión Supabase.</td>
</tr>
</tbody>
</table>

---

### 🛠️ Administrador

> _Mismos permisos que un usuario registrado, más el panel
> administrativo. En el proyecto actual hay **un único administrador**
> (el autor) — decisión consciente, no limitación técnica._

#### 🎛️ Panel `/admin`

```
/admin
├── /admin            → Dashboard con KPIs
├── /admin/chollos    → CRUD de chollos + autocomplete + Telegram
├── /admin/categorias → CRUD de categorías
├── /admin/tiendas    → CRUD de tiendas
└── /admin/usuarios   → Lista de usuarios y roles
```

#### ⚡ Funcionalidad estrella: autocomplete desde URL de Amazon

```
1. ✏️  Admin pega "https://amzn.to/3xyz"
   ▼
2. 🌐  Backend sigue el redirect (con allowlist Amazon + bloqueo IPs privadas)
   ▼
3. 🔍  Extrae el ASIN
   ▼
4. 📡  Amazon Creators API → título, precio, imágenes, descripción técnica
   ▼
5. 🤖  OpenAI → copy adaptado + categorización sugerida
   ▼
6. ✅  Formulario rellenado en el frontend
   ▼
7. 🔁  Si el ASIN ya existe → diálogo "Chollo duplicado" (3 opciones)
   ▼
8. 💾  Admin guarda → dispara AlertMatcher → audit_log
```

#### 📤 Publicación a Telegram

Botón "Enviar a Telegram" integrado en el form de chollos. Genera
copy adaptado con OpenAI, lo muestra editable y publica al canal. Rate
limit 5/min para evitar dobles envíos.

---

## 🔄 Sistema de alertas (la feature más usada)

### Modelo `Alert`

| Campo | Para qué |
|---|---|
| `keyword` | Texto a buscar en title / short_description / description |
| `category_id` / `subcategory_id` | Filtrar por categoría |
| `store_id` | Filtrar por tienda |
| `brand` | Filtrar por marca |
| `max_price` | Sólo alertar si el precio actual está por debajo |
| `min_discount_percentage` | Sólo alertar si el descuento es alto |
| `notify_in_app` | ✅ activo por defecto |
| `notify_email` | ⏸️ preparado para futuro |
| `is_active` | Permite pausar sin borrar |
| `last_triggered_at` | Auditoría |

### 🎯 `AlertMatcher`

```python
# alerts/application/alert_matcher.py
class AlertMatcher:
    """Recibe un Deal, busca alertas activas que coincidan,
    crea Notification por cada usuario con alerta compatible."""
```

**Anti-spam**: si ya existe una notificación para el par
`(alert_id, deal_id)`, **no** se crea duplicada (aunque el chollo se
actualice múltiples veces).

**Matching tolerante**:
- Frase exacta en el texto → match.
- Si no, todos los tokens en el texto (en cualquier orden) → match.
- Normalización de mayúsculas/minúsculas y acentos.

---

## 🔄 Flujos de uso clave

### 🌐 F1 · Usuario anónimo descubre un chollo

```
🏠 Llega a /              ← desde Google o link compartido
   ▼
📰 Ve el feed de chollos
   ▼
👆 Click en una card
   ▼
📄 /chollo/{slug}         ← detalle completo
   ▼
📈 Ve precio, descuento, gráfica Keepa
   ▼
🛒 Click en "Ir a la oferta"  → abre Amazon con tag de afiliado
```

### 🔔 F2 · Usuario crea una alerta y recibe notificación

```
🔐 Login con Google                              [Supabase OAuth]
   ▼
🆕 /alertas/nueva
   ▼
✍️  Escribe "monitor 4k" + descuento mínimo 30
   ▼
💾 Crear alerta                                  [POST /v1/alerts]
   ▼
   ··· tiempo después ···
   ▼
🛠️ Admin publica un monitor 4K con 33% descuento
   ▼
🎯 AlertMatcher detecta coincidencia
   ▼
📬 Crea Notification → badge sube a 1
   ▼
👀 Usuario va a /notificaciones
   ▼
👆 Click en el aviso
   ▼
📄 Aterriza en el detalle del chollo
```

### ⚡ F3 · Admin publica desde URL de Amazon

```
🔐 Login admin → /admin/chollos → NUEVO
   ▼
📋 Pega "https://amzn.to/3xyz" → AUTOCOMPLETAR
   ▼
[Backend ejecuta el flujo de 8 pasos descrito arriba]
   ▼
📝 Admin revisa el form ya rellenado
   ▼
   ├─ ⚠️  Si ASIN ya existe → diálogo duplicado (3 opciones)
   └─ ✅ Si no → continúa
   ▼
💾 GUARDAR                                       [POST /v1/deals/admin]
   ▼
🎯 AlertMatcher dispara notificaciones
   ▼
📋 admin_audit_log registra la acción
   ▼
📤 Botón "Enviar a Telegram" (opcional)
```

### 👍 F4 · Usuario vota un chollo

```
🔐 Estando logueado, en /chollo/{slug}
   ▼
👆 Click en ↑ o ↓                                [POST /v1/deals/{id}/vote]
   ▼
🔁 Si era el mismo voto → toggle (lo retira)
🆕 Si era distinto → lo registra
   ▼
🌡️ Backend recalcula temperatura
   ▼
🔄 Frontend muestra los contadores actualizados (sin refresco)
```

---

## 🎁 Casos de uso secundarios

| Caso | Cómo se resuelve |
|---|---|
| 🔄 **Recuperación de ASINs históricos** | Endpoint one-shot temporal (eliminado tras uso) que rellenaba `external_id` de chollos publicados antes del campo. Documentado en `PROJECT_STATUS.md`. |
| 🔗 **Compartir un chollo** | Cada detalle tiene `ShareBox` con URL canónica + botones copy/share. |
| 🛡️ **Detección de duplicados a futuro** | Índice único parcial `uq_deals_external_id ON deals(external_id) WHERE external_id IS NOT NULL` garantiza a nivel de BD que dos chollos no compartan ASIN. |

---

## ⚠️ Limitaciones funcionales conscientes

> Estas no son omisiones — son **decisiones diseñadas para el MVP**.
> Detalle en [`09 · Limitaciones y mejoras futuras`](09-limitaciones-y-mejoras-futuras.md).

| Limitación | Por qué |
|---|---|
| ❌ Sin email | Primer canal in-app, proveedor SMTP elegir tras validar audiencia. Modelo `Alert.notify_email` ya preparado. |
| ❌ Sin filtrado avanzado en bandeja | Volumen actual bajo. Cuando crezca, se añade. |
| ❌ Sin marcado individual de leído | Marca todas al cargar `/notificaciones`. Diseño simplificado del MVP. |
| ❌ Matching de alertas básico (sin sinónimos ni embeddings) | Para el volumen actual basta substring + tokens. |
| ❌ Sin push del navegador (PWA) | Requeriría Service Worker + permisos + sistema de envío. |
| ❌ Single admin | Modelo deliberado del producto (curación de calidad). |

---

<p align="center">
  <a href="02-objetivos-y-alcance.md">← Anterior: Objetivos y alcance</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="04-arquitectura-y-decisiones-tecnicas.md">Siguiente: Arquitectura →</a>
</p>
