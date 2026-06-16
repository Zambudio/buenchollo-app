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

#### ⏱️ Rate limiting (SlowAPI por IP, respeta `X-Forwarded-For`)

| Endpoint | Límite |
|---|---|
| `POST /v1/deals/comments` | 10/min |
| `POST /v1/deals/{id}/vote` | 30/min |
| `POST /v1/deals/{id}/click` | 60/min |
| `POST /v1/products/preview` | 10/min |
| `POST /v1/telegram/publish` | 5/min |

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

#### 🌐 CORS

Lista explícita, sin reflection en handlers de error, warning al
startup si producción tiene `*`.

#### 🚫 SSRF

`extract_asin_from_url` con allowlist Amazon + bloqueo IPs privadas
(RFC1918, loopback, link-local).

### 📝 Validación y sanitización

| Capa | Cómo |
|---|---|
| 🐍 **Backend** | Pydantic v2 con `max_length`, `gt`, `ge`, `le` en todos los campos string y numéricos |
| ⚛️ **Frontend** | Zod schemas en `lib/validation/` — doble frontera ([ADR-005](../adr/ADR-005-validacion-doble-frontera.md)) |
| 🎨 **Render** | React escapa por defecto; `react-markdown` SIN `rehype-raw`. No `dangerouslySetInnerHTML` con input usuario |
| 💾 **SQL** | SQLAlchemy ORM + `text(... :param)` parametrizado |

### 🔑 Secretos y configuración

- 🚫 `.env` reales NUNCA trackeados; sólo `.env.example` versionado
- 📤 **Entrega del proyecto**: usar el repositorio (clon o `git archive`),
  nunca un ZIP de la carpeta de trabajo. El `.env` real existe en el árbol
  local (no en git) y un ZIP de carpeta lo incluiría, filtrando secretos.
- 🔐 Service role key sólo en backend, anon key sólo en frontend
- 🧪 CI usa env dummy para tests
- 📦 Dependabot semanal con grupos
- 🔒 **RLS Supabase** activado en las 12 tablas. Backend bypassa con
  `service_role` por diseño ([ADR-006](../adr/ADR-006-rls-service-role.md))

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
- ✅ **`npm audit --omit=dev`** → moderate restantes son dev-tooling
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

# 🛡️ Headers de seguridad (con backend corriendo)
curl -sI http://localhost:8000/health | \
  grep -iE "content-security|x-frame|x-content-type|referrer|permissions"
```

---

## ✅ Checklist pre-go-live al dominio definitivo

Cuando BuenChollo se mueva del DDNS de Synology a su dominio propio:

- [ ] 🌐 `CORS_ORIGINS` con los dominios reales (sin `*`)
- [ ] ⚙️ `APP_ENV=production` para activar HSTS y warning CORS
- [ ] 📝 `LOG_LEVEL=INFO` (nunca DEBUG en prod)
- [ ] 🐛 `SENTRY_DSN` configurado y `SENTRY_ENVIRONMENT=production`
- [ ] 🔒 Certificado Let's Encrypt auto-renovado en reverse proxy NAS
- [ ] 🛡️ HSTS en el reverse proxy con `max-age=63072000; includeSubDomains; preload`
- [ ] 📜 DNS CAA records limitando a Let's Encrypt
- [ ] 🟢 Probar `https://securityheaders.com/` (objetivo: A)
- [ ] 🟢 Probar `https://www.ssllabs.com/ssltest/` (objetivo: A)
- [ ] 🔐 Activar 2FA TOTP en la cuenta de Supabase del admin
- [ ] ✅ Ejecutar [`docs/reference/SMOKE_TEST.md`](../reference/SMOKE_TEST.md) completo

---

## 📚 Documentación relacionada

| Documento | Contenido |
|---|---|
| [`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md) | Auditoría OWASP completa con hallazgos SEC-01 a SEC-09 |
| [`SECURITY.md`](../../SECURITY.md) | Política de divulgación responsable (raíz) |
| [`docs/master/07-seguridad.md`](../master/07-seguridad.md) | Sección académica del módulo |

---

<p align="center">
  <a href="06-testing-and-quality.md">← Anterior: Testing y calidad</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="08-deployment.md">Siguiente: Despliegue →</a>
</p>
