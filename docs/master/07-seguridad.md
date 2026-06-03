# 🛡️ 07 · Seguridad

> **TL;DR** · **Security by Design** y **by Default** aplicados desde
> la arquitectura. Auditoría OWASP Top 10 completa con **10 hallazgos
> priorizados** y **6 fixes de severidad media** implementados.
> Resultado: **0 CVEs conocidas** en deps de producción, controles en
> profundidad (rate limit, audit log, CSP, headers, RLS, SSRF
> allowlist).

---

## 🏗️ Security by Design

> _La seguridad no es un parche tardío. Se piensa desde la arquitectura._

| Decisión arquitectónica | Beneficio de seguridad |
|---|---|
| 🚪 **API Gateway** ([ADR-002](../adr/ADR-002-migracion-baas-a-api-gateway.md)): el frontend nunca habla con la BD directamente | Punto único de validación y autorización. Sin lagunas. |
| 🔒 **RLS activado** en las 12 tablas Supabase ([ADR-006](../adr/ADR-006-rls-service-role.md)) | Red de seguridad ante hipotético bypass de la API |
| 🔑 **`service_role` sólo en backend** | El cliente nunca tiene acceso privilegiado a la BD |
| 🛡️ **Validación en doble frontera** ([ADR-005](../adr/ADR-005-validacion-doble-frontera.md)) | El backend nunca confía en datos del cliente |
| ⚠️ **Excepciones de dominio** que no exponen detalles internos | Errores genéricos al cliente, detalle sólo en logs |
| 📋 **Audit log** por acción admin con `request_id` | Trazabilidad forense correlacionada con Sentry |
| 🧬 **Inyección de dependencias con `Depends`** | Auth y autorización son interceptables en un único punto |
| 🐍 **Modular monolito**: un solo proceso, una superficie expuesta | Menos endpoints públicos que una arquitectura distribuida |

---

## ⚙️ Security by Default

> _Los defaults son los seguros. Si alguien copia `.env.example` y
> olvida ajustar, el sistema se comporta de forma defensiva._

| Configuración | Default seguro |
|---|---|
| `CORS_ORIGINS` | `http://localhost:8080` (no `*`). ⚠️ Warning al startup si `APP_ENV=production` y `*` está presente |
| `LOG_LEVEL` | `INFO` — nunca DEBUG (filtra PII) |
| `RATE_LIMIT_ENABLED` | `true` |
| `APP_ENV` | `local` (HSTS y warnings sólo se activan en `production`) |
| `SENTRY_DSN` | vacío → no se inicializa, app funciona normal |
| **Security Headers** | activados desde el momento que el middleware se registra |
| **Cookies de session** | el frontend usa `localStorage` del SDK Supabase (decisión heredada documentada) |
| `python-multipart` | pin `0.0.27` con CVEs resueltas (`pip-audit` 0 vulnerabilidades) |

---

## 🛡️ OWASP Top 10 aplicado

