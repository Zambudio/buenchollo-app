# 08 — Despliegue

## Arquitectura actual

```
Usuario (Browser)
        │  HTTPS · puerto 443
        ▼
DDNS Synology (*.synology.me) → IP pública del router doméstico
        │  Port forward → IP del NAS
        ▼
NAS Synology DSM 7.2+ — Reverse Proxy (HTTPS termina aquí)
        │  HTTP interno hacia el contenedor
        ▼
Docker (buenchollo-api) — puerto 8000
        │
        ├──► Supabase PostgreSQL  (aws-0-eu-central-1.pooler.supabase.com:6543, asyncpg + PgBouncer)
        ├──► Supabase Auth        (validación JWT con service_role)
        ├──► Supabase Storage     (imágenes de chollos)
        ├──► Amazon Creators API  (scraping + preview)
        ├──► OpenAI               (copy + categorización)
        └──► Telegram Bot API     (publicación al canal)
```

El frontend se sirve estáticamente desde el mismo NAS (o se puede servir
desde Cloudflare Pages / Vercel si se quiere CDN global).

## Componentes del despliegue

### Dockerfile

- Imagen base: `python:3.11-slim`.
- Instala desde `requirements.txt` (sin las dev deps).
- Copia el código y arranca uvicorn.

### docker-compose.yml

Característica clave: el `command` ejecuta migraciones Alembic antes de
arrancar uvicorn:

```yaml
command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

De esta forma cada vez que el contenedor reinicia, se aplican las
migraciones pendientes automáticamente (Pedro no necesita SSH al NAS).

En desarrollo monta el código como volumen para hot-reload; en
producción la imagen debería construirse sin volumen de código para que
sea inmutable.

### Migraciones (Alembic)

Convive con SQL histórico (pre-2026-05-27) y nuevas migraciones Alembic
desde el baseline `20260527120000_baseline.py` (vacío, marca el punto
de cambio de formato).

Detalle del setup en
[`buenchollo-api/MIGRATIONS.md`](../../buenchollo-api/MIGRATIONS.md).

## Despliegue inicial en NAS Synology

### 1. Preparar archivos en el NAS

1. File Station → carpeta `docker/buenchollo-api/`.
2. Subir todo el contenido de `buenchollo-api/` (excepto `.venv/`, `__pycache__/`).
3. Subir el `.env` real con las credenciales (este sí, los demás no).

### 2. Desplegar con Container Manager (DSM 7.2+)

1. Container Manager → **Proyecto → Crear**.
2. Nombre: `buenchollo-api`.
3. Ruta: la carpeta subida.
4. Modo: **Usar docker-compose.yml existente**.
5. Finalizar → DSM construye la imagen y lanza el contenedor.

### 3. Reverse proxy en DSM

DSM → `Control Panel → Login Portal → Advanced → Reverse Proxy → Create`:

**Regla API**:
- Source: HTTPS, `embyzambu.synology.me`, puerto 8000.
- Destination: HTTP, `localhost`, puerto 8000.

(Si se separa el frontend en otro subdominio, crear regla análoga
apuntándolo al puerto del frontend.)

### 4. SSL con Let's Encrypt

DSM → `Control Panel → Security → Certificate → Add`:
- "Get a certificate from Let's Encrypt".
- Domain: `embyzambu.synology.me`.
- Email del propietario.
- Se renueva automáticamente cada 90 días.

### 5. Verificación

```bash
curl -s https://embyzambu.synology.me:8000/health
# {"status":"ok"}

curl -s https://embyzambu.synology.me:8000/health/ready
# {"status":"ready","db_latency_ms":...,"checks":{...}}
```

## Actualizar el contenedor tras cambios de código

```bash
# En el NAS (o subiendo con SynologyDrive desde el PC):
cd /volume1/docker/buenchollo-api
git pull   # si está versionado en NAS

# Restart simple (si el volumen monta el código → suficiente)
docker-compose restart

# Rebuild (si cambiaron requirements.txt o Dockerfile)
docker-compose build --no-cache
docker-compose up -d
```

El primer arranque tras un rebuild ejecuta automáticamente
`alembic upgrade head` y aplica migraciones pendientes.

## Frontend en producción

Build estático:

```bash
cd buenchollo-web
# Crear .env.production con valores reales
echo "VITE_API_URL=https://api.tudominio.com" > .env.production
echo "VITE_SUPABASE_URL=https://<ref>.supabase.co" >> .env.production
echo "VITE_SUPABASE_PUBLISHABLE_KEY=eyJ..." >> .env.production

