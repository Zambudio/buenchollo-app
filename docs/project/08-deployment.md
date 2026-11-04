# 🚀 08 · Despliegue

> ⚠️ **ESTADO ACTUAL (2026-06; checklist de chollos de usuarios añadida el 2026-11-04):** la migración al dominio definitivo **ya está
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

```text
Navegador ── HTTPS ──> Cloudflare Worker (frontend SSR)
    │
    └────── HTTPS ──> Cloudflare Tunnel ──> buenchollo-api (NAS)
                                              │
                                              ├─> buenchollo-scheduler
                                              ├─> PostgreSQL/Supabase Auth/Storage
                                              └─> Amazon · Keepa · IA · Telegram · Sentry
```

Contenedores activos del stack: `buenchollo-api`, `buenchollo-scheduler` y
`cloudflared`. El frontend no se sirve desde el NAS.

### Histórico: topología anterior con DDNS y reverse proxy (no vigente)

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

> Este bloque se conserva únicamente para entender la transición. No debe usarse
> como receta de producción.

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

## 🗄️ Histórico: plan pre-go-live ya ejecutado

Este fue el plan utilizado para pasar de DDNS Synology al dominio
`buenchollotech.com`. Se conserva como referencia histórica; no describe una
tarea pendiente ni sustituye la guía viva de Cloudflare.

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
  cloudflare/cloudflared:2026.10.3 \
  tunnel --no-autoupdate run --token <TUNNEL_TOKEN>
```

> Token en `Cloudflare Zero Trust → Tunnels → Create tunnel`. No
> abres puertos, IP oculta, SSL automático.

---

## 🙋 Checklist de despliegue — chollos de usuarios

> ⚠️ **Cómo llega el código al NAS.** Los contenedores `buenchollo-api` y
> `buenchollo-scheduler` montan esta carpeta (`volumes: .:/app`) y el NAS la ve en
> tiempo real: es el mismo recurso de red que `Z:` (ver [`NAS-SSH.md`](../guides/NAS-SSH.md) §1.1).
> **La rama que esté activa en la copia de trabajo es la que ejecutan los contenedores
> en cuanto se reinician o reconstruyen.** No hay `tar`/`scp` ni despliegue separado.
> El comando de la API es `alembic upgrade head && uvicorn ...`.
>
> **Situación a 2026-11-04.** Los contenedores siguen ejecutando en memoria el código de
> `main` (arrancados el 2026-11-03 15:53 UTC), pero la copia de trabajo está en `develop`
> y la BD compartida ya está en la revisión Alembic `20261103140000`. Consecuencias:
>
> - **Cualquier reinicio ahora** (caída del NAS, `docker restart`, `up -d` con cambios)
>   cargaría código de `develop` sobre la imagen antigua, sin `Pillow` →
>   `ModuleNotFoundError` y API caída.
> - **Volver la copia de trabajo a `main`** tampoco sirve hoy: `alembic upgrade head`
>   falla con "Can't locate revision" porque `main` no conoce `20261103140000`.
> - Por tanto el despliegue debe hacerse **pronto**. Camino seguro: mergear
>   `develop` → `main`, dejar la copia de trabajo en `main` (== `develop`) y reconstruir.

Orden recomendado:

1. **Merge** `develop` → `main` y esperar CI verde (backend, integración, frontend, E2E,
   auditoría). La CI de la PR #64 pasó todos los trabajos.
2. **`.env` del NAS** (no copiar valores al repo): añadir
   `ADMIN_NOTIFICATION_EMAIL=pjzambudio@gmail.com` (requiere SMTP operativo; sin SMTP el
   aviso no sale). `AMAZON_AFFILIATE_TAG`: si no está definida se usa el valor por
   defecto `buenchollo0b-21`; **solo un valor explícitamente vacío** (`AMAZON_AFFILIATE_TAG=`)
   aborta el arranque con `APP_ENV=production`. Confirmar que no está vacía.
3. **Reconstruir y levantar desde la copia de trabajo ya en `main`**, en el NAS
   (`NAS-SSH.md` §1.1): `docker-compose build && docker-compose up -d`. Un simple
   `restart` no basta (dependencias nuevas `Pillow` y `limits`). `alembic upgrade head`
   no hará nada: la migración `20261103140000` ya está aplicada.
4. **Ventana web ↔ API.** La web se despliega sola desde `main` (Cloudflare Workers
   Builds, minutos): durante el intervalo hasta que la API nueva esté arriba, `/publicar`
   y `/mis-chollos` llamarían a endpoints que aún no existen en la API antigua. Para
   acortarla, hacer el paso 2 y el 3 inmediatamente después del merge (o reconstruir
   primero desde la copia de trabajo ya mergeada y empujar a `main` después). La ventana
   es de minutos y solo afecta a las pantallas nuevas.
5. **Recomendado: no exponer la API a la LAN.** `docker-compose.yml` publica `8001:8000` en
   el host; como los límites de peticiones confían en `CF-Connecting-IP`, un cliente de la
   LAN que salte Cloudflare podría falsificarla. Enlazar a loopback (`127.0.0.1:8001:8000`)
   **no afecta a `cloudflared`**, que llega a `buenchollo-api:8000` por la red de Compose,
   ni al healthcheck del Dockerfile (`localhost:8000` dentro del contenedor). `NAS-SSH.md`
   solo menciona el `8001` para evitar choques de puertos, no como acceso desde la LAN
   (comprobar antes de aplicar). No está aplicado: es decisión de despliegue.
6. **Supabase Auth → URL Configuration → Redirect URLs** debe incluir
   `https://buenchollotech.com/**` (sin ello Google OAuth vuelve al Site URL en lugar de a
   `/publicar`).