Auditoría completa en
[`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md).

<table>
<thead>
<tr><th>#</th><th>Categoría</th><th>Estado</th><th>Evidencia</th></tr>
</thead>
<tbody>
<tr><td>A01</td><td>Broken Access Control</td><td>🟢</td><td><code>require_admin</code> en 47 ocurrencias, RLS, ADR-002, ownership check en delete_comment</td></tr>
<tr><td>A02</td><td>Cryptographic Failures</td><td>🟢</td><td>JWT validado por Supabase, no passwords propios. Tokens en localStorage mitigado con CSP estricta</td></tr>
<tr><td>A03</td><td>Injection</td><td>🟢</td><td>SQLAlchemy ORM + <code>text(... :param)</code>, Pydantic en entrada, react-markdown sin <code>rehype-raw</code></td></tr>
<tr><td>A04</td><td>Insecure Design</td><td>🟢</td><td>Rate limit, audit log, RLS, SSRF allowlist Amazon</td></tr>
<tr><td>A05</td><td>Security Misconfiguration</td><td>🟢</td><td>CORS lista explícita, sin origin reflection, Security Headers, sin debug en prod</td></tr>
<tr><td>A06</td><td>Vulnerable Components</td><td>🟢</td><td><code>pip-audit</code> 0 CVEs · <code>npm audit --omit=dev</code> sin high+ · Dependabot semanal · CI gatea</td></tr>
<tr><td>A07</td><td>Identification / Auth Failures</td><td>🟢</td><td>Supabase Auth gestiona login/registro/recovery con rate limit</td></tr>
<tr><td>A08</td><td>Software / Data Integrity</td><td>🟢</td><td>Lockfiles versionados, Dependabot, no scripts remotos, imágenes Docker oficiales</td></tr>
<tr><td>A09</td><td>Logging / Monitoring Failures</td><td>🟢</td><td>request_id, Sentry <code>send_default_pii=False</code>, audit_log, no PII en logs DEBUG</td></tr>
<tr><td>A10</td><td>SSRF</td><td>🟢</td><td>Allowlist Amazon + bloqueo IPs privadas en <code>extract_asin_from_url</code></td></tr>
</tbody>
</table>

---

## 🔐 Controles implementados

### 🔑 Autenticación y autorización

```
┌──────────────────────────────────────────────────────────┐
│  Usuario                                                 │
│    │                                                     │
│    │  🌐 Login Google OAuth                              │
│    ▼                                                     │
│  Supabase Auth                                           │
│    │                                                     │
│    │  🎫 Emite JWT                                       │
│    ▼                                                     │
│  Browser (localStorage)                                  │
│    │                                                     │
│    │  📡 Cada request: Authorization: Bearer <JWT>      │
│    ▼                                                     │
│  FastAPI                                                 │
│    │                                                     │
│    ├── get_current_user → supabase.auth.get_user(JWT)  │
│    │   (valida con service_role en cada request)        │
│    │                                                     │
│    └── require_admin → SELECT FROM user_roles            │
│        (consulta directa a BD, no se confía en cliente) │
└──────────────────────────────────────────────────────────┘
```

- 🔐 **47 ocurrencias** de `require_admin` / `get_current_user` en los routers
- 🤝 **Ownership check** en `delete_comment` (sólo el autor borra)
- 🚫 NO se confía en flags del cliente

### ⏱️ Rate limiting (SlowAPI por IP)

| Endpoint | Límite |
|---|---|
| `POST /v1/deals/comments` | 10/min |
| `POST /v1/deals/{id}/vote` | 30/min |
| `POST /v1/deals/{id}/click` | 60/min |
| `POST /v1/products/preview` | 10/min |
| `POST /v1/telegram/publish` | 5/min |

Respeta `X-Forwarded-For` cuando el proxy lo añade.

### 🛡️ Security Headers (middleware global)

```http
Content-Security-Policy: script-src 'self'; img-src https: data:; ...
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), geolocation=(), microphone=(), payment=(), usb=()
Strict-Transport-Security: max-age=63072000; includeSubDomains  (sólo en producción)
```

### 🚫 SSRF mitigado en preview Amazon

```python
# extract_asin_from_url:
#   1. Allowlist de hosts Amazon (amazon.com, amazon.es, amzn.to, ...)
#   2. Bloqueo de IPs privadas (RFC1918, loopback, link-local)
#   3. Resuelve redirect → re-valida host de destino
```

### 📋 Audit log

```python
# Cada acción crítica del admin:
admin_audit_log(
    user_id=current_user.id,
    action="deal.create",        # qué acción
    target_type="deal",          # sobre qué entidad
    target_id=str(deal.id),      # qué instancia
    payload={...},               # detalles relevantes
    request_id=request_id,       # ← correlacionable con Sentry
)
```

---

## 🚨 Riesgos detectados y mitigaciones

> Auditoría OWASP completa en
> [`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md).
> Todos los hallazgos están resueltos o aceptados conscientemente.

<table>
<thead>
<tr><th>ID</th><th>Categoría</th><th>Severidad</th><th>Estado</th></tr>
</thead>
<tbody>
<tr><td><strong>SEC-01</strong></td><td>python-multipart 0.0.6 con 5 CVEs DoS</td><td>🟡 Media</td><td>✅ Resuelto (pin 0.0.27)</td></tr>
<tr><td><strong>SEC-02</strong></td><td>CORS origin reflection en handler 500</td><td>🟡 Media</td><td>✅ Resuelto (checked contra allowlist)</td></tr>
<tr><td><strong>SEC-03</strong></td><td>Sin Security Headers globales</td><td>🟡 Media</td><td>✅ Resuelto (middleware con CSP + 5 headers)</td></tr>
<tr><td><strong>SEC-04</strong></td><td><code>CORS_ORIGINS=*</code> default peligroso</td><td>🟡 Media</td><td>✅ Resuelto (default sensato + warning startup)</td></tr>
<tr><td><strong>SEC-05</strong></td><td>Schemas Pydantic sin <code>max_length</code></td><td>🟢 Baja</td><td>✅ Resuelto (límites en todos los campos)</td></tr>
<tr><td><strong>SEC-06</strong></td><td>SSRF parcial en preview Amazon</td><td>🟡 Media</td><td>✅ Resuelto (allowlist + bloqueo IPs privadas)</td></tr>
<tr><td><strong>SEC-07</strong></td><td>npm moderate sólo dev-tooling</td><td>🟢 Baja</td><td>🟡 Aceptado (no se usa en prod)</td></tr>
<tr><td><strong>SEC-08</strong></td><td>JWT en localStorage (Supabase SDK)</td><td>🟡 Media</td><td>🟡 Aceptado con mitigación CSP</td></tr>
<tr><td><strong>SEC-09</strong></td><td><code>logger.debug</code> loguea email</td><td>🟢 Baja</td><td>✅ Resuelto (sólo user_id)</td></tr>
<tr><td><strong>SEC-10</strong></td><td>Headers proxy NAS no verificables</td><td>🔵 Info</td><td>📝 Checklist pre-go-live</td></tr>
</tbody>
</table>

