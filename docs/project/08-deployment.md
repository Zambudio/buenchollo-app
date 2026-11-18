# 🚀 08 · Despliegue

> **TL;DR** · La web es un Cloudflare Worker que se despliega solo al hacer merge a `main`.
> La API corre en Docker en el NAS Synology, expuesta con Cloudflare Tunnel, y ejecuta el
> **código del share montado**: desplegar es dejar el share en `main` y reiniciar los
> contenedores (o reconstruirlos si cambian las dependencias). Las migraciones Alembic se
> aplican solas al arrancar. La guía viva de Cloudflare es
> [`docs/guides/Cloudflare.md`](../guides/Cloudflare.md) y el acceso al NAS está en
> [`docs/guides/NAS-SSH.md`](../guides/NAS-SSH.md).

---

## 🏠 Arquitectura de producción

```text
Navegador ── HTTPS ──> Cloudflare Worker (frontend SSR)
    │
    └────── HTTPS ──> Cloudflare Tunnel ──> buenchollo-api (NAS)
                                              │
                                              ├─> buenchollo-scheduler
                                              ├─> PostgreSQL / Supabase Auth y Storage
                                              └─> Amazon · Keepa · IA · Telegram · Sentry
```

Contenedores del stack: `buenchollo-api`, `buenchollo-scheduler` y `cloudflared`. El NAS no
sirve el frontend ni abre puertos en el router.

---

## 🧱 Componentes del despliegue

### 🐳 Dockerfile y Compose

- Imagen base `python:3.11-slim`, dependencias de `requirements.txt` (sin las de desarrollo), usuario no root y `HEALTHCHECK` sobre `/health`.
- `docker-compose.yml` monta el código (`.:/app`) y arranca la API con
  `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`: cada reinicio aplica las migraciones pendientes sin SSH adicional.
- `buenchollo-scheduler` usa el mismo código y `.env` con `python -m app.run_scheduler`. La API lleva `SCHEDULER_ENABLED=false` para que los jobs (revisión de precios, publicaciones programadas, resumen de alertas) no se dupliquen entre sus dos workers.
- El contexto de build excluye `.env`, entornos virtuales y cachés.

### 🛠️ Migraciones (Alembic)

Cadena incremental desde el baseline `20260527120000_baseline.py`. Guía: [`MIGRATIONS.md`](../guides/MIGRATIONS.md).

### 📝 Variables clave del `.env` del NAS

El `.env` del NAS es independiente del local y nunca se versiona (lista completa en [`04-configuration.md`](04-configuration.md)).

| Variable | Valor en producción |
|---|---|
| `APP_ENV` | `production` (con `local` la API acepta CORS desde `localhost` y no envía HSTS) |
| `LOG_LEVEL` | `INFO` |
| `CORS_ORIGINS` | `https://buenchollotech.com,https://www.buenchollotech.com` |
| `SENTRY_DSN` / `SENTRY_ENVIRONMENT` | DSN real / `production` |
| `AMAZON_AFFILIATE_TAG` | Con valor. Solo un valor explícitamente vacío aborta el arranque en producción |
| `TELEGRAM_ENABLED` | `true` (en local y en las pruebas es `false`) |
| `ADMIN_NOTIFICATION_EMAIL` | Buzón que recibe el aviso de cada propuesta de chollo (requiere SMTP) |

Un `docker restart` **no** recarga el `env_file`: tras cambiar el `.env`, recrear con `docker-compose up -d --force-recreate <servicio>`.

---

## 🌐 Frontend: Cloudflare Workers

El frontend es TanStack Start con SSR, desplegado como Worker (`buenchollo-web/wrangler.jsonc`, `main: @tanstack/react-start/server-entry`). El Worker renderiza en el edge y sirve los estáticos de `dist/client`.

```bash
cd buenchollo-web
npm run build      # dist/client (estáticos) + dist/server (Worker SSR)
```

| Opción | Cómo | Previews por rama |
|---|---|---|
| Workers Builds (Git) — **la que se usa** | Repositorio conectado, root `buenchollo-web`, build `npm run build`, deploy `wrangler deploy` | Sí, automáticos |
| Wrangler CLI | `cd buenchollo-web && npx wrangler deploy` | Manual (`--name` distinto) |

Push a `main`: despliegue a producción. Push a otra rama: versión *preview* con su URL `*.workers.dev`.

**Variables de build** (`VITE_*`): se incrustan en el bundle al construir, por eso se definen como *build variables* en el panel de Workers Builds y no existe `.env.production` en el repo.

```
VITE_API_URL=https://api.buenchollotech.com
VITE_SUPABASE_URL=https://<ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<anon key, pública por diseño>
```

**Dominio y DNS**: `buenchollotech.com` y `www` son *Custom Domains* del Worker (Cloudflare crea los registros). `api` apunta al Tunnel. TLS, redirecciones y WAF: [`Cloudflare.md`](../guides/Cloudflare.md).

**Supabase Auth → URL Configuration**: Site URL `https://buenchollotech.com` y Redirect URLs `https://buenchollotech.com/**` y `https://www.buenchollotech.com/**`, sin `localhost`. Sin ellas, Google OAuth vuelve al Site URL en lugar de a la página de origen.

