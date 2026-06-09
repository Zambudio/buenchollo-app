# ☁️ Cloudflare — Guía viva de producción (BuenCholloTech)

> **Para qué sirve este archivo**: es nuestro mapa para dejar la web segura y
> estable en producción **sin perder el hilo**. Vamos tarea a tarea; al
> completar cada una, marcamos su casilla `[x]`. No saltarse el orden salvo que
> se indique.

Última actualización: 2026-06-09

---

## 1. 📍 Estado actual

| Pieza | Estado |
|---|---|
| Dominio | ✅ `buenchollotech.com` comprado en Cloudflare Registrar |
| Frontend | ✅ En producción como **Cloudflare Worker** `buenchollotech` (Workers Builds conectado al repo, rama de prod = `main`). Preview: `buenchollotech.pjzambudio.workers.dev` |
| Login Google (Supabase) | ✅ Funciona. Site URL y Redirect URLs ya apuntan a `https://buenchollotech.com` y `https://www.buenchollotech.com` |
| API (FastAPI) | ⏳ En el NAS, aún accesible por `https://embyzambu.synology.me:8000`. **Pendiente** moverla a `api.buenchollotech.com` vía túnel |
| DNS | `www CNAME → buenchollotech.pjzambudio.workers.dev` (proxy ON). `api CNAME → embyzambu.synology.me` (proxy ON) **← a corregir, ver §3** |
| Routes Worker | `buenchollotech.com/*` y `www.buenchollotech.com/*` → Worker |

**Infra de la API (para el túnel):** contenedor Docker `buenchollo-api`,
escucha **interna** en `:8000` (mapeado a `:8001` del host). Healthcheck:
`/health` y `/health/ready`. Rutas de negocio bajo `/v1/`. Admin en
`/v1/deals/admin/*` (protegido por JWT `require_admin`).

---

## 2. 🔄 Forma de trabajo permanente (a partir de ahora SIEMPRE)

```
main     = PRODUCCIÓN  → buenchollotech.com. Solo recibe merges YA validados.
develop  = INTEGRACIÓN/PRUEBAS → cada push genera un preview público *.workers.dev.
           (para tareas concretas se pueden abrir sub-ramas que salen de develop)
```

**Ciclo:** trabajar en `develop` → `git push` → **preview** automático de
Cloudflare → validar en esa URL (la API se prueba en localhost o contra la real)
→ cuando TODO funciona → `merge develop → main` → deploy a producción.

> ⚠️ **Importante**: el preview por rama solo cubre **cambios de ficheros del
> repo** (p.ej. `docker-compose.yml`, docs). Los cambios de **panel Cloudflare /
> NAS** (túnel, TLS, WAF, CORS del `.env` del NAS) se aplican directamente a
> producción — por eso cada tarea de abajo trae su **verificación** y su
> **rollback**. El túnel es *aditivo* (añade `api.`), no rompe lo que ya hay.

> 🔴 **Regla de oro**: nunca commits directos a `main`. Siempre `develop` →
> preview → validar → merge.

---

## 3. ⚠️ 3 correcciones clave del setup actual

1. **Quitar el DNS `api → embyzambu.synology.me` (proxy ON)**. Es del enfoque
   "reverse proxy + abrir puertos", incompatible con el túnel. Cuando creemos el
   túnel y le añadamos el hostname `api.buenchollotech.com`, **Cloudflare crea
   automáticamente** el DNS correcto (CNAME al túnel `…cfargotunnel.com`). → T2.
2. **Con túnel NO hace falta**: abrir puertos, DDNS (da igual la IP dinámica),
   ni certificado de origen. El contenedor `cloudflare-ddns` que dejamos
   preparado **no se usa** en esta vía (queda comentado). El origen deja de
   estar expuesto a Internet = lo más seguro.
3. **NO bloquear `/admin` en el WAF**. El panel admin vive en el frontend
   (`buenchollotech.com/admin`) y la API admin en `api…/v1/deals/admin/*`,
   protegidos por JWT. Bloquear `/admin` en el edge rompería tu propio panel.

---

## 4. 🗺️ Roadmap de tareas

