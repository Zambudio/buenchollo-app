# 🔍 09 · Troubleshooting

> **TL;DR** · Errores comunes y soluciones. Si llegaste aquí, espero
> que el problema esté en esta página. Si no, abre issue privado o
> manda email a `pjzambudio@gmail.com`.

---

## 📥 Setup / instalación

### 🚫 `pnpm: command not found`

Este proyecto usa **npm**, no pnpm (Husky se configuró con npm).
Cualquier guía vieja que mencione pnpm es residuo.

```bash
npm install
npm run dev
```

### 🐍 `python` no encontrado en PowerShell

Windows a veces tiene `py` en vez de `python`:

```powershell
py --version
py -m venv .venv
```

> 💡 O instalar Python 3.11 desde [python.org](https://python.org)
> marcando "Add to PATH".

### 🔒 `Set-ExecutionPolicy` impide activar el venv

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Luego cerrar y reabrir terminal.

### 📦 `asyncpg` falla al instalar en Windows

> 💡 Necesita **Python 3.11+ de 64 bits** y Visual C++ Build Tools.
> Si no quieres tocar el sistema, usa Python desde el Microsoft Store
> o desde [python.org](https://python.org) marcando "Add to PATH".

---

## 🚀 Arranque del backend

### 🔴 Puerto 8000 ocupado

**Windows**:

```powershell
netstat -ano | Select-String ':8000'
Stop-Process -Id <PID> -Force
```

**Linux/Mac**:

```bash
lsof -i :8000
kill -9 <PID>
```

### 🔑 `Missing Supabase environment variables`

> 💡 El cliente Supabase tira al construirse si faltan
> `SUPABASE_URL` / `SUPABASE_KEY` (backend) o `VITE_SUPABASE_URL` /
> `VITE_SUPABASE_PUBLISHABLE_KEY` (frontend).

```bash
cat buenchollo-api/.env       # backend
cat buenchollo-web/.env.local # frontend
```

> 📚 Detalle: [`04-configuration.md`](04-configuration.md).

### 💾 `statement_cache_size` error al conectar a Postgres

> 💡 `DATABASE_URL` apunta al puerto **6543** (pooler PgBouncer), no
> al 5432. El backend ya pasa `statement_cache_size=0` para
> compatibilidad con PgBouncer en modo transacción.

```env
# ✅ correcto
DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<pwd>@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

### ❗ `ValueError: invalid interpolation syntax in postgresql+asyncpg://...%XX...`

> 💡 Tu contraseña de Supabase contiene caracteres URL-encoded
> (`%40` = `@`, `%E2%82%AC` = `€`). Alembic usa `ConfigParser` que
> interpreta `%` como sintaxis de interpolación.

El proyecto ya escapa los `%` en `alembic/env.py`:

```python
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("%", "%%"),
)
```

> ⚠️ Si vuelve a aparecer tras tocar `env.py`, restaurar ese `.replace`.

### 🛠️ Migraciones Alembic fallan al arrancar el contenedor

```
ERROR: alembic_version VARCHAR(32) too short
```

> 💡 Las revisiones Alembic deben usar IDs de ≤ 32 chars. Los del
> proyecto son timestamps puros (14 chars). Si añades una migración
> con un nombre largo, recórtalo: `20260605120000` y descripción en
> el filename, no en el ID.

### 🔍 Backend arranca pero `/v1/...` da 404

> 💡 El backend versiona todo bajo `/v1`. Las rutas sin prefijo
> (`/deals/...`, `/auth/...`) **no existen** — sólo `/health` y
> `/health/ready`. El frontend añade `/v1` automáticamente en
> `services/api/client.ts`.

---

## 🌐 Arranque del frontend

### 🔄 Puerto 8080 ocupado → salta a 8081

> ✅ Comportamiento normal de vinxi/Vite. El frontend funciona igual.
> Si los E2E fallan por URL fija, ajustar `playwright.config.ts →
> webServer.url`.

### 🪦 `npm run dev` cuelga al arrancar

Borrar caches:

```bash
rm -rf node_modules dist .vinxi .output .tanstack
npm install
npm run dev
```

### 🚫 `Cannot GET /` en local aunque `vite.config.ts` esté bien

> 💡 Comprueba si tu máquina tiene **dos letras de unidad mapeadas a la misma
> ruta de red** (p. ej. `N:` y `Z:` ambas apuntando a `\\mi-nas\carpeta`).
> Lanzar `npm run dev` desde una de ellas puede hacer que Vite/TanStack Start
> mezclen rutas de ambas letras para el mismo módulo internamente y el
> middleware SSR deje de responder — sin ningún error visible en consola ni
> en el log del servidor.

```powershell
Get-PSDrive -PSProvider FileSystem | Select-Object Name, DisplayRoot
```

Si dos letras comparten `DisplayRoot`, arranca siempre desde la que use
`fileURLToPath(import.meta.url)` internamente (compruébalo con
`DEBUG=vite:* npm run dev` y buscando rutas `default-entry` en el log — si
salen con una letra distinta a la que usaste para lanzar el comando, ese es
el problema). En este proyecto: **arrancar siempre desde `Z:`, no desde
`N:`**.

### 🚫 `@/*` no resuelve en el arranque (`Failed to run dependency scan`)

> 💡 Mismo origen que el de arriba: `vite-tsconfig-paths` no siempre resuelve
> alias en unidades de red con doble letra. `vite.config.ts` ya trae un alias
> explícito de respaldo (`resolve.alias: { "@": path.resolve(__dirname, "./src") }`)
> — si vuelve a fallar, revisa que no se haya perdido en un merge.

### 🗂️ El Drawer de categorías se queda abierto al cargar

> 💡 Bug detectado durante los E2E. La causa es que el dialog de
> Radix se monta en el DOM aunque `open=false`. Si bloquea
> interacciones en tests E2E, hacer
> `page.keyboard.press("Escape")` antes de interactuar con el header.

---

## 🌐 CORS

### 🚫 `CORS policy: No 'Access-Control-Allow-Origin'` en el navegador

Verificar `CORS_ORIGINS` en el `.env` del backend:

```env
# dev local
CORS_ORIGINS=http://localhost:8080,http://localhost:8081

# producción
CORS_ORIGINS=https://buenchollotech.com,https://www.buenchollotech.com
```

> ⚠️ Reiniciar el backend tras editar `.env`. Recuerda que **nunca**
> debe quedarse `*` en producción (el backend loguea WARNING si lo
> detecta con `APP_ENV=production`).

---

## 🤖 Motor de IA (OmniRoute)

### ⏱️ "Autocompletar desde Amazon" falla con `signal timed out`

> 💡 `/products/preview-from-url` encadena Amazon PA-API + Supabase + 2
> llamadas a OmniRoute (copywriting y categorización, en paralelo desde
> `ProductAIEnricher`). Con modelos gratuitos/locales puede rondar los 15-20s
> incluso paralelizado. Esa ruta ya usa un timeout propio de 45s en
> `productsApi.previewFromUrl` (`services/api/products.ts`), no el de 15s por
> defecto de `apiClient`. Si vuelve a fallar:

```
1. Revisar el log del backend: cada llamada a OmniRoute aparece como
   "HTTP Request: POST http://<ip-nas>:20128/v1/chat/completions"
2. Si tarda >45s de forma consistente, el contenedor OmniRoute del NAS está
   sobrecargado o el modelo elegido (AI_MODEL / AI_FALLBACK_MODELS) es lento
   — no es un bug del código, es latencia real del proveedor gratuito.
```

> 📚 Diagnóstico completo y decisión de diseño:
> [`PROJECT_STATUS.md` § 3.terdecies](../../PROJECT_STATUS.md).

### ❓ ¿Las llamadas de IA van a OmniRoute o a OpenAI?

> 💡 No te fíes solo del `.env` — verifícalo en los logs del backend
> (`logger: "httpx"`, línea `HTTP Request: POST <url>/chat/completions`). El
> fallback a `api.openai.com` (`config.py → effective_ai_base_url`) solo se
> activa si `AI_BASE_URL` está **vacío**; si OmniRoute está caído pero
> `AI_BASE_URL` sigue relleno, los reintentos de `AI_FALLBACK_MODELS` siguen
> yendo todos a OmniRoute (mismo `base_url` cacheado en el cliente) y fallan
> igual — no hay failover automático de proveedor en caliente.

---

## 🧪 Tests

### ⚠️ Vitest falla con `Cannot access X before initialization`

> 💡 `vi.mock` se hoistea al top del módulo y no puede referenciar
> variables declaradas debajo. Usar `vi.hoisted`:

```ts
const mocks = vi.hoisted(() => ({ useAuth: vi.fn(), toast: { error: vi.fn() } }));

vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));
```

### ⏱️ Test de userEvent se queda timeout

> 💡 No combines `vi.useFakeTimers()` con `userEvent.setup()` salvo
> que pases `advanceTimers: vi.advanceTimersByTime`. Para la mayoría
> de componentes basta con desactivar los fake timers en tests con
> clicks.

### 🎭 Playwright falla con `Timed out waiting for webServer`

> 💡 Verificar que el puerto del `playwright.config.ts → PORT`
> coincide con el que vinxi usa al arrancar (normalmente 8080).

### 📉 Coverage threshold falla en `src/lib/**`

Algún módulo de `lib/` bajó de 90%. Opciones:

```
1. Añadir tests para cubrir las ramas faltantes
2. Si es un archivo de config sin lógica, excluirlo en
   vitest.config.ts → coverage.exclude
   (como hicimos con query-client.ts)
```

---

## 🪝 Husky

### 🚫 El hook no se ejecuta tras clonar

Después de `git clone`, hay que correr `npm install` en la raíz del
repo para que `prepare: "husky"` lo enganche.

```bash
cd buenchollo-app   # raíz
npm install
ls -la .husky/      # verifica que pre-commit y pre-push existen
```

### 🚨 Quiero saltarme el hook por una vez

```bash
git commit --no-verify -m "..."
git push --no-verify
```

> ⚠️ Sólo en emergencias.
> 📚 Documentado en [`05-development-workflow.md`](05-development-workflow.md).

---

## 🚀 Despliegue NAS

### ⏹️ `alembic upgrade head` no se ejecuta al reiniciar contenedor

> 💡 Verificar el `command` del `docker-compose.yml`:

```yaml
command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

> ⚠️ Si está reemplazado por algo distinto (p.ej. sólo `uvicorn`),
> las migraciones no corren.

### 🔑 `gitleaks` falla en CI con secretos detectados

> 💡 Algún commit antiguo contiene una clave. Opciones:

```
1. Si la clave ya está revocada → marcar como falso positivo en .gitleaks.toml
2. Si está activa → revocar primero, luego limpiar el historial con
   git filter-repo y force-push (notificar antes a los demás devs)
```

---

## 🐛 Sentry

### 🔇 No llegan eventos a Sentry aunque hay errores

```
1. Comprobar SENTRY_DSN en el .env real (no el .env.example)

2. Comprobar logs del contenedor al arrancar:
   "Sentry inicializado (env=production, traces=0.00)."

   Si dice "Sentry desactivado (SENTRY_DSN vacío)" → el DSN no se cargó

3. Forzar un error desde /health (cambiar el handler para que lance
   una excepción) y verificar que aparece en Sentry
```

---

## 🆘 Si todo falla

```bash
# Estado del repo
git status
git log --oneline -10

# CI en GitHub
# https://github.com/Zambudio/buenchollo-app/actions

# Última versión estable
git checkout v1.0.0-tfm
```

> 📧 Si el problema persiste, abrir issue privado o mandar email a
> `pjzambudio@gmail.com` con los logs del contenedor.

---

<p align="center">
  <a href="08-deployment.md">← Anterior: Despliegue</a> ·
  <a href="00-index.md">Índice</a>
</p>