---

## 🚀 Desplegar la API en el NAS

El NAS ve el share de red en tiempo real y los contenedores montan esa carpeta, por lo que la **rama activa del share es la que ejecuta producción** en cuanto se reinicia un contenedor. Por eso el share debe estar siempre en `main` y nunca se cambia de rama allí para probar (usa un clon local; ver [`LOCAL-ENV.md`](../guides/LOCAL-ENV.md)). El NAS no tiene `git`: el `git pull` se hace desde la máquina de trabajo sobre el share.

1. **Merge a `main`** con el CI en verde. La web se redespliega sola; hasta que la API se actualice, las pantallas nuevas pueden llamar a endpoints que todavía no existen (ventana de minutos). Si hay migraciones o endpoints nuevos, actualiza la API justo después del merge.
2. **Backup previo** de la base de producción, siempre antes de aplicar migraciones:
   `pg_dump -Fc` con cliente PostgreSQL 17 y comprobación con `pg_restore -l`. Guarda el volcado en `<RUTA_BACKUPS>` y verifica que existe. El `.env` guarda `DATABASE_URL` entre comillas y `--env-file` las conserva: quítalas antes de validar el esquema de la URL. Ejecuta los scripts remotos desde Bash con heredoc; canalizarlos desde PowerShell añade BOM y CRLF.
3. **Actualizar el share a `main`**: para el entorno local si está arrancado sobre el share y haz `git pull --ff-only` en `main`.
4. **Aplicar el cambio** por SSH ([`NAS-SSH.md`](../guides/NAS-SSH.md) §1.1):
   - Sin dependencias nuevas: `docker restart buenchollo-api buenchollo-scheduler`.
   - Con cambios en `requirements.txt` o `Dockerfile`: `docker-compose build && docker-compose up -d`. Un reinicio simple no basta: la imagen antigua no tendría las dependencias nuevas y la API no arrancaría.
5. **Verificar**:
   - `https://api.buenchollotech.com/health` (200, `"environment":"production"`) y `/health/ready`.
   - `docker exec buenchollo-api alembic current` apunta a la cabeza esperada.
   - Un endpoint nuevo del cambio y los logs de arranque sin errores.
6. **Anotar** el despliegue en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md) (merge, revisión Alembic, resultado).

> ⚠️ Nunca reinicies los contenedores con el share en una rama distinta de `main` o con código desfasado respecto a la base: el arranque ejecuta Alembic y la API caería con `Can't locate revision` o con `ModuleNotFoundError` si faltan dependencias.

> 🔒 Recomendado, aún sin aplicar: `docker-compose.yml` publica `8001:8000` en el host. El rate limiting confía en `CF-Connecting-IP`, así que un cliente de la LAN que salte Cloudflare podría falsificarla. Enlazar a loopback (`127.0.0.1:8001:8000`) no afecta a `cloudflared`, que llega por la red de Compose.

---

## ✅ Comprobaciones post-despliegue

- [ ] `https://buenchollotech.com` carga y `https://api.buenchollotech.com/health` responde `200`.
- [ ] Login con Google funciona y una petición autenticada (favoritos, voto) responde bien.
- [ ] Un usuario sin rol admin recibe `403` en `/v1/deals/admin/*`.
- [ ] Los logs del contenedor no muestran errores de CORS.
- [ ] HTTP redirige a HTTPS y las cabeceras de seguridad están presentes:

```bash
curl -sI https://api.buenchollotech.com/health | \
  grep -iE "content-security|x-frame|x-content-type|referrer|permissions|strict-transport"
```

El guion manual completo antes de un release es [`SMOKE-TEST.md`](../guides/SMOKE-TEST.md).

---

## 🔙 Rollback

- **Web**: revertir el merge en `main` (se redespliega sola) o elegir la versión anterior del Worker en Cloudflare.
- **API sin migraciones nuevas**: volver el share al commit anterior de `main` (`git checkout <commit>` desde la máquina de trabajo, no en el NAS) y `docker restart buenchollo-api buenchollo-scheduler`; si cambiaron dependencias, `docker-compose build && docker-compose up -d`. Después, corregir en `develop` y volver a `main` con el arreglo.
- **API con migraciones nuevas**: el arranque ejecuta `alembic upgrade head`, así que el código desplegado debe seguir conteniendo los ficheros de las revisiones aplicadas. Antes de volver al commit anterior, ejecuta `alembic downgrade <revisión anterior>` con el código nuevo todavía en el share. Revisa el `downgrade()` de cada migración: varias eliminan tablas con datos (propuestas, publicaciones de Telegram, votos de producto, catálogo) y esos datos se pierden; el `pg_dump` previo es la red de seguridad. Alternativa sin downgrade: revertir solo el código de la funcionalidad y conservar los ficheros de migración.

---

<p align="center">
  <a href="07-security.md">← Anterior: Seguridad</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="09-troubleshooting.md">Siguiente: Troubleshooting →</a>
</p>
