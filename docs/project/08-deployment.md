# 🚀 08 · Despliegue

> ⚠️ **ESTADO ACTUAL (2026-06):** la migración al dominio definitivo **ya está
> hecha**. Producción = **frontend en Cloudflare Workers** (`buenchollotech.com`)
> + **API en el NAS expuesta vía Cloudflare Tunnel** (`api.buenchollotech.com`).
> La **guía operativa viva y verificada** es
> [`docs/guides/Cloudflare.md`](../guides/Cloudflare.md). Las secciones de abajo
> (DDNS Synology, reverse proxy DSM, "Cloudflare Pages/Vercel") describen el
> **enfoque anterior / la transición** y se conservan como histórico/contexto.

> **TL;DR (backend)** · Docker Compose en NAS Synology; el contenedor ejecuta
> `alembic upgrade head` antes de uvicorn al arrancar — migraciones automáticas,
> sin SSH. La exposición pública del NAS hoy es por **Cloudflare Tunnel**
> (`cloudflared` en el `docker-compose.yml`), no por reverse proxy + DDNS.

---

## 🏠 Arquitectura actual

```
┌──────────────────────────────────────────────────┐
│  🌐 Internet                                     │
└────────────────┬─────────────────────────────────┘
                 │  🔒 HTTPS · puerto 443
                 ▼
┌──────────────────────────────────────────────────┐
│  🏠 DDNS Synology (*.synology.me)                │
└────────────────┬─────────────────────────────────┘
                 │  Port forward → IP del NAS
                 ▼
┌──────────────────────────────────────────────────┐
│  💾 NAS Synology DSM 7.2+ — Reverse Proxy        │
│      └─ 🔐 HTTPS termina aquí                    │
└────────────────┬─────────────────────────────────┘
                 │  HTTP interno hacia el contenedor
                 ▼
┌──────────────────────────────────────────────────┐
│  🐳 Docker (buenchollo-api) — puerto 8000        │
│      └─ 📦 python:3.11-slim                      │
└────────────────┬─────────────────────────────────┘
                 │
   ┌─────────────┼─────────────┬─────────────┬──────────┐
   ▼             ▼             ▼             ▼          ▼
┌──────┐     ┌────────┐     ┌────────┐    ┌──────┐  ┌───────┐
│Supab.│     │ Amazon │     │ OpenAI │    │Telegm│  │Sentry │
└──────┘     └────────┘     └────────┘    └──────┘  └───────┘
```

> 💡 El frontend se sirve estáticamente desde el mismo NAS, o se
> puede mover a Cloudflare Pages / Vercel si se quiere CDN global.

---

## 🧱 Componentes del despliegue

### 🐳 Dockerfile

```
Base: python:3.11-slim
├── Instala desde requirements.txt (sin dev deps)
├── Copia el código
└── Arranca uvicorn
```

### 📋 docker-compose.yml

> 🎯 **Característica clave**: ejecuta migraciones Alembic antes de
> arrancar uvicorn:

```yaml
command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

> ✅ Cada vez que el contenedor reinicia, se aplican las migraciones
> pendientes **automáticamente** (sin SSH al NAS).

El Compose de producción incluye además `buenchollo-scheduler`, con el mismo
código e `.env`, ejecutando `python -m app.run_scheduler`. La API usa
`SCHEDULER_ENABLED=false` para que los jobs —incluida la verificación de precio,
stock y publicación— no se dupliquen entre los dos workers de uvicorn.

### 🛠️ Migraciones (Alembic)

Convive con SQL histórico pre-2026-05-27 y nuevas migraciones Alembic
desde el baseline `20260527120000_baseline.py` (vacío, marca el punto
de cambio de formato).

> 📚 Detalle: [`MIGRATIONS.md`](../guides/MIGRATIONS.md).

---

## 🚀 Despliegue inicial en NAS Synology

### 1️⃣ Preparar archivos en el NAS

```
1. File Station → carpeta `docker/buenchollo-api/`
2. Subir todo el contenido de `buenchollo-api/`
   (excepto `.venv/`, `__pycache__/`)