7. **Backfill** (idempotente): desde `buenchollo-api/` (o dentro del contenedor API)
   `python scripts/backfill_canonical_urls.py` (dry-run) y luego `--apply`, para los chollos
   que aún no tengan `canonical_url`.
8. **Smoke tests**:
   - `https://api.buenchollotech.com/health` → 200 y logs sin error de arranque.
   - Con un usuario real: `/publicar` → pegar un enlace `amazon.es` → prefill y
     `?tag=<nuestro>`; enviar una propuesta (llega aviso a `ADMIN_NOTIFICATION_EMAIL`).
   - `/admin/propuestas` carga la cola y aprobar/rechazar notifica al autor; borrar luego
     el chollo de prueba.
   - Subir una imagen: la URL es de `deal-images/submissions/` y termina en `.webp`.
   - Un 429 devuelve `Retry-After`.
   - Sin sesión, "+ Publicar chollo" muestra el diálogo de cuenta.

### 🔙 Rollback de esta feature

- **Web**: revertir el merge en `main` (se redespliega solo) o volver a la versión anterior
  del Worker desde Cloudflare.
- **API**: la migración es aditiva, pero el contenedor ejecuta `alembic upgrade head` al
  arrancar y **falla si el código no contiene el fichero `20261103140000`** ("Can't locate
  revision") → la API no arranca. Opciones, de menor a mayor impacto:
  1. Volver a un commit **que conserve** el fichero de migración (p. ej. revertir solo el
     código de la feature y mantener `alembic/versions/20261103140000_*.py`).
  2. Cambiar temporalmente el `command` del compose a `uvicorn app.main:app --host 0.0.0.0
     --port 8000 --workers 2` (sin alembic; ver el comentario del propio compose) y
     restaurar después.
  3. Solo si es imprescindible: `alembic downgrade 20261103120000` **antes** de volver al
     commit anterior. Borra `deal_submissions` y las columnas `deals.canonical_url` /
     `coupon_code`: **pérdida de las propuestas** existentes.
- Recordar que el reinicio del contenedor usa la rama activa en la copia de trabajo (ver
  aviso inicial); cambiar de rama sin reconstruir deja la imagen y el código desfasados.

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