> Marca `[x]` al terminar cada una. Riesgo: 🟢 bajo · 🟡 medio · 🔴 alto.

### ✅ T1 — Crear y desplegar Cloudflare Tunnel para `api.buenchollotech.com` · 🟡 — HECHO (2026-06-09)

**Por qué:** expone la API del NAS sin abrir puertos ni depender de IP fija.

**1.1 Crear el túnel (modo dashboard):**
1. Cloudflare → **Zero Trust** (`one.dash.cloudflare.com`). Primera vez: elige
   nombre de equipo y plan **Free**.
2. **Networks → Tunnels → Create a tunnel** → tipo **Cloudflared** → Next.
3. Nombre: `buenchollo-nas` → **Save tunnel**.
4. Copia el **TUNNEL_TOKEN** (`eyJ...`) que muestra. Guárdalo (irá en Docker).

**1.2 Public Hostname:**
1. En el túnel → **Public Hostnames → Add a public hostname**.
2. Subdomain `api` · Domain `buenchollotech.com` · Path vacío.
3. Type **HTTP** · URL **`buenchollo-api:8000`** (nombre de contenedor + puerto
   interno). **Save hostname**.

**1.3 Desplegar `cloudflared` en el NAS** (añadir al
`buenchollo-api/docker-compose.yml`, mismo proyecto para compartir red Docker):

```yaml
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: buenchollo-cloudflared
    restart: always
    command: tunnel --no-autoupdate run
    env_file:
      - .env
    depends_on:
      - buenchollo-api
```

En el `.env` del NAS: **`TUNNEL_TOKEN=eyJ...`** (cloudflared lee `TUNNEL_TOKEN`
de forma nativa).

> ⚠️ **Aprendido a la fuerza (Synology Container Manager):**
> 1. CM **no interpola** `${VAR}` en el YAML → usar **`env_file`**, no
>    `environment: - X=${VAR}`.
> 2. La variable debe llamarse **`TUNNEL_TOKEN`** (no `CLOUDFLARE_TUNNEL_TOKEN`).
> 3. CM guarda **su propia copia** del compose; editar el fichero en disco no
>    basta — hay que reflejarlo en la pestaña *Configuraciones de YAML*.
> 4. **"Guardar"/"Iniciar" a veces solo REINICIA** el contenedor (conserva el
>    entorno antiguo, token vacío). Para que tome el `.env` nuevo hay que
>    **RECREAR** el contenedor: borrarlo (Contenedor → Eliminar) y recrear, o
>    por SSH `docker compose -p bc-api up -d --force-recreate cloudflared`.
> 5. Verificar que el token entró: `docker exec buenchollo-cloudflared printenv
>    TUNNEL_TOKEN | cut -c1-12`.

**Comprobaciones:**
```bash
curl -s https://api.buenchollotech.com/health        # {"status":"ok"}
docker logs buenchollo-cloudflared                   # "Registered tunnel connection" x4
```
Zero Trust → Tunnels: el túnel debe estar **HEALTHY**.

**Rollback:** parar contenedor `cloudflared` + borrar el public hostname. El
acceso anterior (`embyzambu.synology.me:8000`) sigue intacto por separado.

---

### ✅ T2 — Borrar DNS `api → embyzambu.synology.me` · 🟢 — HECHO (2026-06-09)

**Por qué:** choca con el túnel (corrección §3.1).

**Pasos:** Dashboard → dominio → **DNS → Records**. Borra el CNAME **manual**
`api → embyzambu.synology.me`. Deja el `api` gestionado por el túnel.

**Comprobación:** `curl https://api.buenchollotech.com/health` sigue `{"status":"ok"}`.
**Rollback:** recrear el CNAME manual.

---

### ⬜ T3 — Cutover: frontend → API nueva + cerrar CORS + redeploy · 🟡

**Por qué:** el Worker de prod aún llama a `embyzambu.synology.me:8000`.

**3.1 Variable del Worker:** Workers & Pages → `buenchollotech` → **Settings →
Variables** → `VITE_API_URL` = `https://api.buenchollotech.com` → **redeploy**
(Deployments → Create deployment, o un commit a `main`). Es build-time.

