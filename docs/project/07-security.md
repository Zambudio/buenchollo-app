# 🛡️ 07 · Seguridad operativa

> **TL;DR** · Controles aplicados (auth, rate limit, headers, RLS,
> SSRF allowlist), comandos de auditoría, política `--no-verify` y
> plan de respuesta a incidentes. La auditoría OWASP completa vive en
> [`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md).

---

## 🔐 Controles implementados

### 🔑 Autenticación y autorización

- 🔐 **Supabase Auth** (Google OAuth + email). Recovery, rate limit y
  políticas anti-bruteforce gestionadas por Supabase.
- 🎫 **Validación JWT** en cada request al backend
  (`get_current_user → supabase.auth.get_user()`). No se confía en
  flags del cliente.
- 🛠️ **Rol admin** consultado directamente a `user_roles` con SQL
  parametrizado. **47 ocurrencias** de `require_admin` /
  `get_current_user` en los routers.
- 🤝 **Ownership check** en `delete_comment` (sólo el autor borra).
- 🚪 **ADR-002**: frontend nunca habla con la BD de Supabase
  directamente.

### 🛡️ Defensa en profundidad

#### ⏱️ Rate limiting (SlowAPI por IP real de Cloudflare)

La clave es `CF-Connecting-IP` (Cloudflare la sobrescribe) y, si no existe, la IP
del peer. **Nunca** se lee `X-Forwarded-For`: el cliente podía falsificarlo y saltarse
el límite. Supuesto: la API solo es alcanzable a través del Cloudflare Tunnel; si el
puerto publicado en el NAS (`8001:8000`) se alcanza desde la LAN, `CF-Connecting-IP`
es falsificable (ver recomendación en `08-deployment.md`).

| Endpoint | Límite |
|---|---|
| `POST /v1/deals/comments` | 10/min |
| `POST /v1/deals/{id}/vote` | 30/min |
| `POST /v1/deals/{id}/click` | 60/min |
| `POST /v1/products/preview-from-url` | 10/min (además exige `require_admin` desde 2026-11-07) |
| `POST /v1/telegram/publish` | 5/min |
| `POST /v1/submissions/check-link` | 20/min **por usuario** |
| `POST /v1/submissions` | 10/min **por usuario** |
| `POST /v1/submissions/images` y `/images/from-url` | 30/min **por usuario** cada uno |

Los endpoints de propuestas usan la dependencia `user_rate_limit` (clave `user:{id}`,
misma storage y mismo 429 con `Retry-After` que slowapi). Se evalúa antes de las
demás dependencias, así que una petición limitada no toca la BD. Las peticiones que
fallan la validación (422) también cuentan. El almacenamiento es en memoria por worker
(TD-28).
#### 📋 Audit log

`admin_audit_log` con cada acción admin: `request_id` correlacionable
con Sentry.

#### 🛡️ Security Headers (middleware global)

```http
Content-Security-Policy: script-src 'self'; img-src https: data:; ...
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), geolocation=(), microphone=(), payment=(), usb=()
Strict-Transport-Security: max-age=63072000; includeSubDomains  (sólo prod)
```

#### 🛡️ Security Headers en la web (Worker SSR)

`buenchollo-web/src/start.ts` añade un request middleware global de TanStack
Start que pone en **todas** las respuestas SSR:

```http
X-Frame-Options: DENY
Content-Security-Policy: frame-ancestors 'none'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), geolocation=(), microphone=(), payment=(), usb=()
```

Sin `script-src`: el SSR inyecta scripts inline de hidratación y se rompería
sin nonces. Test: `e2e/security-headers.spec.ts`.

#### 🌐 CORS

Lista explícita, sin reflection en handlers de error, warning al
startup si producción tiene `*`.

#### 🚫 SSRF

`extract_asin_from_url` con allowlist Amazon + bloqueo IPs privadas
(RFC1918, loopback, link-local).
La comprobación vive en `core/ssrf.py` (también CGNAT y multicast) y la usan el cliente de
Amazon y el fetcher de imágenes; ver la sección "Contenido de usuarios" más abajo.

### 📝 Validación y sanitización

| Capa | Cómo |
|---|---|
| 🐍 **Backend** | Pydantic v2 con `max_length`, `gt`, `ge`, `le` en todos los campos string y numéricos |
| ⚛️ **Frontend** | Zod schemas en `lib/validation/` — doble frontera ([ADR-005](../adr/ADR-005-validacion-doble-frontera.md)) |
| 🎨 **Render** | React escapa por defecto; `react-markdown` SIN `rehype-raw`. No `dangerouslySetInnerHTML` con input usuario |
| 💾 **SQL** | SQLAlchemy ORM + `text(... :param)` parametrizado |

### 🙋 Contenido de usuarios (propuestas de chollos)

Decisiones en [ADR-015](../adr/ADR-015-ingesta-imagenes-backend.md) y
[ADR-016](../adr/ADR-016-propuestas-comunidad-y-afiliados.md); spec en
[`docs/superpowers/specs/2026-11-03-chollos-de-usuarios-design.md`](../superpowers/specs/2026-11-03-chollos-de-usuarios-design.md).

| Riesgo | Control |
|---|---|
| Imagen maliciosa / bomba de descompresión | Pillow re-codifica a WebP (≤ 1600 px, 5 MB, 40 MP); errores del parser → 400; límite de cuerpo ASGI previo al parseo multipart (413 con CORS) |
| SSRF al importar imagen o resolver enlace | `core/ssrf.py` bloquea privadas, loopback, link-local, multicast, CGNAT `100.64.0.0/10` y `192.0.0.0/24`; redirecciones revalidadas (máx. 3); plazo total 20 s. Ventana de DNS rebinding conocida (TD-25) |
| Imágenes externas en fichas públicas | Solo se aceptan URLs del prefijo público de `deal-images/submissions/`; allowlist probada contra `\`, `../` y userinfo |
| Enlaces de afiliado ajenos | `amazon.es` se reescribe con nuestro tag; tags ajenos desaparecen; acortadores genéricos rechazados (400); API no arranca en producción con `AMAZON_AFFILIATE_TAG` vacío |
| Open redirect tras login | El parámetro `redirect` solo admite rutas internas (sanitizador en el frontend, con tests de variantes codificadas) |
| Spam / abuso | 5 pendientes por usuario y 15 / 24 h; perfil completo obligatorio; rate limit por usuario; máx. 8 imágenes |
| Fuga de propuestas no aprobadas | Tabla `deal_submissions` separada con RLS activado; los listados públicos nunca la consultan |
| Inyección en correos | Plantillas `.html.j2` con autoescape de Jinja (`_env` en `emails/application/rendering.py`); el asunto colapsa espacios y saltos de línea con `_one_line` (mismo fichero) |

| SSRF al resolver acortadores de Amazon (`preview-from-url`, `check-link`) | Allowlist de hosts Amazon y bloqueo de IP interna **en cada salto** de redirección (`_AllowlistRedirectHandler` en `products/infrastructure/amazon_client.py`), no solo en la URL final |
| SSRF al pre-descargar la imagen que se sube a Telegram | `TelegramBot._download_image` solo admite `http(s)` hacia IP pública, revalida cada redirección (máx. 3) y corta a 10 MB; si no puede, envía la URL y la descarga Telegram |
| Fuga del token del bot de Telegram | Las excepciones de `requests` incluyen la URL `…/bot<TOKEN>/…`: `TelegramBot._redact` lo sustituye por `<token>` en logs, Sentry y `last_error` (que ve el panel). Sin `logger.exception` con trazas que lo contengan |

Deuda abierta relacionada: TD-24 (imágenes huérfanas), TD-25 (DNS rebinding, también
en la descarga de imágenes para Telegram), TD-29 (cuota no atómica).

### 🔑 Secretos y configuración

- 🚫 `.env` reales NUNCA trackeados; sólo `.env.example` versionado
- 📤 **Entrega del proyecto**: usar el repositorio (clon o `git archive`),
  nunca un ZIP de la carpeta de trabajo. El `.env` real existe en el árbol
  local (no en git) y un ZIP de carpeta lo incluiría, filtrando secretos.
- 🔐 Service role key sólo en backend, anon key sólo en frontend
- 🧪 CI usa env dummy para tests
- 📦 Dependabot semanal con grupos
- 🔒 **RLS Supabase** activado en todas las tablas de `public` (22). Backend
  bypassa con `service_role` por diseño ([ADR-006](../adr/ADR-006-rls-service-role.md)).
  El test `test_migrations_rls.py` verifica que ninguna migración cree una tabla
  de `public` sin RLS (regresión de `scheduled_deals`, ver `PROJECT_STATUS.md`
  § 3.tervicies)

### 📝 Logging y monitoring

- 🔍 `request_id` middleware con ContextVar → cada log lleva el ID
- 🐛 Sentry con `send_default_pii=False`
- 🚫 `logger.debug` NO loguea email (sólo user_id UUID)
- 📋 `admin_audit_log` con `user_id`, `action`, `target_type`,
  `target_id`, `payload`, `request_id`, `created_at`

### 📦 Supply chain

- 🔒 **Lockfiles** versionados
- ✅ **`pip-audit`** sobre `requirements.txt` → **0 CVEs** (tras pin
  `python-multipart==0.0.27`, SEC-01)
- ✅ **`npm audit`** (incluidas dev) → **0** desde 2026-10-27; el CI falla en
  `high` o superior (`npm audit --omit=dev --audit-level=high`)
- 🩹 **Overrides temporales** en `buenchollo-web/package.json`
  (`miniflare.undici`, `@tailwindcss/typography.postcss-selector-parser`):
  parchean deps transitivas fijadas por upstream; retirada en TD-22
- 🐳 Imágenes Docker oficiales (`python:3.11-slim`)
- ⚙️ CI job `security-audit` corre `pip-audit`, `npm audit`, `gitleaks`

---

## 🚨 Política `--no-verify`

> ⚠️ Sólo en emergencia y con justificación en el mensaje del commit:

```bash
git commit --no-verify -m "fix(prod): rollback parche urgente — bypass gate"
git push --no-verify
```

### 📜 Reglas

- ❌ **Nunca en main** si la rama está abierta a otros desarrolladores
- ✅ **El siguiente commit** debe restaurar el estado verde

---

## 🚒 Respuesta a incidentes

### 🔑 Si se filtra una clave

```
1. 🚨 Revocar y regenerar en el proveedor:
        ├── Supabase: Settings → API → Regenerate service_role
        ├── Amazon Creators: developer.amazon.com → regenerar Client ID/Secret
        ├── OpenAI: platform.openai.com → API keys → revocar
        └── Telegram: /revoke al @BotFather
        │
        ▼
