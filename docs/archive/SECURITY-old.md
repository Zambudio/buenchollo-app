# Security Policy — BuenCholloTech

> Política de seguridad del proyecto, controles implementados, deuda
> asumida y respuesta ante incidentes.
>
> *Última actualización: 2026-06-02 (post-sprint de seguridad).*
> *Auditoría detallada en [`docs/SECURITY_AUDIT.md`](SECURITY_AUDIT.md).*

---

## 1. Divulgación responsable

Si encuentras una vulnerabilidad en BuenCholloTech:

1. **NO** abras un issue público.
2. Manda un correo a `pjzambudio@gmail.com` con asunto
   `[SECURITY] BuenChollo - <título corto>` describiendo el problema,
   pasos para reproducir y, si es posible, una PoC mínima.
3. Compromiso: respuesta inicial en < 7 días, fix coordinado antes de
   divulgación pública.

---

## 2. Controles implementados

### Autenticación y autorización

- **Auth**: Supabase Auth con Google OAuth + email. Recovery, rate
  limit y políticas anti-bruteforce gestionados por Supabase.
- **Validación de JWT**: en cada request al backend, `get_current_user`
  valida el token contra Supabase (`supabase.auth.get_user()`). No se
  confía en flags del cliente.
- **Rol admin**: consulta directa a la tabla `user_roles` con SQL
  parametrizado. 47 ocurrencias de `require_admin`/`get_current_user`
  en los routers del backend.
- **Ownership check**: el endpoint de delete de comentario valida que
  `comment.user_id == current_user.id` antes de borrar.
- **ADR-002**: el frontend NUNCA habla con la BD de Supabase
  directamente. Único intermediario: la API FastAPI con Auth.

### Defensa en profundidad

- **Rate limiting** (SlowAPI por IP, respeta X-Forwarded-For):
  comentarios 10/min, votos 30/min, click tracking 60/min, preview
  Amazon 10/min, publicación Telegram 5/min.
- **Audit log** (`admin_audit_log`) de cada acción admin con
  `request_id`, correlacionable con Sentry.
- **Security Headers** (middleware global):
  - Content-Security-Policy con script-src 'self' (sin unsafe-inline
    de scripts); style-src acepta 'unsafe-inline' por las styles de
    React/shadcn; img-src https: data:; frame-ancestors 'none'.
  - X-Frame-Options: DENY (clickjacking).
  - X-Content-Type-Options: nosniff (MIME sniffing).
  - Referrer-Policy: strict-origin-when-cross-origin.
  - Permissions-Policy: camera/geo/mic/payment/usb deshabilitados.
  - Strict-Transport-Security en producción (max-age 6 meses,
    includeSubDomains).
- **CORS**: lista de orígenes explícita; warning al startup si
  producción tiene `*`. Sin origin reflection en handlers de error.
- **SSRF**: `extract_asin_from_url` con allowlist de hosts Amazon +
  bloqueo de IPs privadas (RFC1918, loopback, link-local). Re-validación
  post-redirect.

### Validación y sanitización

- **Backend**: Pydantic v2 en cada endpoint, con `max_length` y
  constraints numéricos (`gt`, `ge`, `le`) en todos los campos de
  texto y números.
- **Frontend**: Zod en formularios (deals, alerts) — doble frontera
  ADR-005.
- **Render**: React escapa por defecto; `react-markdown` SIN
  `rehype-raw` no permite HTML inline. No se usa `dangerouslySetInnerHTML`
  con input de usuario (sólo en `shadcn/ui/chart.tsx` para CSS variables
  internas).
- **SQL**: SQLAlchemy ORM + `text(... :param)` parametrizado. No queries
  por concatenación.

### Secretos y configuración

- `.env` reales NUNCA trackeados; sólo `.env.example` versionado.
- `.gitignore` excluye `.env*.local`.
- Service role key sólo en backend, anon key sólo en frontend.
- CI usa env dummy para tests (no exponen secretos reales).
- Dependabot semanal con grupos (pip, npm, github-actions).
- **RLS Supabase** activado en las 12 tablas (ver `PROJECT_STATUS.md §3.ter`).
  El backend bypassa RLS usando `service_role` por diseño, manejado vía
  el patrón API Gateway (ADR-006).