**3.2 CORS + producción en `.env` del NAS:**
```
APP_ENV=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://buenchollotech.com,https://www.buenchollotech.com
```
Reiniciar API: `docker-compose up -d buenchollo-api`.

**Comprobaciones:** `https://buenchollotech.com` carga chollos; F12 → Network →
llamada a `api.buenchollotech.com/v1/...` con `access-control-allow-origin:
https://buenchollotech.com`; logs del NAS sin warning de `CORS=*`.
**Rollback:** volver `VITE_API_URL` a la URL anterior y `CORS_ORIGINS=*`, redeploy.

---

### ⬜ T4 — TLS / Edge security · 🟢 (🟡 solo si activas HSTS preload)

Dashboard → **SSL/TLS**:

| Ajuste | Dónde | Valor |
|---|---|---|
| Encryption mode | SSL/TLS → Overview | **Full (strict)** (NUNCA "Flexible") |
| Always Use HTTPS | Edge Certificates | **ON** |
| Automatic HTTPS Rewrites | Edge Certificates | **ON** |
| Minimum TLS Version | Edge Certificates | **TLS 1.2** |
| HSTS | Edge Certificates → Enable HSTS | Max-Age **6 months**, Include subdomains **OFF**, **Preload OFF** |

> ⚠️ **No actives Preload** hasta estar 100% seguro (es semi-irreversible). La
> API ya emite HSTS en producción; que coincida con el edge no pasa nada.

**Comprobaciones:**
```bash
curl -sI https://buenchollotech.com | findstr /I "strict-transport"
curl -sI http://buenchollotech.com            # 301 → https
```
**Rollback:** desactivar HSTS (sin preload, basta apagarlo).

---

### ⬜ T5 — Redirect `www → raíz` (301) · 🟢

**Por qué:** una URL canónica (`buenchollotech.com`), coherente con Supabase.

**Pasos:** **Rules → Redirect Rules → Create rule**:
- When: `Hostname equals www.buenchollotech.com`
- Then: Dynamic → `concat("https://buenchollotech.com", http.request.uri.path)`
  · Status **301** · Preserve query string **ON**.

**Comprobación:** `curl -sI https://www.buenchollotech.com` → `301 location:
https://buenchollotech.com/`.
**Rollback:** borrar la regla.

---

### ⬜ T6 — WAF / Rate limiting / Bots · 🟡

**6.1 Bot Fight Mode:** Security → Bots → **ON** (gratis).

**6.2 Managed Rules:** el *Free Managed Ruleset* ya está activo (mitiga CVEs).
Las reglas OWASP completas son de pago (Pro+). No tocar.

**6.3 Rate limiting (Free incluye 1 regla):** Security → Rate limiting rules →
Create:
- When: `Hostname eq api.buenchollotech.com`
- 100 requests / **10 s** por IP · Action **Block** 60 s. (Empezar holgado.)

**6.4 WAF custom (Free: hasta 5):** Security → WAF → Custom rules:
- `http.host eq "api.buenchollotech.com" and not http.request.method in {"GET" "POST" "PUT" "DELETE" "PATCH" "OPTIONS"}` → **Block**.

> ❌ No bloquear `/admin` ni `/auth` (rompe panel y login).

**Comprobación:** ~150 peticiones rápidas a `api…/health` empiezan a dar `429`;
la web y el login siguen OK.
**Rollback:** desactivar/borrar cada regla.

---

### ⬜ T7 — Caching (SSR) · 🟢

**Qué hacer:** **nada**. El frontend es SSR en el Worker; cachear HTML daría
contenido obsoleto. Cloudflare por defecto no cachea respuestas dinámicas. No
crear Cache Rules sobre `buenchollotech.com`. (Futuro: cachear solo `/assets/*`.)

---

### ⬜ T8 — Tokens / secretos · 🟢

- `TUNNEL_TOKEN` → solo en el `.env` del NAS (gitignored). **No** a git.
- **No** hace falta API Token de Cloudflare (DDNS descartado).
- Rotación: Zero Trust → Tunnels → tu túnel → **Refresh token** → actualizar
  `.env` + reiniciar `cloudflared`.

---

## 5. ✅ Checklist de go-live