2. 🔄 Actualizar .env en el NAS, reiniciar contenedor
        │
        ▼
3. 🔍 Verificar que NO está en git:
        git log --all -p -S "<fragmento_clave>"
        │
        ▼
4. ❗ Si llegó a git → git filter-repo + git push --force + notificar
```

### 🚷 Si se detecta acceso no autorizado

```sql
-- 1. Bloquear usuario en Supabase (SQL Editor)
UPDATE auth.users
SET banned_until = '2099-12-31'
WHERE id = '<uuid>';

-- 2. Revisar admin_audit_log filtrando por user_id
SELECT * FROM admin_audit_log
WHERE user_id = '<uuid>'
ORDER BY created_at DESC;
```

3. **Cruzar `request_id` con Sentry** para reconstruir la cadena.

### 📦 Si una dependencia crítica está vulnerable

```bash
# 1. Aceptar PR de Dependabot si existe, o bump manual
pip install -U <paquete>  # o npm update <paquete>

# 2. Verificar
pip-audit -r requirements.txt --strict
npm audit --omit=dev --audit-level=high

# 3. CI verde + redeploy NAS
```

---

## 🔍 Comandos de auditoría

```bash
# 🐍 Backend Python: CVEs en deps de producción
cd buenchollo-api
python -m pip_audit -r requirements.txt