---

## 🚒 Plan de respuesta a incidentes

### 🔑 Si se filtra una clave

```
1. 🚨 Revocar y regenerar en el proveedor
       │
       ├── Supabase → Settings → API → Regenerate service_role
       ├── Amazon Creators → developer.amazon.com → regenerar Client ID/Secret
       ├── OpenAI → platform.openai.com → API keys → revocar
       └── Telegram → /revoke al @BotFather
       │
       ▼
2. 🔄 Actualizar .env en el NAS y reiniciar contenedor
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
-- 1. Bloquear usuario en Supabase
UPDATE auth.users
SET banned_until = '2099-12-31'
WHERE id = '<uuid>';

-- 2. Auditar
SELECT * FROM admin_audit_log
WHERE user_id = '<uuid>'
ORDER BY created_at DESC;
```

3. Cruzar `request_id` con Sentry para reconstruir la cadena de eventos.

### 📦 Si una dependencia crítica está vulnerable

```bash
# Aceptar PR de Dependabot, o bump manual:
pip install -U <paquete>  # o npm update <paquete>

# Verificar
pip-audit -r requirements.txt --strict
npm audit --omit=dev --audit-level=high

# CI verde + redeploy NAS
```

---

## 🔭 Mejoras futuras de seguridad

> Detalle en
> [`09 · Limitaciones y mejoras futuras`](09-limitaciones-y-mejoras-futuras.md).

- 🔐 **2FA TOTP** para administradores (configuración externa en Supabase)
- 🤖 **DAST automatizado** con OWASP ZAP en CI
- 📜 **SBOM** con CycloneDX
- 🍪 **Migración JWT a cookies HttpOnly** (alto coste, SDK Supabase no lo soporta idiomáticamente)
- ⚡ **Lighthouse-CI** automatizado para performance budget
- 🛡️ **WAF / Cloudflare front** cuando se mueva al dominio definitivo

---

## 📜 Resumen para evaluación

### ¿Cómo se aplicó Security by Design?

La arquitectura limita la superficie de ataque desde el origen.
ADR-002 prohíbe llamadas directas del frontend a la BD: todo pasa por
la API Gateway FastAPI, donde se valida autenticación y autorización
en cada endpoint. La BD tiene RLS activado en sus 12 tablas
(ADR-006); el backend usa la `service_role` key, que bypassa RLS de
forma controlada y auditada.

### ¿Cómo se aplicó Security by Default?

Los defaults son los seguros: rate limiting activado, audit log de
acciones admin, headers de seguridad globales (CSP, X-Frame-Options,
X-Content-Type-Options, Referrer-Policy, Permissions-Policy), CORS
restringido a la lista de orígenes configurada, errores genéricos al
cliente sin filtrar stack traces.

### ¿Cómo se usó OWASP como marco?

Auditoría completa contra **OWASP Top 10:2021**. Los hallazgos se
documentan en `docs/reference/SECURITY_AUDIT.md` y se han resuelto
los 6 medios identificados. Quedan dos asunciones documentadas
conscientemente (JWT en localStorage por requisito del Supabase JS SDK,
MFA admin no implementado por escala del proyecto).

### ¿Qué amenazas se consideraron?

| Actores | Activos |
|---|---|
| 👤 Visitante anónimo | 🔑 Cuentas |
| 🔑 Usuario registrado | 💰 Ofertas |
| 🛠️ Admin | 🛠️ Panel admin |
| 🤖 Bot/scraper | 🎫 Tokens |
| 😈 Atacante externo | 🔐 Claves API |
| 😈 Admin comprometido | 💾 BD |

Para cada superficie (formularios, endpoints API, rutas admin, login,
integración con APIs externas, despliegue y CI/CD) se han implementado
controles documentados en `docs/reference/SECURITY_AUDIT.md §2`.

### ¿Por qué las decisiones son razonables?

> El proyecto tiene un único administrador (el autor), opera sobre un
> NAS doméstico con tráfico bajo, y maneja datos no críticos
> (ofertas públicas, no datos financieros ni de salud).
>
> El nivel de control aplicado es **proporcional al riesgo real** y
> defendible al nivel **"developer senior con visión de seguridad"**.
> No se exige nivel CISO ni auditoría externa, pero todos los controles
> aplicados son los que un desarrollador profesional aplicaría en un
> producto que va a producción real.

---

<p align="center">
  <a href="06-calidad-testing-y-refactorizacion.md">← Anterior: Calidad y testing</a> ·
  <a href="00-index.md">Índice</a> ·
  <a href="08-uso-de-ia-en-el-desarrollo.md">Siguiente: Uso de IA →</a>
</p>
