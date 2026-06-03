# ⚙️ 04 · Configuración

> **TL;DR** · Variables de entorno separadas por contexto: backend
> (`.env`), frontend (`.env.local`), CI (dummies en `ci.yml`). Lo
> sensible nunca toca el repo. Defaults seguros: `LOG_LEVEL=INFO`,
> `CORS_ORIGINS` con lista explícita.

---

## 🐍 Backend (`buenchollo-api/.env`)

### ✅ Obligatorias para arrancar

| Variable | Descripción | Ejemplo |
|---|---|---|
| 🔒 `DATABASE_URL` | Conexión asyncpg al pooler PgBouncer (puerto **6543**) | `postgresql+asyncpg://postgres.<ref>:<pwd>@aws-0-…pooler.supabase.com:6543/postgres` |
| 🔑 `SUPABASE_URL` | URL del proyecto (sin `/rest/v1/`) | `https://<ref>.supabase.co` |
| 🔐 `SUPABASE_KEY` | **service_role key** (privada, bypassa RLS). **NO** la anon key | `eyJ...` |
| 🌐 `CORS_ORIGINS` | Lista separada por comas. ⚠️ Nunca `*` en producción | `http://localhost:8080,http://localhost:8081` |

### 🎛️ Opcionales (defaults seguros)

| Variable | Default | Descripción |
|---|---|---|
| `APP_NAME` | `BuenChollo API` | Nombre que se loguea al arrancar |
| `APP_ENV` | `local` | `local` · `staging` · `production`. En `production` se activa HSTS y warning si `CORS_ORIGINS=*` |
| `LOG_LEVEL` | `INFO` | `DEBUG` · `INFO` · `WARNING` · `ERROR`. ⚠️ Nunca DEBUG en prod |
| `LOG_FORMAT` | `json` | `json` (Loki/ELK) o `text` (legible local) |
| `RATE_LIMIT_ENABLED` | `true` | Desactiva todos los `@limiter.limit` sin tocar código |

### 🐛 Sentry (opcional)

| Variable | Default | Descripción |
|---|---|---|
| `SENTRY_DSN` | (vacío) | Vacío para desactivar tracking |
| `SENTRY_ENVIRONMENT` | hereda APP_ENV | Etiqueta del entorno |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | 0.0 sólo errores, >0 captura performance |
| `SENTRY_RELEASE` | (vacío) | Versión para correlacionar con despliegues |

### 🛒 Amazon Creators API (⚠️ obligatorias para el autocomplete)

| Variable | Descripción |
|---|---|
| `AMAZON_CLIENT_ID` | Credencial LWA |
| `AMAZON_CLIENT_SECRET` | Credencial LWA |
| `AMAZON_AFFILIATE_TAG` | p.ej. `buenchollo0b-21` |
| `AMAZON_API_VERSION` | `3.2` (no cambiar salvo indicación de Amazon) |
| `AMAZON_MARKETPLACE` | `www.amazon.es` |

### 🤖 OpenAI (⚠️ obligatoria para copy)

| Variable | Descripción |
|---|---|
| `OPENAI_API_KEY` | `sk-...` |
| `OPENAI_MODEL` | `gpt-4o` por defecto |

### ✈️ Telegram (⚠️ obligatorias para publicar al canal)

| Variable | Descripción |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token del bot (BotFather) |
| `TELEGRAM_MAIN_CHANNEL_ID` | ID del canal público (`-100…`) |
| `TELEGRAM_ADMIN_CHANNEL_ID` | Canal de pruebas/admin |

> **Leyenda**: ✅ = la app no arranca sin ella · ⚠️ = la app arranca
> pero el endpoint concreto falla cuando se invoca.

---

## ⚛️ Frontend (`buenchollo-web/.env.local`)

| Variable | Obligatoria | Descripción |
|---|---|---|
| `VITE_SUPABASE_URL` | ✅ | URL del proyecto Supabase |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | ✅ | **anon key** (pública por diseño). 🚨 **NUNCA** la service_role |
| `VITE_API_URL` | ✅ | Base de `buenchollo-api` sin `/v1` final. Dev: `http://localhost:8000` |

> ⚠️ **Importante**: las variables `VITE_*` se embeben en el JavaScript
> del cliente al hacer `npm run build`. **Cualquier valor que pongas
> aquí es público**. Si filtraras la service_role key aquí, cualquier
> visitante podría hacer bypass de RLS.

---

## ⚙️ CI (GitHub Actions)

El workflow `.github/workflows/ci.yml` usa **valores dummy** para los
tests E2E, porque el cliente Supabase tira al construirse si faltan:

```yaml
env:
  VITE_SUPABASE_URL: https://dummy.supabase.co
  VITE_SUPABASE_PUBLISHABLE_KEY: dummy-anon-key-for-tests
  VITE_API_URL: http://localhost:9999
```

> 💡 Esto permite que `getSession()` devuelva `null` (no hay nada en
> localStorage del runner) y los tests del guard de admin
> (`/admin → /login`) funcionen sin necesitar un Supabase real.

---

## 🔁 Separación dev/prod

```
┌─────────────────────────────────────────────────────────┐
│  Variable          │  Dev local         │  Producción  │
├─────────────────────────────────────────────────────────┤
│  APP_ENV           │  local             │  production  │
│  LOG_LEVEL         │  INFO o DEBUG      │  INFO  ⚠️    │
│  CORS_ORIGINS      │  localhost:8080    │  dominio  ⚠️ │
│  DATABASE_URL      │  mismo proyecto    │  mismo       │
│  SUPABASE_KEY      │  mismo             │  mismo       │
│  SENTRY_DSN        │  (vacío)           │  DSN real    │
│  VITE_API_URL      │  localhost:8000    │  dominio     │
└─────────────────────────────────────────────────────────┘
```

> 🚨 **`LOG_LEVEL=DEBUG` en producción** filtraría info sensible.
> El backend emite WARNING al arrancar si detecta `CORS_ORIGINS=*`
> con `APP_ENV=production`.

---

## 🚫 Qué NUNCA se sube al repo

El `.gitignore` excluye:

```
*.env (excepto *.env.example)
.env.local, .env.*.local
buenchollo-web/coverage/
buenchollo-web/playwright-report/
buenchollo-web/test-results/
node_modules/, .venv/, dist/
.pytest_cache/, .mypy_cache/, .ruff_cache/
```

### ✅ Verificación pre-commit

```bash
git ls-files | grep -iE "\.env$|\.env\..*local$"
# debe estar vacío
```

### 🛡️ Doble defensa en CI

El job `security-audit` del CI ejecuta **gitleaks** sobre **todo el
historial**. Si alguna vez se cuela un secreto, el CI rompe y lo verás
en el run.

---

## 🔄 Rotación de claves

Si una clave se filtra (incluso por accidente):

```
1. 🚨 Revocar y regenerar en el proveedor (Supabase, Amazon, OpenAI, Telegram)
       │
       ▼
2. 🔄 Actualizar .env en el NAS
       │
       ▼
3. 🐳 Reiniciar contenedor
       │
       ▼
4. 🔍 Verificar con git log:
       git log --all -p -S "<fragmento>"
       │
       ▼
5. ❗ Si llegó a git → git filter-repo + force-push + notificar
```

> 📚 Plan completo de respuesta en
> [`07 · Seguridad → Respuesta a incidentes`](07-security.md).

---

<p align="center">
  <a href="03-project-structure.md">← Anterior: Estructura</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="05-development-workflow.md">Siguiente: Flujo de desarrollo →</a>
</p>
