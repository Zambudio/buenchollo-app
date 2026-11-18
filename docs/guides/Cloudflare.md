# ☁️ Cloudflare — Guía operativa de producción (BuenCholloTech)

> Estado real de Cloudflare para la web y la API, con cómo está configurado cada
> ajuste, cómo verificarlo y cómo deshacerlo. Es la guía viva: se actualiza cuando
> cambia el panel o el túnel.

Última revisión: 2026-11-18

---

## 1. 📍 Estado actual

| Pieza | Estado |
|---|---|
| Dominio | `buenchollotech.com`, registrado en Cloudflare Registrar |
| Frontend | **Cloudflare Worker** `buenchollotech` (Workers Builds conectado al repo; producción = rama `main`). Cada push a otra rama genera un preview `*.workers.dev` |
| Login Google (Supabase) | Site URL y Redirect URLs apuntan a `https://buenchollotech.com` y `https://www.buenchollotech.com` |
| API (FastAPI) | En el NAS, expuesta en `https://api.buenchollotech.com` con **Cloudflare Tunnel** (`APP_ENV=production`, CORS cerrado al dominio) |
| DNS | `@` y `www` → Worker (Custom Domain). `api` → túnel (`…cfargotunnel.com`, lo gestiona el propio túnel) |
| Rutas del Worker | `buenchollotech.com/*` y `www.buenchollotech.com/*` |

La API escucha de forma interna en `:8000` (mapeado a `:8001` en el host). Healthchecks: `/health` y `/health/ready`. Rutas de negocio bajo `/v1/`; la administración, en `/v1/deals/admin/*`, protegida por JWT (`require_admin`).

Con el túnel no hace falta abrir puertos, usar DDNS ni certificado de origen: el NAS no queda expuesto a Internet.

## 2. 🔄 Flujo de ramas

```
main     = PRODUCCIÓN. Solo recibe merges ya validados.
develop  = INTEGRACIÓN. Cada push genera un preview público *.workers.dev.
```

Trabajar en `develop`, validar en el preview (la API se prueba en local o contra la real) y hacer `merge develop → main`. Nunca commits directos a `main`.

El preview solo cubre cambios de ficheros del repo. Los cambios de **panel de Cloudflare** o del **`.env` del NAS** (túnel, TLS, WAF, CORS) se aplican directamente a producción: cada ajuste de abajo indica cómo verificarlo y revertirlo.

---

## 3. 🚇 Cloudflare Tunnel

**Cómo está montado**

- Túnel `buenchollo-nas` (Zero Trust → Networks → Tunnels), con el *public hostname* `api.buenchollotech.com` → HTTP → `buenchollo-api:8000` (nombre del contenedor y puerto interno).
- Servicio `cloudflared` en el `docker-compose.yml` del NAS (mismo proyecto, para compartir red Docker):

```yaml
  cloudflared:
    image: cloudflare/cloudflared:2026.10.3
    container_name: buenchollo-cloudflared
    restart: always
    command: tunnel --no-autoupdate run
    env_file:
      - .env
    depends_on:
      - buenchollo-api
```

- `TUNNEL_TOKEN` vive solo en el `.env` del NAS (cloudflared lo lee de forma nativa). Nunca en Git, chat ni logs.

**Trampas de Synology Container Manager**

1. No interpola `${VAR}` en el YAML: usar `env_file`, no `environment: - X=${VAR}`.
2. La variable debe llamarse `TUNNEL_TOKEN`.
3. Container Manager guarda su propia copia del compose: editar el fichero en disco no basta si el proyecto se gestiona desde su interfaz.
4. «Iniciar» o un `docker restart` **no recargan el `env_file`**. Para aplicar un `.env` nuevo hay que **recrear** el contenedor: `docker-compose up -d --no-deps --force-recreate cloudflared` por SSH (rutas y `sudo -n` en [`NAS-SSH.md`](NAS-SSH.md); el proyecto Compose se llama `buenchollo-api`).
5. Para comprobar que el token entró: `docker exec buenchollo-cloudflared printenv TUNNEL_TOKEN | cut -c1-12`.
6. El `.env` del NAS está excluido del sync de SynologyDrive y es independiente del local: se edita directamente en el NAS.

**Comprobar**

```bash
curl -s https://api.buenchollotech.com/health        # {"status":"ok"}
docker logs buenchollo-cloudflared                   # "Registered tunnel connection" x4
```

En Zero Trust → Tunnels el túnel debe figurar como **HEALTHY**.

**Actualizar `cloudflared`**: la imagen está fijada (no `:latest`) y con `--no-autoupdate`, así que actualizar es cambiar el tag en el compose, hacer `pull` y recrear. Mínimo `2026.10.2` por el aviso de certificados intermedios eMudhra/emSign de 2026-10; el NAS corre `2026.10.3` (comprobado el 2026-10-27: 4 conexiones registradas y `/health` en 200).

**Rotar el token** (pendiente, [TD-21](../project/10-technical-debt.md)): el token quedó visible en una conversación y no hay evidencia de rotación. Zero Trust → Tunnels → túnel → *Refresh token*; actualizar el `.env` del NAS y recrear `cloudflared` como arriba; comprobar el health público y anotar aquí la fecha.

**Rollback**: parar el contenedor `cloudflared` y borrar el *public hostname*.

---

## 4. 🔧 Ajustes del panel (vigentes)

### CORS y entorno de la API

