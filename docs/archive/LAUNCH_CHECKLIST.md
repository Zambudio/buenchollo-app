# Checklist de Lanzamiento — BuenCholloTech

Guía paso a paso para pasar la web a producción pública.  
Estado actual: desarrollo en red local / NAS Synology.

---

## FASE 1 — Seguridad (antes de tocar el dominio)

### 1.1 CORS — cambio obligatorio

**Archivo**: `buenchollo-api/.env`

```env
# ❌ Ahora mismo
CORS_ORIGINS=*

# ✅ Producción (poner el dominio real una vez comprado)
CORS_ORIGINS=https://buenchollotech.com,https://www.buenchollotech.com
```

La lógica ya está preparada en `main.py` — cuando no hay `*`, activa `allow_credentials=True` automáticamente.  
No hay que tocar código, solo el `.env`.

---

### 1.2 Rate limiting — añadir slowapi

Actualmente no hay ningún throttling. Con la API pública, los endpoints admin y de votos son vulnerables a abuso.

**Instalar:**
```bash
pip install slowapi
```

**Añadir a `requirements.txt`:**
```
slowapi==0.1.9
```

**Implementación mínima en `buenchollo-api/app/main.py`:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Aplicar en endpoints críticos** (routers de deals, auth):
```python
@router.post("/vote")
@limiter.limit("10/minute")
async def vote(request: Request, ...):
```

**Prioridad de endpoints a limitar:**
- `POST /deals/{id}/vote` — 10/minuto por IP
- `POST /deals/{id}/favorite` — 20/minuto por IP
- `GET /deals` — 60/minuto por IP (scraping)
- `POST /products/preview-from-url` — 30/hora por IP (llama a OpenAI)

---

### 1.3 Variables de entorno — revisión

**Backend** `buenchollo-api/.env`:
- [ ] `APP_ENV=production` — cambiar de `local`
- [ ] `LOG_LEVEL=INFO` — no dejar en `DEBUG` en prod
- [ ] `SUPABASE_KEY` — confirmar que es la **service_role key** (contiene `"role":"service_role"` en el JWT payload)
- [ ] Ningún secreto en el código fuente (ya está bien, solo verificar)

**Frontend** `buenchollo-web/.env` (o `.env.production`):
- [ ] `VITE_API_URL=https://api.tudominio.com` — actualizar con el dominio real
- [ ] `VITE_SUPABASE_URL` — ya es la URL de producción, sin cambios
- [ ] `VITE_SUPABASE_PUBLISHABLE_KEY` — es la anon key, es pública por diseño, correcto

---

### 1.4 Supabase — configuración de Auth

En el **dashboard de Supabase** (`Authentication → URL Configuration`):

- [ ] **Site URL**: `https://tudominio.com`
- [ ] **Redirect URLs**: añadir `https://tudominio.com/**` y `https://www.tudominio.com/**`
- [ ] Eliminar `http://localhost:*` de los redirect URLs (o dejarlo solo para dev)

Sin esto, el login con Google fallará en producción.

---

### 1.5 Supabase — Row Level Security (RLS)

Verificar en el dashboard de Supabase (`Table Editor → cada tabla → RLS`):

- [ ] Tabla `deals` — ¿solo admins pueden insertar/actualizar/eliminar?
- [ ] Tabla `votes` — ¿un usuario solo puede votar/modificar sus propios votos?
- [ ] Tabla `favorites` — ¿un usuario solo puede ver/modificar sus propios favoritos?
- [ ] Tabla `user_roles` — ¿solo service_role puede modificar?

> La API ya valida con `require_admin`, pero RLS es la segunda línea de defensa si alguien llamara a Supabase directamente.

---

### 1.6 Docker — hardening mínimo

**Archivo**: `buenchollo-api/docker-compose.yml`

El volumen actual monta todo el directorio en el contenedor:
```yaml
volumes:
  - .:/app   # ⚠️ En producción esto no es ideal
```

Para producción, mejor que la imagen sea inmutable (sin volumen de código):
```yaml
# Eliminar el volumen de código y el comando override
services:
  buenchollo-api:
    build: .
    container_name: buenchollo-api
    ports:
      - "8001:8000"
    env_file:
      - .env
    restart: always
    # Sin volumes de código, sin command override
```

Con esto la imagen es la que está en el Dockerfile (más seguro y reproducible).

---

### 1.7 HTTPS — forzar en producción

Una vez configurado el reverse proxy en Synology DSM:
- [ ] Redirigir HTTP (80) → HTTPS (443) automáticamente
- [ ] Certificado Let's Encrypt configurado (ver Fase 3)

El backend en sí no necesita cambios — el SSL termina en el reverse proxy.

---

## FASE 2 — Dominio

### 2.1 Comprar el dominio