```bash
curl -s https://api.buenchollotech.com/health         # {"status":"ok"}
curl -s https://api.buenchollotech.com/health/ready    # {"status":"ready",...}
curl -sI http://buenchollotech.com                     # 301 → https
curl -sI https://www.buenchollotech.com                # 301 → https://buenchollotech.com/
curl -sI https://buenchollotech.com | findstr /I "strict-transport content-security x-frame"
```
- [ ] `https://buenchollotech.com` carga + chollos visibles.
- [ ] Login con Google OK.
- [ ] Petición autenticada (favorito/voto) OK.
- [ ] Usuario sin rol admin → `api…/v1/deals/admin/*` devuelve **403**.
- [ ] Túnel **HEALTHY** en Zero Trust.
- [ ] Logs del NAS sin warning de CORS `*`.

---

## 6. 🎯 10 acciones rápidas (orden recomendado)

1. Zero Trust → Create Tunnel `buenchollo-nas`; copiar TUNNEL_TOKEN.
2. Public Hostname `api.buenchollotech.com` → HTTP → `buenchollo-api:8000`.
3. Añadir servicio `cloudflared` al `docker-compose.yml` + `CLOUDFLARE_TUNNEL_TOKEN` en `.env` del NAS → levantar. Verificar `api…/health`.
4. Borrar DNS manual `api → embyzambu.synology.me`.
5. `VITE_API_URL = https://api.buenchollotech.com` en el Worker → redeploy.
6. `.env` NAS: `APP_ENV=production`, `LOG_LEVEL=INFO`, `CORS_ORIGINS=https://buenchollotech.com,https://www.buenchollotech.com` → reiniciar API.
7. SSL/TLS: Full (strict) + Always Use HTTPS + Auto HTTPS Rewrites + Min TLS 1.2.
8. Redirect Rule `www → buenchollotech.com` (301).
9. HSTS 6m sin preload · Bot Fight Mode ON · Rate limiting `api.` (100/10s).
10. Pasar el checklist de go-live completo → `merge develop → main`.

---

## 7. 📓 Registro de avance (bitácora)

> Anotar aquí fecha + qué se hizo, para no perder el hilo entre sesiones.

- 2026-06-09 — Creada rama `develop` y este `Cloudflare.md`. Pendiente: empezar por T1.
- 2026-06-09 — T1.1 (túnel `buenchollo-nas`) y T1.2 (public hostname `api` →
  `buenchollo-api:8000`) hechos. T2 hecho (borrado DNS `api → synology.me`).
  `cloudflared` añadido al `docker-compose.yml` (pasado de `environment:${}` a
  `env_file`). `.env` del NAS con `TUNNEL_TOKEN`. **T1.3 BLOQUEADO**: el
  contenedor `cloudflared` arranca sin token (`requires the ID or name`) porque
  CM lo **reinicia** en vez de **recrearlo**. Ficheros verificados OK. **Acción
  al volver:** recrear el contenedor (Opción A borrar+recrear en CM, u Opción B
  SSH `docker compose -p bc-api up -d --force-recreate cloudflared`) y verificar
  con `docker exec ... printenv TUNNEL_TOKEN`. Después: T3.
- 2026-06-09 — ✅ **T1 RESUELTO**. Causa final: el `.env` del **NAS** no tenía
  la línea `TUNNEL_TOKEN` (SynologyDrive **no la sincronizó** desde el PC —
  posible conflicto). Solución: añadir `TUNNEL_TOKEN` directamente en el `.env`
  del NAS + `sudo docker compose -p bc-api up -d --force-recreate cloudflared`
  (por SSH). Túnel HEALTHY; `https://api.buenchollotech.com/health` → ok desde
  fuera (pasa por Cloudflare). **T1 y T2 COMPLETADOS.**
  ⚠️ Pendiente investigar: SynologyDrive no sincroniza fiablemente el `.env` al
  NAS → para cambios en el `.env` del NAS, editarlo **directamente en el NAS**.
  🔐 Pendiente: rotar el TUNNEL_TOKEN (quedó en texto plano en el chat).
  **Siguiente: T3** (VITE_API_URL→api.buenchollotech.com + CORS/APP_ENV prod).