### Logging y monitoring

- `request_id` middleware con ContextVar → cada log lleva el ID.
- Sentry con `send_default_pii=False` (no envía cookies/headers/user).
- `logger.debug` no loguea email (sólo user_id UUID).
- Audit log con `user_id`, `action`, `target_type`, `target_id`,
  `payload`, `request_id`, `created_at`.

### Supply chain

- **Lockfiles** versionados: `package-lock.json`, `requirements.txt`
  + `requirements-dev.txt`.
- **`pip-audit`** sobre `requirements.txt` → 0 CVEs conocidas (tras pin
  `python-multipart==0.0.27`).
- **`npm audit --omit=dev`** → moderate restantes son dev-tooling
  (Cloudflare Workers que no se usa para deploy).
- Imágenes Docker oficiales (`python:3.11-slim`).
- Dependabot abre PRs semanales agrupados.

---

## 3. Deuda asumida (decisiones documentadas)

| Item | Por qué | Mitigación actual |
|---|---|---|
| **JWT en `localStorage`** | Default del SDK de Supabase. Cookies HttpOnly requeriría custom storage + endpoint server-side de refresh, complejidad alta. | CSP estricta + ESLint sin `dangerouslySetInnerHTML` ni `eval` reducen drásticamente el riesgo XSS. |
| **MFA admin no implementado en código** | El proyecto tiene 1 administrador (el autor). MFA TOTP se activa en la cuenta de Supabase del propio admin (configuración externa al código). | Recomendado: activar 2FA en https://app.supabase.com/account/security. |
| **`style-src 'unsafe-inline'` en CSP** | React + shadcn inyectan styles inline. Migrar a nonces es un sprint completo. | `script-src 'self'` (sin unsafe-inline) impide cualquier `<script>` inline, que es el vector real. |
| **Validación MIME de uploads server-side** | Sólo admin sube imágenes. Validación se hace en frontend. | Acceptable para el modelo de amenazas actual (admin único de confianza). |
| **Dependencias dev npm con CVEs moderate** | `wrangler`, `miniflare`, `@cloudflare/vite-plugin` no se usan en deploy (NAS Docker, no Cloudflare). | Sólo afectan al entorno de desarrollo. `npm audit fix` opcional cuando Dependabot lo proponga. |

---

## 4. Plan mínimo de respuesta a incidentes

### Si se filtra una clave (.env, GitHub Actions secret, etc.)

1. **Revocar inmediatamente** en el proveedor:
   - Supabase: regenerar `service_role` key en Settings → API.
   - Amazon Creators: regenerar Client ID/Secret en developer.amazon.com.
   - OpenAI: revocar la key en platform.openai.com → API keys.
   - Telegram bot: `/revoke` al @BotFather y reemitir token.
2. Actualizar `.env` en el NAS y reiniciar el contenedor.
3. Auditar `git log -p` y `git log --all -p -S "<fragmento_clave>"` para
   verificar que NO se subió accidentalmente.
4. Si la clave llegó a `git`: forzar `git filter-repo` + push --force +
   notificar a todos los colaboradores.

### Si se detecta acceso no autorizado

1. Marcar usuario `is_blocked` en `auth.users` de Supabase (SQL Editor):
   ```sql
   UPDATE auth.users SET banned_until = '2099-12-31' WHERE id = '<uuid>';
   ```
2. Revisar `admin_audit_log` filtrando por `user_id`:
   ```sql
   SELECT * FROM admin_audit_log
   WHERE user_id = '<uuid>'
   ORDER BY created_at DESC;
   ```
3. Cruzar `request_id` con Sentry para reconstruir la cadena de eventos.
4. Si hubo cambios en `deals`: revisar `updated_at` cercanos al incidente.

### Si una dependencia crítica está vulnerable (CVE high/critical)