**Recomendado: Cloudflare Registrar** (https://www.cloudflare.com/products/registrar/)
- Precio de coste (sin margen)
- DNS + CDN + protección DDoS básica en el mismo sitio
- Gestión de DDNS con Cloudflare API fácil de automatizar

**Nombres disponibles probables:**
- `buenchollotech.com`
- `buenchollo.tech`
- `buenchollo.es`

---

### 2.2 Estructura DNS recomendada

Una vez tengas el dominio, crear estos registros DNS en Cloudflare:

| Tipo | Nombre | Valor | Proxy |
|------|--------|-------|-------|
| A | `@` | IP pública del NAS | ✅ Sí |
| A | `www` | IP pública del NAS | ✅ Sí |
| A | `api` | IP pública del NAS | ✅ Sí |
| CNAME | `* ` | `tudominio.com` | ✅ Sí |

Con el proxy de Cloudflare activo, la IP real del NAS queda oculta.

---

### 2.3 IP dinámica — DDNS

Si tu ISP te da IP dinámica (lo habitual en fibra residencial):

**Opción A — Synology DDNS integrado** (si ya lo configuraste antes):
- DSM → `Control Panel → External Access → DDNS`
- Verificar que sigue activo y apuntando bien

**Opción B — Cloudflare DDNS** (recomendado si usas Cloudflare para el dominio):
- Imagen Docker: `oznu/cloudflare-ddns`
- Actualiza el registro A de Cloudflare automáticamente cuando cambia la IP

```yaml
# Añadir al docker-compose del NAS
cloudflare-ddns:
  image: oznu/cloudflare-ddns:latest
  restart: always
  environment:
    - API_KEY=tu_cloudflare_api_token
    - ZONE=tudominio.com
    - SUBDOMAIN=@
```

**Opción C — Cloudflare Tunnel** (sin abrir puertos, más seguro):
Ver sección 3.3.

---

## FASE 3 — Infraestructura NAS

### 3.1 Abrir puertos en el router

Acceder al router de casa y crear reglas de port forwarding:

| Puerto externo | Puerto interno | IP destino | Protocolo |
|----------------|----------------|------------|-----------|
| 80 | 80 | IP del NAS | TCP |
| 443 | 443 | IP del NAS | TCP |

> ⚠️ Algunos ISPs bloquean el puerto 80/443 en tarifas residenciales. Si es el caso, usar Cloudflare Tunnel (sección 3.3) que no requiere abrir puertos.

---

### 3.2 Reverse proxy en Synology DSM

DSM → `Control Panel → Login Portal → Advanced → Reverse Proxy`

Crear dos reglas:

**Regla 1 — Frontend:**
- Source: HTTPS, `tudominio.com`, puerto 443
- Destination: HTTP, `localhost`, puerto del contenedor frontend

**Regla 2 — API:**
- Source: HTTPS, `api.tudominio.com`, puerto 443
- Destination: HTTP, `localhost`, puerto 8001

---

### 3.3 SSL con Let's Encrypt

DSM → `Control Panel → Security → Certificate → Add`
- Seleccionar "Get a certificate from Let's Encrypt"
- Domain name: `tudominio.com`
- Subject Alternative Name: `www.tudominio.com`, `api.tudominio.com`

Se renueva automáticamente cada 90 días.

---

### 3.4 Alternativa: Cloudflare Tunnel (sin abrir puertos)

Si prefieres no tocar el router o el ISP bloquea puertos:

```bash
# En el NAS, con Docker
docker run -d \
  --name cloudflared \
  --restart unless-stopped \
  cloudflare/cloudflared:latest \
  tunnel --no-autoupdate run --token TU_TUNNEL_TOKEN
```

El token se obtiene en Cloudflare Zero Trust → Tunnels → Create tunnel.  
Ventajas: no abres puertos, IP oculta, SSL automático.

---

## FASE 4 — Despliegue final

### 4.1 Build del frontend para producción

```bash
cd buenchollo-web

# Crear .env.production con las variables reales
echo "VITE_API_URL=https://api.tudominio.com" > .env.production
echo "VITE_SUPABASE_URL=https://[ref].supabase.co" >> .env.production
echo "VITE_SUPABASE_PUBLISHABLE_KEY=eyJ..." >> .env.production

# Build
npm run build
# Genera dist/ con los archivos estáticos
```

El `dist/` se sirve con un servidor estático (Nginx en el NAS o el reverse proxy de Synology).

---

### 4.2 Actualizar el backend en el NAS

```bash
# En el NAS, donde está el proyecto
cd /volume1/docker/buenchollo-api

# Actualizar código
git pull

# Editar .env con CORS_ORIGINS real, APP_ENV=production, etc.

# Reconstruir imagen sin el volumen de código
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

### 4.3 Verificación post-despliegue

- [ ] `https://tudominio.com` carga la web correctamente
- [ ] `https://api.tudominio.com/health` responde `{"status": "ok"}`
- [ ] Login con Google funciona (redirección de Supabase Auth)
- [ ] Una petición autenticada funciona (favoritos, votación)
- [ ] Un usuario sin rol admin NO puede acceder a endpoints `/admin/*`
- [ ] Los logs del contenedor no muestran errores CORS
- [ ] HTTP redirige a HTTPS automáticamente

---

## FASE 5 — Post-lanzamiento (semana 1)

- [ ] Monitorizar logs del contenedor los primeros días: `docker logs -f buenchollo-api`
- [ ] Verificar que Let's Encrypt se renueva correctamente (alerta a los 30 días)
- [ ] Revisar si el DDNS sigue actualizado tras un cambio de IP
- [ ] Migrar Telegram de Supabase Functions a `POST /telegram/notify` (pendiente de Fase anterior)
- [ ] Configurar Alembic para gestionar migraciones de BD desde el backend

---

## Resumen de cambios en código

| Archivo | Cambio |
|---------|--------|
| `buenchollo-api/.env` | `CORS_ORIGINS`, `APP_ENV`, `LOG_LEVEL` |
| `buenchollo-api/requirements.txt` | Añadir `slowapi` |
| `buenchollo-api/app/main.py` | Integrar Limiter de slowapi |
| `buenchollo-api/app/modules/deals/api/router.py` | Decoradores `@limiter.limit()` |
| `buenchollo-api/docker-compose.yml` | Eliminar volumen de código en prod |
| `buenchollo-web/.env.production` | `VITE_API_URL` con dominio real |
| Supabase Dashboard | Site URL + Redirect URLs |
