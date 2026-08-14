# 🌅 01 · Overview

> **TL;DR** · BuenCholloTech es una plataforma web tipo comunidad
> para chollos tecnológicos. Web + Telegram + alertas in-app, todo
> alimentado por curación humana del admin con autocomplete IA desde
> Amazon.

---

## 🎯 ¿Qué es BuenCholloTech?

Plataforma web para **publicar, gestionar y automatizar chollos
tecnológicos** (electrónica, gadgets, periféricos). Más que un
agregador: el admin curado decide qué se publica, los usuarios votan
y comentan, y el sistema notifica vía **alertas personalizadas** y un
**canal de Telegram**.

---

## 🔥 ¿Qué problema resuelve?

```
┌─────────────────────────────────────────────────┐
│  Las ofertas tech buenas viven dispersas        │
│  (Amazon, foros, canales cerrados)              │
│  y se pierden antes de que un usuario           │
│  interesado las vea.                            │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│  BuenCholloTech centraliza:                     │
│                                                 │
│  ✅ Curación humana del admin                   │
│  ✅ Descubrimiento por categorías y búsqueda    │
│  ✅ Alertas por keyword/categoría/precio        │
│  ✅ Publicación automatizada en Telegram con IA │
│  ✅ Histórico de precios con gráfica Keepa      │
└─────────────────────────────────────────────────┘
```

---

## 🧱 Módulos principales

### 🐍 Backend

| Módulo | Responsabilidad |
|---|---|
| 🛒 `deals` | CRUD de chollos, votos, click tracking, búsqueda y feed |
| 💬 `comments` | Comentarios anidados con votación + ownership check |
| 🔔 `alerts` | Alertas por keyword/categoría/precio. AlertMatcher cruza cada chollo nuevo |
| 📬 `notifications` | Bandeja in-app + badge en el header |
| 🤖 `ai` | Motor de IA desacoplado (OmniRoute/OpenCode/modelos gratuitos), fallback multi-modelo y base para Chatbot web |
| 📦 `products` | Preview de URL Amazon (extracción ASIN + enriquecimiento IA con copywriting y categorías) |
| ✈️ `telegram` | Publicación al canal con formato emoji premium, hashtags IA y programación de deals |
| 🏷️ `categories` | Catálogo maestro (admin) |
| 🏪 `stores` | Catálogo maestro (admin) |
| 👤 `users` | Perfil, roles, stats |

---

## 👥 Roles de usuario

```
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  👤 Anónimo  │        │ 🔑 Registrado│        │ 🛠️ Admin     │
│              │        │              │        │              │
│ Ver feed     │   →    │  + votar     │   →    │  + CRUD      │
│ Ver detalle  │ login  │  + comentar  │  rol   │  + IA copy   │
│ Buscar       │ Google │  + favoritos │  admin │  + Telegram  │
│              │        │  + alertas   │        │  + audit log │
└──────────────┘        └──────────────┘        └──────────────┘
```

---

## 🔄 Flujo general

```
1. 👤  Anónimo llega a /                              [home con feed]
        │
        ▼
2. 👆  Click en card → /chollo/{slug}                 [detalle]
        │
        ▼
3. 🔐  Login Google                                   [Supabase OAuth]
        │
        ▼
4. 🔔  Usuario crea alerta · vota · comenta · favorito
        │
        ▼
5. 🛠️  Admin pega URL Amazon → autocomplete + IA     [/admin/chollos]
        │
        ├─ 🎯 AlertMatcher dispara notificaciones
        ├─ 📋 admin_audit_log registra la acción
        └─ ✈️ Publicación opcional a Telegram
        │
        ▼
6. ⏰  Scheduler interno                              [cada 5 min]
        ├─ Marca chollos expirados
        ├─ Activa programados
        └─ Limpia recursos antiguos                   [03:00 daily]
```

---

## 🏗️ Pirámide del sistema

```
┌────────────────────────────────────────────────────────────┐
│  ⚛️ buenchollo-web                                          │
│  React 19 + TS strict + TanStack Router/Query              │
└──────────────────────────┬─────────────────────────────────┘
                           │  🔒 HTTPS · JWT en Authorization
                           ▼
┌────────────────────────────────────────────────────────────┐
│  🐍 buenchollo-api                                          │
│  FastAPI · Clean Architecture pragmática                   │
└──┬───────────┬───────────┬───────────┬─────────────┬───────┘
   ▼           ▼           ▼           ▼             ▼
┌──────┐  ┌────────┐  ┌────────┐  ┌────────┐   ┌──────────┐
│  🔐  │  │  💾    │  │  📦    │  │  🤖    │   │  ✈️      │
│Supab.│  │Supab.  │  │Amazon  │  │OpenAI  │   │Telegram  │
│Auth  │  │ DB+RLS │  │Creators│  │ GPT-4o │   │  Bot     │
└──────┘  └────────┘  └────────┘  └────────┘   └──────────┘
```

Más detalle en [`03 · Estructura del proyecto`](03-project-structure.md).

---

## 📚 Documentos hermanos

- [02 · Instalación y setup](02-installation-and-setup.md)
- [03 · Estructura del proyecto](03-project-structure.md)
- [04 · Configuración (env vars)](04-configuration.md)
- [05 · Flujo de desarrollo](05-development-workflow.md)
- [06 · Testing y calidad](06-testing-and-quality.md)
- [07 · Seguridad](07-security.md)
- [08 · Despliegue](08-deployment.md)
- [09 · Troubleshooting](09-troubleshooting.md)

---

<p align="center">
  <a href="00-index.md">← Índice</a> ·
  <a href="02-installation-and-setup.md">Siguiente: Instalación y setup →</a>
</p>