npm run build
# Genera dist/ con los archivos estáticos
```

Servir `dist/` desde:
- Reverse proxy del NAS apuntando a Nginx local, o
- Cloudflare Pages / Vercel / Netlify para CDN global.

## Pre-go-live al dominio definitivo

Cuando BuenCholloTech se mueva de DDNS Synology a su propio dominio
(p.ej. `buenchollotech.com`):

### Variables de entorno (.env del NAS)

| Variable | Cambiar a |
|---|---|
| `APP_ENV` | `production` |
| `LOG_LEVEL` | `INFO` |
| `CORS_ORIGINS` | `https://buenchollotech.com,https://www.buenchollotech.com` |
| `SENTRY_DSN` | el DSN real |
| `SENTRY_ENVIRONMENT` | `production` |

### Supabase

Authentication → URL Configuration:
- **Site URL**: `https://buenchollotech.com`.
- **Redirect URLs**: `https://buenchollotech.com/**` y
  `https://www.buenchollotech.com/**`. Eliminar `localhost`.

### DNS (Cloudflare recomendado)

| Tipo | Nombre | Valor | Proxy |
|---|---|---|---|
| A | `@` | IP pública del NAS | ✅ |
| A | `www` | IP pública del NAS | ✅ |
| A | `api` | IP pública del NAS | ✅ |

Con proxy de Cloudflare activo, la IP real del NAS queda oculta y
ganamos CDN + protección DDoS básica.

### IP dinámica → DDNS Cloudflare

Si la IP del router es dinámica, contenedor adicional para actualizar
el registro DNS:

```yaml
cloudflare-ddns:
  image: oznu/cloudflare-ddns:latest
  restart: always
  environment:
    - API_KEY=<token_cloudflare>
    - ZONE=buenchollotech.com
    - SUBDOMAIN=@
```

### Reverse proxy en DSM con dominio nuevo

Mismas reglas que en el setup inicial pero con `buenchollotech.com` y
`api.buenchollotech.com`. El certificado Let's Encrypt cubre ambos
subdominios añadiéndolos como SAN.

### Cloudflare Tunnel (alternativa sin abrir puertos)

Si el ISP bloquea 80/443 o quieres no abrir puertos:

```bash
docker run -d \
  --name cloudflared \
  --restart unless-stopped \
  cloudflare/cloudflared:latest \
  tunnel --no-autoupdate run --token <TUNNEL_TOKEN>
```

Token en `Cloudflare Zero Trust → Tunnels → Create tunnel`. No abres
puertos, IP oculta, SSL automático.

## Hardening pre-go-live

Cubierto en detalle en
[`07-security.md → Checklist pre-go-live`](07-security.md). Resumen:

- HSTS en el reverse proxy con `max-age=63072000; includeSubDomains; preload` (cuando confirmes que todo va por HTTPS).
- CAA records limitando emisión de certificados a Let's Encrypt.
- 2FA TOTP en cuenta de Supabase del admin.
- Probar `securityheaders.com` (objetivo A) y `ssllabs.com/ssltest` (objetivo A).
- Ejecutar [`docs/reference/SMOKE_TEST.md`](../reference/SMOKE_TEST.md) completo.

## Comprobaciones post-deploy

- [ ] `https://tudominio.com` carga la web.
- [ ] `https://api.tudominio.com/health` → `200 {"status":"ok"}`.
- [ ] Login con Google funciona (redirección Supabase Auth).
- [ ] Petición autenticada funciona (favoritos, voto).
- [ ] Usuario sin rol admin **NO** accede a `/v1/deals/admin/*` (debe devolver 403).
- [ ] Logs del contenedor sin errores de CORS.
- [ ] HTTP redirige a HTTPS.
- [ ] Headers de seguridad correctos:

  ```bash
  curl -sI https://api.tudominio.com/health | grep -iE "content-security|x-frame|x-content-type|referrer|permissions|strict-transport"
  ```

## Rollback rápido

Si un release rompe producción:

```bash
cd /volume1/docker/buenchollo-api
git log --oneline -10               # buscar el commit estable previo
git checkout <commit_estable>
docker-compose build --no-cache && docker-compose up -d
```

Tras estabilizar, mergear el fix correcto a `main` y desplegar de nuevo.