# ⚛️ Frontend npm: CVEs sólo en producción
cd buenchollo-web
npm audit --omit=dev --audit-level=high

# 🔍 Búsqueda de patrones peligrosos
grep -rn "dangerouslySetInnerHTML\|eval(\|innerHTML" buenchollo-web/src
grep -rn "TODO\|FIXME\|HACK\|XXX" buenchollo-web/src buenchollo-api/app

# 🔑 Verificar que no hay secretos hardcoded
grep -rEn "(SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE_KEY).*=.*['\"][a-zA-Z0-9]{16,}" \
  buenchollo-api/app buenchollo-web/src

# 🛡️ Headers de seguridad de la web en producción
curl -sI https://buenchollotech.com |   grep -iE "content-security|x-frame|x-content-type|referrer|permissions"

# 🛡️ Headers de seguridad (con backend corriendo)
curl -sI http://localhost:8000/health | \
  grep -iE "content-security|x-frame|x-content-type|referrer|permissions"
```

---

## ✅ Estado de seguridad en producción

- [x] `CORS_ORIGINS` limitado a los dominios reales.
- [x] `APP_ENV=production` y `LOG_LEVEL=INFO` en el NAS.
- [x] TLS Full (strict), HSTS, redirección HTTPS y `www` → raíz en Cloudflare.
- [x] API publicada mediante Cloudflare Tunnel, sin puertos abiertos ni DDNS.
- [x] WAF, rate limiting y Bot Fight Mode activos.
- [x] RLS obligatorio para tablas públicas y prueba de regresión de migraciones.
- [x] CI con auditoría de dependencias y escaneo del historial con gitleaks.
- [ ] Activar manualmente la protección de contraseñas filtradas en Supabase Auth (TD-20).
- [ ] Mantener el smoke test de [`docs/reference/SMOKE_TEST.md`](../reference/SMOKE_TEST.md) como comprobación previa a cambios sensibles.

---

## 📚 Documentación relacionada

| Documento | Contenido |
|---|---|
| [`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md) | Auditoría OWASP completa con hallazgos SEC-01 a SEC-09 |
| [`SECURITY.md`](../../SECURITY.md) | Política de divulgación responsable (raíz) |
| [`docs/master/07-seguridad.md`](../master/07-seguridad.md) | Documento detallado de arquitectura de seguridad |

---

<p align="center">
  <a href="06-testing-and-quality.md">← Anterior: Testing y calidad</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="08-deployment.md">Siguiente: Despliegue →</a>
</p>