3. Subir el `.env` real con las credenciales
```

### 2️⃣ Desplegar con Container Manager (DSM 7.2+)

```
1. Container Manager → Proyecto → Crear
2. Nombre: buenchollo-api
3. Ruta: la carpeta subida
4. Modo: Usar docker-compose.yml existente
5. Finalizar → DSM construye la imagen y lanza el contenedor
```

### 3️⃣ Reverse proxy en DSM

> `Control Panel → Login Portal → Advanced → Reverse Proxy → Create`

**Regla API**:

| Campo | Valor |
|---|---|
| Source | HTTPS, `embyzambu.synology.me`, puerto 8000 |
| Destination | HTTP, `localhost`, puerto 8000 |

### 4️⃣ SSL con Let's Encrypt

> `Control Panel → Security → Certificate → Add`

```
- "Get a certificate from Let's Encrypt"
- Domain: embyzambu.synology.me
- Email del propietario
- Se renueva automáticamente cada 90 días
```

### 5️⃣ Verificación

```bash
curl -s https://embyzambu.synology.me:8000/health
# → {"status":"ok"}

curl -s https://embyzambu.synology.me:8000/health/ready
# → {"status":"ready","db_latency_ms":...,"checks":{...}}
```

---

## 🔄 Actualizar el contenedor tras cambios

```bash
# 📥 En el NAS (o subiendo con SynologyDrive desde el PC)
cd /volume1/docker/buenchollo-api
git pull

# 🔄 Restart simple (si el volumen monta el código)
docker-compose restart

# 🔨 Rebuild (si cambiaron requirements.txt o Dockerfile)
docker-compose build --no-cache
docker-compose up -d
```

> ✅ El primer arranque tras un rebuild ejecuta automáticamente
> `alembic upgrade head` y aplica migraciones pendientes.

---

## 🌐 Frontend en producción — Cloudflare Workers

> 🎯 **Vía elegida**: el frontend es **TanStack Start** (SSR), no un SPA
> estático. Se despliega como un **Cloudflare Worker** (config en
> `buenchollo-web/wrangler.jsonc`, `main: @tanstack/react-start/server-entry`).
> El NAS solo aloja la API. El Worker renderiza en el edge y sirve los
> estáticos de `dist/client`.

### 📦 Build

```bash
cd buenchollo-web
npm run build      # genera dist/client (estáticos) + dist/server (worker SSR)
```

### 🚀 Despliegue

Dos opciones (elegir una):

| Opción | Cómo | Previews por rama |
|---|---|---|
| 🔗 Workers Builds (Git) | `Workers & Pages → Create → Workers → Connect to Git`, root `buenchollo-web`, build `npm run build`, deploy `wrangler deploy` | ✅ automáticos |
| 💻 Wrangler CLI | `cd buenchollo-web && npx wrangler deploy` | manual (`--name` distinto) |

> 💡 **Recomendado**: Workers Builds conectado al repo. Push a `main` →
> deploy a producción; push a otra rama → **versión preview** con su propia
> URL `*.workers.dev`. Aísla cada rama sin tocar producción.

### 🔑 Variables de entorno (build-time)

> ⚠️ Los `VITE_*` se embeben en el bundle al construir, **no** en un
> `.env.production` del repo (no existe ni debe existir). En Workers Builds se
> definen como *build variables* en el panel:

```
VITE_API_URL=https://api.tudominio.com
VITE_SUPABASE_URL=https://<ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=eyJ...   # anon key (pública por diseño)
```

### 🌍 Dominio propio

`Worker → Settings → Domains & Routes → Add Custom Domain` →
`tudominio.com` y `www.tudominio.com`. Cloudflare crea los registros DNS
automáticamente (no hace falta apuntar a la IP del NAS).

---

## 🎯 Pre-go-live al dominio definitivo

Cuando BuenCholloTech se mueva de DDNS Synology a su propio dominio
(p.ej. `buenchollotech.com`):

### 📝 Variables de entorno (.env del NAS)

| Variable | Cambiar a |
|---|---|
| `APP_ENV` | `production` |
| `LOG_LEVEL` | `INFO` |
| `CORS_ORIGINS` | `https://buenchollotech.com,https://www.buenchollotech.com` |
| `SENTRY_DSN` | el DSN real |
| `SENTRY_ENVIRONMENT` | `production` |

