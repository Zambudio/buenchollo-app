# 🚀 08 · Despliegue

> **TL;DR** · Docker Compose en NAS Synology con reverse proxy DSM +
> Let's Encrypt. El contenedor ejecuta `alembic upgrade head` antes
> de uvicorn al arrancar — migraciones automáticas, sin SSH. Para el
> dominio definitivo, Cloudflare + 2FA en Supabase admin.

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

### 🛠️ Migraciones (Alembic)

Convive con SQL histórico pre-2026-05-27 y nuevas migraciones Alembic
desde el baseline `20260527120000_baseline.py` (vacío, marca el punto
de cambio de formato).

> 📚 Detalle: [`buenchollo-api/MIGRATIONS.md`](../../buenchollo-api/MIGRATIONS.md).

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

## 🌐 Frontend en producción

### 📦 Build estático

```bash
cd buenchollo-web

# Crear .env.production con valores reales
echo "VITE_API_URL=https://api.tudominio.com" > .env.production
echo "VITE_SUPABASE_URL=https://<ref>.supabase.co" >> .env.production
echo "VITE_SUPABASE_PUBLISHABLE_KEY=eyJ..." >> .env.production

npm run build
# Genera dist/ con los archivos estáticos
```

### 🌍 Dónde servir `dist/`

| Opción | Cuándo |
|---|---|
| 🏠 Reverse proxy del NAS apuntando a Nginx local | Coste cero, control total |
| ☁️ Cloudflare Pages / Vercel / Netlify | CDN global, ideal si la audiencia es internacional |

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

### 🌐 DNS (Cloudflare recomendado)

| Tipo | Nombre | Valor | Proxy |
|---|---|---|---|
| A | `@` | IP pública del NAS | ✅ |
| A | `www` | IP pública del NAS | ✅ |
| A | `api` | IP pública del NAS | ✅ |

> 💡 Con proxy de Cloudflare activo, la IP real del NAS queda oculta
> y ganamos CDN + protección DDoS básica.

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
