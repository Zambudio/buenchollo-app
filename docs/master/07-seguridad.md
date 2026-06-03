# 07 — Seguridad

## Security by Design

La seguridad se ha planteado desde la fase de arquitectura, no como
parche tardío. Las decisiones de diseño que limitan la superficie de
ataque desde el origen:

| Decisión arquitectónica | Beneficio de seguridad |
|---|---|
| **API Gateway** (ADR-002): el frontend nunca habla con la BD directamente | Punto único de validación y autorización. Sin lagunas |
| **RLS activado** en las 12 tablas Supabase (ADR-006) | Red de seguridad ante hipotético bypass de la API |
| **`service_role` sólo en backend** | El cliente nunca tiene acceso privilegiado a la BD |
| **Validación en doble frontera** (Zod + Pydantic, ADR-005) | El backend nunca confía en datos del cliente |
| **Excepciones de dominio** que no exponen detalles internos | Errores genéricos al cliente, detalle sólo en logs |
| **Audit log** por acción admin con `request_id` | Trazabilidad forense correlacionada con Sentry |
| **Inyección de dependencias con `Depends`** (ADR-007) | Auth y autorización son interceptables en un solo punto |
| **Modular monolito**: un solo proceso, una sola superficie expuesta | Menos endpoints expuestos públicamente que una arquitectura distribuida |

## Security by Default

Los defaults son los seguros. Si alguien copia `.env.example` y olvida
ajustar, el sistema se comporta de forma defensiva:

| Configuración | Default seguro |
|---|---|
| `CORS_ORIGINS` | `http://localhost:8080` (no `*`). Warning al startup si `APP_ENV=production` y `*` está presente |
| `LOG_LEVEL` | `INFO` (nunca DEBUG en defaults — DEBUG filtra PII) |
| `RATE_LIMIT_ENABLED` | `true` |
| `APP_ENV` | `local` (HSTS y warnings sólo se activan en `production`) |
| `SENTRY_DSN` | vacío → no se inicializa, app funciona normal |
| Security Headers | activados desde el momento que el middleware se registra |
| Cookies de session | el frontend usa `localStorage` del SDK Supabase (decisión heredada documentada) |
| `python-multipart` | pin `0.0.27` con CVEs resueltas (`pip-audit` 0 vulnerabilidades) |

## OWASP Top 10 aplicado

