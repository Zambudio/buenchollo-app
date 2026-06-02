# 01 — Overview

> Documentación operativa del repositorio. Punto de entrada para
> quien quiera entender, instalar o evolucionar BuenCholloTech.

---

## Qué es BuenCholloTech

Plataforma web tipo comunidad para publicar, gestionar y automatizar
**chollos tecnológicos** (ofertas de electrónica, gadgets,
periféricos). Va más allá de un agregador: el admin curado decide qué
publicar, los usuarios votan y comentan, y el sistema notifica vía
**alertas personalizadas** y un **canal de Telegram**.

## Qué problema resuelve

Las ofertas tech buenas viven dispersas (Amazon, foros, canales de
Telegram cerrados) y suelen perderse antes de que un usuario interesado
las vea. BuenCholloTech centraliza:

- Curación humana del admin (descarta el ruido).
- Descubrimiento por categorías y búsqueda.
- Alertas por palabra clave / categoría / precio.
- Publicación automática en Telegram con copy generado por IA.
- Histórico de precios con gráfica Keepa.

## Módulos principales

| Módulo backend | Responsabilidad |
|---|---|
| `deals` | CRUD de chollos, votos, click tracking, búsqueda y feed |
| `comments` | Comentarios anidados con votación, ownership check al borrar |
| `alerts` | Alertas por keyword/categoría/precio que el sistema cruza con cada chollo nuevo |
| `notifications` | Bandeja in-app + badge en el header |
| `products` | Preview de URL de Amazon (extracción ASIN + enriquecimiento OpenAI) |
| `telegram` | Publicación al canal con copy IA y categorías |
| `categories` / `stores` | Catálogo maestro (admin) |
| `users` | Perfil, roles, stats |

## Roles

- **Anónimo**: navega chollos, ve detalles, abre Telegram, abre enlace afiliado.
- **Usuario registrado** (Google OAuth): vota, comenta, marca favoritos, crea alertas, recibe notificaciones.
- **Admin**: panel `/admin/*` con CRUD de chollos, autocomplete desde URL de Amazon, publicación a Telegram, gestión de tiendas/categorías/usuarios.

## Flujo general

```
1. Anónimo  → home (lista de chollos recientes y populares) → /chollo/<slug>
2. Login    → Google OAuth (Supabase Auth)
3. Usuario  → vota / comenta / favorito / crea alerta
4. Admin    → pega URL Amazon → autocomplete (ASIN + título + imagen + precio + copy IA) → guarda
              → backend dispara `AlertMatcher` → notifica a usuarios con alerta coincidente
              → opcionalmente publica en Telegram con copy adaptado
5. Cron     → scheduler interno marca chollos expirados, activa programados, limpia
```

## Pirámide de la app

```
buenchollo-web (React 19 + TS strict + TanStack Router/Query)
        │
        │  HTTPS · JWT en Authorization header
        ▼
buenchollo-api (FastAPI · Clean Architecture pragmática)
        │
        ├─ Supabase Auth   (Google OAuth + email)
        ├─ Supabase DB     (Postgres · RLS activado · pooler PgBouncer 6543)
        ├─ Supabase Storage (subida imágenes admin)
        ├─ Amazon Creators API (preview producto)
        ├─ OpenAI (copy y categorización)
        └─ Telegram Bot API (publicación)
```

Más detalle en [`03-project-structure.md`](03-project-structure.md).

## Documentos hermanos

- [02 — Instalación y setup](02-installation-and-setup.md)
- [03 — Estructura del proyecto](03-project-structure.md)
- [04 — Configuración (env vars)](04-configuration.md)
- [05 — Flujo de desarrollo](05-development-workflow.md)
- [06 — Testing y calidad](06-testing-and-quality.md)
- [07 — Seguridad](07-security.md)
- [08 — Despliegue](08-deployment.md)
- [09 — Troubleshooting](09-troubleshooting.md)
