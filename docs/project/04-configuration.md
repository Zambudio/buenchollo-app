# 04 — Configuración

## Variables de entorno — backend (`buenchollo-api/.env`)

| Variable | Obligatoria | Descripción | Ejemplo |
|---|---|---|---|
| `APP_NAME` | — | Nombre que se loguea al arrancar | `BuenChollo API` |
| `APP_ENV` | — | `local` \| `staging` \| `production`. En `production` se activa HSTS y warning si `CORS_ORIGINS=*` | `local` |
| `LOG_LEVEL` | — | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`. Nunca DEBUG en prod (filtra info) | `INFO` |
| `LOG_FORMAT` | — | `json` (Loki/ELK) o `text` (legible local) | `json` |
| `RATE_LIMIT_ENABLED` | — | Desactiva todos los `@limiter.limit` sin tocar código. Útil en tests masivos | `true` |
| `CORS_ORIGINS` | ✅ | Lista separada por comas. En producción NUNCA `*` (el backend loguea WARNING si lo detecta) | `http://localhost:8080,http://localhost:8081` |
| `DATABASE_URL` | ✅ | Conexión asyncpg al pooler PgBouncer de Supabase (puerto 6543) | `postgresql+asyncpg://postgres.<ref>:<pwd>@aws-0-eu-central-1.pooler.supabase.com:6543/postgres` |
| `SUPABASE_URL` | ✅ | URL del proyecto (sin `/rest/v1/`) | `https://<ref>.supabase.co` |
| `SUPABASE_KEY` | ✅ | **service_role key** (privada, bypassa RLS). NO la anon key | `eyJ...` |
| `SENTRY_DSN` | — | Dejar vacío para desactivar tracking | `https://...ingest.sentry.io/...` |
| `SENTRY_ENVIRONMENT` | — | Hereda APP_ENV si está vacío | `production` |
| `SENTRY_TRACES_SAMPLE_RATE` | — | 0.0 sólo errores, >0 captura performance | `0.0` |
| `SENTRY_RELEASE` | — | Versión para correlacionar con despliegues | `1.0.0` |
| `AMAZON_CLIENT_ID` | ⚠️ | Credenciales LWA. Sin estas no funciona el autocomplete | `amzn1.application-oa2-client.…` |
| `AMAZON_CLIENT_SECRET` | ⚠️ | (privada) | — |
| `AMAZON_AFFILIATE_TAG` | ⚠️ | Tag para los enlaces afiliados | `buenchollo0b-21` |
| `AMAZON_API_VERSION` | — | Versión LWA (no cambiar salvo indicación de Amazon) | `3.2` |
| `AMAZON_MARKETPLACE` | — | Marketplace de Amazon | `www.amazon.es` |
| `OPENAI_API_KEY` | ⚠️ | Para copy y categorización del autocomplete | `sk-...` |
| `OPENAI_MODEL` | — | Modelo a usar | `gpt-4o` |
| `TELEGRAM_BOT_TOKEN` | ⚠️ | Token del bot (BotFather) | `123456:ABC...` |
| `TELEGRAM_MAIN_CHANNEL_ID` | ⚠️ | ID del canal público (`-100…`) | `-1001234567890` |
| `TELEGRAM_ADMIN_CHANNEL_ID` | ⚠️ | Canal de pruebas/admin | `-1001234567891` |

✅ = obligatoria, app no arranca sin ella.
⚠️ = obligatoria para activar la feature concreta; la app arranca sin ellas pero el endpoint correspondiente falla cuando se invoca.

## Variables de entorno — frontend (`buenchollo-web/.env.local`)

| Variable | Obligatoria | Descripción |
|---|---|---|
| `VITE_SUPABASE_URL` | ✅ | URL del proyecto Supabase |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | ✅ | **anon key** (pública por diseño, embebida en el bundle). NUNCA la service_role |
| `VITE_API_URL` | ✅ | Base de `buenchollo-api` sin `/v1` final (el cliente lo añade). Dev: `http://localhost:8000`. Prod: `https://api.tudominio.com` |

> **Importante**: las variables `VITE_*` se embeben en el JavaScript del cliente al hacer `npm run build`. Cualquier valor que pongas aquí es público. Si filtraras la service_role key aquí, cualquier visitante podría hacer bypass de RLS.

## Variables — CI (GitHub Actions)

El workflow `.github/workflows/ci.yml` usa valores **dummy** para los
tests E2E, porque el cliente Supabase tira al construirse si faltan las
variables:

```yaml
env:
  VITE_SUPABASE_URL: https://dummy.supabase.co
  VITE_SUPABASE_PUBLISHABLE_KEY: dummy-anon-key-for-tests
  VITE_API_URL: http://localhost:9999
```

Esto permite que `getSession()` devuelva `null` (no hay nada en
localStorage del runner) y los tests del guard de admin (`/admin → /login`)
funcionen sin necesitar un Supabase real.

## Separación dev/prod

| Tema | Dev local | Producción NAS |
|---|---|---|
| `APP_ENV` | `local` | `production` |
| `LOG_LEVEL` | `INFO` o `DEBUG` | `INFO` (nunca DEBUG — filtra PII) |
| `CORS_ORIGINS` | `http://localhost:8080` | `https://tudominio.com,https://www.tudominio.com` |
| `DATABASE_URL` | mismo proyecto Supabase (no merece la pena tener dos) | mismo |
| `SUPABASE_KEY` | mismo service_role key | mismo |
| `SENTRY_DSN` | vacío | DSN real |
| `VITE_API_URL` | `http://localhost:8000` | `https://api.tudominio.com` |

## Qué NUNCA se sube al repo

El `.gitignore` excluye:

- `*.env` (excepto `*.env.example`)
- `.env.local`, `.env.*.local`
- `buenchollo-web/coverage/`, `playwright-report/`, `test-results/`
- `node_modules/`, `.venv/`, `dist/`
- Caches: `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`

Verificación pre-commit:

```bash
git ls-files | grep -iE "\.env$|\.env\..*local$"
# debe estar vacío
```

Y el job `security-audit` del CI ejecuta **gitleaks** sobre todo el
historial — si alguna vez se cuela un secreto, el CI rompe y lo verás
en el run.

## Rotación de claves

Si una clave se filtra (incluso por accidente):

1. Revocar y regenerar en el proveedor (Supabase, Amazon, OpenAI, Telegram).
2. Actualizar `.env` en el NAS.
3. Reiniciar contenedor.
4. Verificar `git log --all -p -S "<fragmento>"` para confirmar que no
   se subió a git. Si se subió, `git filter-repo` y force-push.

Plan completo de respuesta en [`07-security.md` § Respuesta a incidentes](07-security.md).