Auditoría completa en
[`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md).
Resumen del estado actual:

| # | Categoría | Estado | Evidencia |
|---|---|---|---|
| A01 | Broken Access Control | 🟢 OK | `require_admin` en 47 ocurrencias, RLS Supabase, ADR-002, ownership check en delete_comment |
| A02 | Cryptographic Failures | 🟢 OK (con CSP) | JWT validado por Supabase, no passwords propios. Tokens en localStorage mitigado con CSP estricta |
| A03 | Injection | 🟢 OK | SQLAlchemy ORM + `text(... :param)`, Pydantic en entrada, react-markdown sin `rehype-raw`, no `eval`/`innerHTML` |
| A04 | Insecure Design | 🟢 OK | Rate limit, audit log, RLS, SSRF allowlist Amazon |
| A05 | Security Misconfiguration | 🟢 OK | CORS lista explícita, sin origin reflection, Security Headers, sin debug en prod |
| A06 | Vulnerable Components | 🟢 OK | `pip-audit` 0 CVEs, `npm audit --omit=dev` sin high+, Dependabot semanal, CI gatea |
| A07 | Identification/Auth Failures | 🟢 OK | Supabase Auth gestiona login/registro/recovery con rate limit, backend valida JWT en cada call |
| A08 | Software/Data Integrity | 🟢 OK | Lockfiles versionados, Dependabot, no scripts remotos, imágenes Docker oficiales |
| A09 | Logging/Monitoring Failures | 🟢 OK | request_id, Sentry `send_default_pii=False`, audit_log, no PII en logs DEBUG |
| A10 | SSRF | 🟢 OK | Allowlist Amazon + bloqueo IPs privadas en `extract_asin_from_url` |

## Controles implementados

### Autenticación y autorización

- **Supabase Auth** con Google OAuth + email. Recovery, rate limit y
  políticas anti-bruteforce gestionados por Supabase.
- **Validación JWT** en cada request al backend
  (`get_current_user → supabase.auth.get_user()`). No se confía en
  flags del cliente.
- **Rol admin** consultado directamente a `user_roles` con SQL
  parametrizado. 47 ocurrencias de `require_admin`/`get_current_user`
  en los routers del backend.
- **Ownership check** en `delete_comment`: el usuario sólo borra los
  suyos.

### Defensa en profundidad

- **Rate limiting** (SlowAPI por IP, respeta `X-Forwarded-For`):
  comentarios 10/min, votos 30/min, click tracking 60/min, preview
  Amazon 10/min, publicación Telegram 5/min.
- **Audit log** (`admin_audit_log`) de cada acción admin con
  `request_id`, correlacionable con Sentry.
- **Security Headers** (middleware global):
  - `Content-Security-Policy` con `script-src 'self'` (sin
    unsafe-inline de scripts).
  - `X-Frame-Options: DENY`.
  - `X-Content-Type-Options: nosniff`.
  - `Referrer-Policy: strict-origin-when-cross-origin`.
  - `Permissions-Policy` deshabilitando camera/geo/mic/payment/usb.
  - `Strict-Transport-Security` en producción.
- **CORS** lista explícita; sin origin reflection en handlers de error.
- **SSRF**: `extract_asin_from_url` con allowlist de hosts Amazon +
  bloqueo de IPs privadas (RFC1918, loopback, link-local).

### Validación y sanitización

- **Backend**: Pydantic v2 con `max_length`, `gt`, `ge`, `le` en todos
  los campos string y numéricos.
- **Frontend**: Zod schemas — doble frontera (ADR-005).
- **Render**: React escapa por defecto, `react-markdown` sin
  `rehype-raw`. No se usa `dangerouslySetInnerHTML` con input de
  usuario.
- **SQL**: SQLAlchemy ORM + `text(... :param)` parametrizado.

### Secretos y configuración

- `.env` reales NUNCA trackeados (`.gitignore`).
- Service role key sólo en backend, anon key sólo en frontend.
- CI usa env dummy para tests.
- Dependabot semanal.
- RLS Supabase activado en 12 tablas; backend bypassa con
  `service_role` por diseño (ADR-006).

### Logging y monitoring

- `request_id` middleware con ContextVar → cada log lleva el ID.
- Sentry con `send_default_pii=False`.
- `logger.debug` NO loguea email (sólo user_id UUID).
- Audit log con `user_id`, `action`, `target_type`, `target_id`,
  `payload`, `request_id`, `created_at`.

### Supply chain

- Lockfiles versionados.
- `pip-audit -r requirements.txt --strict` → 0 CVEs (tras pin
  `python-multipart 0.0.27`).
- `npm audit --omit=dev` → moderate restantes sólo en dev-tooling
  (Cloudflare Workers que no se usa).
- Imágenes Docker oficiales (`python:3.11-slim`).
- CI job `security-audit` corre `pip-audit`, `npm audit` y
  `gitleaks` en cada push.

## Riesgos detectados y mitigaciones

Hallazgos del sprint de seguridad (S1–S7) y de la auditoría OWASP.
Todos están resueltos. Detalle completo con cómo se explotaba, impacto
y cambio mínimo aplicado en
[`docs/reference/SECURITY_AUDIT.md`](../reference/SECURITY_AUDIT.md).

| ID | Categoría | Severidad | Estado |
|---|---|---|---|
| SEC-01 | `python-multipart 0.0.6` con 5 CVEs DoS | 🟡 Media | ✅ Resuelto (pin 0.0.27) |
| SEC-02 | CORS origin reflection en handler 500 | 🟡 Media | ✅ Resuelto (checked contra allowlist) |
| SEC-03 | Sin Security Headers globales | 🟡 Media | ✅ Resuelto (middleware con CSP + 5 headers) |
| SEC-04 | `CORS_ORIGINS=*` default peligroso | 🟡 Media | ✅ Resuelto (default sensato + warning startup) |
| SEC-05 | Schemas Pydantic sin `max_length` | 🟢 Baja | ✅ Resuelto (límites en todos los campos) |
| SEC-06 | SSRF parcial en preview Amazon | 🟡 Media | ✅ Resuelto (allowlist + bloqueo IPs privadas) |
| SEC-07 | npm moderate sólo dev-tooling | 🟢 Baja | 🟡 Aceptado (no se usa en prod) |
| SEC-08 | JWT en localStorage (Supabase SDK) | 🟡 Media | 🟡 Aceptado con mitigación CSP |
| SEC-09 | `logger.debug` loguea email | 🟢 Baja | ✅ Resuelto (sólo user_id) |
| SEC-10 | Headers proxy NAS no verificables | 🔵 Info | 📝 Checklist pre-go-live |

## Mejoras futuras de seguridad

Documentadas en
[`09-limitaciones-y-mejoras-futuras.md`](09-limitaciones-y-mejoras-futuras.md):

- **2FA TOTP** para administradores (configuración externa en
  Supabase de la cuenta del autor).
- **DAST automatizado** con OWASP ZAP en CI (over-engineering para
  TFM, valor educativo si se añade).
- **SBOM** con CycloneDX (over-engineering para el tamaño actual).
- **Migración JWT a cookies HttpOnly** (alto coste; el SDK Supabase
  no lo soporta idiomáticamente; CSP estricta mitiga).
- **Lighthouse-CI** automatizado para performance budget.
- **WAF / Cloudflare front** (depende del dominio definitivo).

## Plan de respuesta a incidentes

Documentado operativamente en
[`docs/project/07-security.md`](../project/07-security.md). Resumen
del enfoque:

1. **Filtración de clave**: revocar y regenerar en proveedor →
   actualizar `.env` NAS → reiniciar contenedor → verificar `git log`
   y limpiar historial si llegó a commitearse.
2. **Acceso no autorizado**: bloquear usuario en Supabase con
   `banned_until` → auditar `admin_audit_log` filtrando por `user_id`
   → cruzar `request_id` con Sentry para reconstruir.
3. **Dependencia crítica vulnerable**: aceptar PR de Dependabot o bump
   manual → tests + CI verde → redeploy NAS → verificar con
   `pip-audit --strict` y `npm audit --audit-level=high`.

## Defensa ante el tribunal

### ¿Cómo se ha aplicado Security by Design?

La arquitectura limita la superficie de ataque desde el origen.
ADR-002 prohíbe llamadas directas del frontend a la BD: todo pasa por
la API Gateway FastAPI, donde se valida autenticación y autorización
en cada endpoint. La BD tiene RLS activado en sus 12 tablas
(ADR-006); el backend usa la `service_role` key, que bypassa RLS de
forma controlada y auditada. La separación de claves
`anon`/`service_role` evita exposición accidental.

### ¿Cómo se ha aplicado Security by Default?

Los defaults son los seguros: rate limiting activado, audit log de
acciones admin, headers de seguridad globales (CSP, X-Frame-Options,
X-Content-Type-Options, Referrer-Policy, Permissions-Policy), CORS
restringido a la lista de orígenes configurada, errores genéricos al
cliente sin filtrar stack traces.

### ¿Cómo se ha usado OWASP como marco?

Auditoría completa contra OWASP Top 10:2021. Los hallazgos se
documentan en `docs/reference/SECURITY_AUDIT.md` y se han resuelto los
6 medios identificados. Quedan dos asunciones documentadas (JWT en
localStorage por requisito del Supabase JS SDK, MFA admin no
implementado por escala del proyecto).

### ¿Qué amenazas principales se han considerado?

Actores: visitante anónimo, usuario registrado, admin, atacante
externo, bot/scraper, admin comprometido. Activos: cuentas, ofertas,
panel admin, tokens, claves API, BD. Para cada superficie (formularios,
endpoints API, rutas admin, login, integración con APIs externas,
despliegue y CI/CD) se han implementado controles documentados en
[`docs/reference/SECURITY_AUDIT.md §2`](../reference/SECURITY_AUDIT.md).

### ¿Qué controles se han implementado?

Auth JWT validada server-side, autorización por rol con consulta
directa a `user_roles` (no se confía en el cliente), rate limiting por
IP, audit log de acciones admin con `request_id` correlacionable a
Sentry, CSP + Security Headers, validación Pydantic en cada endpoint,
validación Zod en cliente, SQL parametrizado, secrets en `.env` no
trackeados, Dependabot semanal, CI con `pip-audit` + `npm audit` +
`gitleaks`, RLS Supabase, SSRF allowlist.

### ¿Qué queda como mejora futura?

- Migración JWT a cookies HttpOnly cuando el SDK de Supabase lo
  soporte idiomáticamente.
- 2FA TOTP para administradores en el código (hoy es configuración
  externa en Supabase para la cuenta del admin).
- DAST automatizado con OWASP ZAP en CI.
- SBOM con CycloneDX.
- WAF / Cloudflare front cuando se mueva al dominio definitivo.

### ¿Por qué las decisiones son razonables para un proyecto final de máster?

El proyecto tiene un único administrador (el autor), opera sobre un
NAS doméstico con tráfico bajo, y maneja datos no críticos (ofertas
públicas, no datos financieros ni de salud). El nivel de control
aplicado es **proporcional al riesgo real** y defendible al nivel
"developer senior con visión de seguridad". No se exige nivel CISO ni
auditoría externa, pero todos los controles aplicados son los que un
desarrollador profesional aplicaría en un producto que va a producción
real.