1. Aceptar el PR de Dependabot si existe.
2. Si no: bump manual + tests + CI verde + redeploy en NAS.
3. Verificar con `pip-audit -r requirements.txt --strict` y
   `npm audit --omit=dev --audit-level=high`.

---

## 5. Checklist pre-go-live al dominio definitivo

Cuando BuenChollo se mueva del DDNS de Synology a su dominio propio:

- [ ] `CORS_ORIGINS` con los dominios reales (sin `*`).
- [ ] `APP_ENV=production` para activar HSTS y el warning de CORS.
- [ ] `LOG_LEVEL=INFO` (nunca DEBUG en prod — fuga de PII).
- [ ] `SENTRY_DSN` configurado y `SENTRY_ENVIRONMENT=production`.
- [ ] Certificado Let's Encrypt auto-renovado configurado en el reverse
      proxy del NAS.
- [ ] HSTS en el reverse proxy (además del backend) con
      `max-age=63072000; includeSubDomains; preload` cuando se confirme
      que todo funciona vía HTTPS.
- [ ] DNS CAA records limitando a Let's Encrypt.
- [ ] Probar `https://securityheaders.com/` contra el dominio.
- [ ] Probar `https://www.ssllabs.com/ssltest/` contra el dominio
      (objetivo: grado A).
- [ ] Activar 2FA TOTP en la cuenta de Supabase del admin.
- [ ] Smoke test manual (`docs/SMOKE_TEST.md`).

---

## 6. Comandos de auditoría

```bash
# Backend Python: CVEs en dependencias de producción
cd buenchollo-api
python -m pip_audit -r requirements.txt

# Frontend npm: CVEs sólo en producción (ignora dev-tooling)
cd buenchollo-web
npm audit --omit=dev --audit-level=high

# Búsqueda de patrones peligrosos en código
grep -rn "dangerouslySetInnerHTML\|eval(\|innerHTML" buenchollo-web/src
grep -rn "TODO\|FIXME\|HACK\|XXX" buenchollo-web/src buenchollo-api/app

# Verificar que no hay secretos hardcoded
grep -rEn "(SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE_KEY).*=.*['\"][a-zA-Z0-9]{16,}" \
  buenchollo-api/app buenchollo-web/src

# Comprobación de headers de seguridad (con backend corriendo)
curl -sI http://localhost:8000/health | grep -iE "content-security|x-frame|x-content-type|referrer|permissions"
```

---

## 7. Defensa ante el tribunal (resumen)

> *Versión completa en [`SECURITY_AUDIT.md §14`](SECURITY_AUDIT.md#14-defensa-ante-el-tribunal-borrador).*

- **Security by Design**: arquitectura de API Gateway (ADR-002) que limita
  la superficie. RLS activado en las 12 tablas Supabase (ADR-006). Service
  role bypass controlado.
- **Security by Default**: rate limiting, audit log, Security Headers,
  CORS restringido, errores genéricos al cliente.
- **OWASP Top 10 como marco**: auditoría completa documentada en
  `SECURITY_AUDIT.md`. 6 hallazgos medios resueltos en commits separados.
  2 puntos como deuda asumida con justificación.
- **Amenazas consideradas**: usuarios maliciosos autenticados, bots/
  scrapers, atacantes externos, admin comprometido, SSRF, XSS,
  clickjacking, exposición de PII.
- **Controles implementados**: auth JWT validada server-side,
  autorización por rol con SQL directo (no se confía en cliente),
  rate limiting por IP, audit log con request_id, CSP + Security
  Headers, validación Pydantic+Zod, SQL parametrizado, secrets en
  `.env` no trackeados, Dependabot semanal, CI con audit (S7),
  RLS Supabase.
- **Mejoras futuras**: 2FA TOTP para admin, migración JWT a cookies
  HttpOnly cuando Supabase JS SDK lo soporte idiomáticamente, DAST
  con OWASP ZAP, SBOM con CycloneDX.

---

*Mantenedor: Pedro Zambudio — pjzambudio@gmail.com*