En el `.env` del NAS: `APP_ENV=production`, `LOG_LEVEL=INFO` y `CORS_ORIGINS=https://buenchollotech.com,https://www.buenchollotech.com` (lista separada por comas). Tras cambiarlo, **recrear** la API (un reinicio no relee el `.env`). Comprobar en el navegador que las llamadas a `api.buenchollotech.com/v1/...` devuelven `access-control-allow-origin: https://buenchollotech.com` y que los logs no avisan de `CORS=*`.

`VITE_API_URL=https://api.buenchollotech.com` es una variable **de build** del Worker; solo se aplica al construir `main` (los builds de `develop` son previews).

### TLS y seguridad del borde

| Ajuste | Dónde | Valor |
|---|---|---|
| Encryption mode | SSL/TLS → Overview | **Full (strict)** (nunca «Flexible») |
| Always Use HTTPS | Edge Certificates | ON |
| Automatic HTTPS Rewrites | Edge Certificates | ON |
| Minimum TLS Version | Edge Certificates | TLS 1.2 |
| HSTS | Edge Certificates | Max-Age 6 meses, Include subdomains OFF, **Preload OFF** (semi-irreversible) |

```bash
curl -sI https://buenchollotech.com | findstr /I "strict-transport"
curl -sI http://buenchollotech.com            # 301 → https
```

Rollback: desactivar HSTS (sin preload basta apagarlo).

### Redirección `www` → raíz

Rules → Redirect Rules: `Hostname equals www.buenchollotech.com` → dinámica `concat("https://buenchollotech.com", http.request.uri.path)`, estado **301**, conservando la query string. Comprobar: `curl -sI https://www.buenchollotech.com` → `301 location: https://buenchollotech.com/`. Rollback: borrar la regla.

### WAF, rate limiting y bots

- **Bot Fight Mode**: ON (gratis). El *Free Managed Ruleset* ya está activo; las reglas OWASP completas son de pago.
- **Rate limiting** (el plan gratuito incluye una regla): `Hostname eq api.buenchollotech.com`, 100 peticiones / 10 s por IP, acción Block 60 s.
- **WAF custom**: `http.host eq "api.buenchollotech.com" and not http.request.method in {"GET" "POST" "PUT" "DELETE" "PATCH" "OPTIONS"}` → Block. Consecuencia: un `HEAD` a la API da `403`; para comprobar cabeceras usar `curl -D -` y no `curl -I`.
- **No bloquear `/admin` ni `/auth`**: el panel vive en el frontend y la API admin va protegida por JWT; bloquearlos rompería el panel y el login.

Verificación: unas 150 peticiones rápidas a `api…/health` empiezan a devolver `429` y la web y el login siguen bien. Rollback: desactivar o borrar cada regla.

### Caché

- **Web (SSR)**: no se cachea el HTML (daría contenido obsoleto); no crear Cache Rules sobre `buenchollotech.com`.
- **API**: Cache Rule solo para los listados públicos con **rutas exactas** (nunca `starts_with`), en `api.buenchollotech.com`:
  `(http.host eq "api.buenchollotech.com" and http.request.method eq "GET" and http.request.uri.path in {"/v1/deals" "/v1/deals/latest" "/v1/deals/popular" "/v1/categories" "/v1/stores"})` → *Eligible for cache*, Edge TTL «Use cache-control header if present, bypass cache if not» y Browser TTL «Respect origin».
- El origen manda `Cache-Control` explícito (middleware `app/core/cache_headers.py`): `no-store` en todo `/v1`, salvo los cinco listados públicos exactos, que llevan `public, max-age=0, s-maxage=30` (el navegador siempre revalida; solo el borde cachea 30 s).
- **Lección**: una primera regla con `starts_with("/v1/deals")` y TTL fijo cacheaba también endpoints por usuario (`/my-votes`, `/favorites`) y servía contadores obsoletos con F5. Tras editar la regla, hacer *Purge* del hostname de la API.

```bash
# Listado público: public, max-age=0, s-maxage=30 · MISS → HIT
curl -s -o /dev/null -D - https://api.buenchollotech.com/v1/deals | grep -iE "cf-cache-status|cache-control"
# Endpoint por usuario: no-store · nunca HIT
curl -s -o /dev/null -D - -H "Authorization: Bearer <token>" "https://api.buenchollotech.com/v1/deals/my-votes?ids=<id>" | grep -iE "cf-cache-status|cache-control"
```

Rollback: desactivar la regla; el origen sirve igual sin ella.

---

## 5. ✅ Checklist de verificación

```bash
curl -s https://api.buenchollotech.com/health         # {"status":"ok"}
curl -s https://api.buenchollotech.com/health/ready   # {"status":"ready",...}
curl -sI http://buenchollotech.com                    # 301 → https
curl -sI https://www.buenchollotech.com               # 301 → https://buenchollotech.com/
curl -sI https://buenchollotech.com | findstr /I "strict-transport content-security x-frame"
```

- [ ] `https://buenchollotech.com` carga y se ven chollos.
- [ ] Login con Google correcto.
- [ ] Una petición autenticada (favorito o voto) funciona.
- [ ] Un usuario sin rol admin recibe `403` en `api…/v1/deals/admin/*`.
- [ ] El túnel figura como HEALTHY en Zero Trust.
- [ ] Los logs del NAS no avisan de CORS `*`.

---

<p align="center">
  <a href="NAS-SSH.md">🔐 NAS-SSH</a> ·
  <a href="../project/08-deployment.md">🚀 Despliegue</a> ·
  <a href="../project/00-index.md">📘 Operativa</a>
</p>