### 🔐 Supabase

`Authentication → URL Configuration`:

- 🌐 **Site URL**: `https://buenchollotech.com`
- 🔄 **Redirect URLs**: `https://buenchollotech.com/**` y
  `https://www.buenchollotech.com/**`
- 🗑️ Eliminar `localhost`

### 🌐 DNS (Cloudflare)

| Tipo | Nombre | Valor | Proxy | Quién lo crea |
|---|---|---|---|---|
| — | `@` | Worker `buenchollotech` | ✅ | Cloudflare al añadir Custom Domain al Worker |
| — | `www` | Worker `buenchollotech` | ✅ | Cloudflare al añadir Custom Domain al Worker |
| A | `api` | IP pública del NAS | ✅ | Manual + lo mantiene `cloudflare-ddns` |

> 💡 El frontend (`@`, `www`) lo resuelve el Worker (Cloudflare crea su ruta
> al añadir el Custom Domain). Solo `api` apunta al NAS; con proxy activo su IP
> real queda oculta (CDN + DDoS básica). Como la IP es **dinámica**, el
> contenedor `cloudflare-ddns` actualiza el registro `api` automáticamente —
> ver `docker-compose.yml`.

### 🔄 IP dinámica → DDNS Cloudflare

Si la IP del router es dinámica, contenedor adicional:

```yaml
cloudflare-ddns:
  image: oznu/cloudflare-ddns:latest
  restart: always
  environment:
    - API_KEY=<token_cloudflare>
    - ZONE=buenchollotech.com
    - SUBDOMAIN=@
```

### 🔄 Reverse proxy en DSM con dominio nuevo

Mismas reglas que en el setup inicial pero con `buenchollotech.com` y
`api.buenchollotech.com`. El certificado Let's Encrypt cubre ambos
subdominios añadiéndolos como SAN.

### 🚇 Cloudflare Tunnel (alternativa sin abrir puertos)

> 💡 Si el ISP bloquea 80/443 o quieres no abrir puertos:

```bash
docker run -d \
  --name cloudflared \
  --restart unless-stopped \
  cloudflare/cloudflared:latest \
  tunnel --no-autoupdate run --token <TUNNEL_TOKEN>
```

> Token en `Cloudflare Zero Trust → Tunnels → Create tunnel`. No
> abres puertos, IP oculta, SSL automático.

---

## ✅ Comprobaciones post-deploy

- [ ] 🌐 `https://tudominio.com` carga la web
- [ ] ❤️ `https://api.tudominio.com/health` → `200 {"status":"ok"}`
- [ ] 🔐 Login con Google funciona (redirección Supabase Auth)
- [ ] 🎫 Petición autenticada funciona (favoritos, voto)
- [ ] 🚷 Usuario sin rol admin **NO** accede a `/v1/deals/admin/*` (debe devolver 403)
- [ ] 📝 Logs del contenedor sin errores de CORS
- [ ] 🔄 HTTP redirige a HTTPS
- [ ] 🛡️ Headers de seguridad correctos:

```bash
curl -sI https://api.tudominio.com/health | \
  grep -iE "content-security|x-frame|x-content-type|referrer|permissions|strict-transport"
```

---

## 🔙 Rollback rápido

Si un release rompe producción:

```bash
cd /volume1/docker/buenchollo-api
git log --oneline -10               # 🔍 buscar el commit estable previo
git checkout <commit_estable>
docker-compose build --no-cache && docker-compose up -d
```

> ✅ Tras estabilizar, mergear el fix correcto a `main` y desplegar
> de nuevo.

---

<p align="center">
  <a href="07-security.md">← Anterior: Seguridad</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="09-troubleshooting.md">Siguiente: Troubleshooting →</a>
</p>
