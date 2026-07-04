# Auditoría de Seguridad — BuenCholloTech

> **Documento de auditoría — NO implementar nada hasta aprobación de Pedro.**
>
> Fecha: 2026-05-30. Auditor: arquitecto senior de seguridad (AppSec / OWASP / SSDLC).
>
> Alcance: backend FastAPI + frontend React + Supabase Auth/Storage + CI/CD GitHub Actions + despliegue NAS Synology.

---

## 1. Resumen ejecutivo

**Nivel de cumplimiento: 🟡 Medio-Alto.**

El proyecto parte de una postura defensiva razonable gracias al trabajo
previo de hardening (request_id, rate limiting, audit log, validación
JWT contra Supabase, RLS activado en todas las tablas, ADR-002 que
prohíbe llamadas directas a la BD desde el cliente). **No detecto
vulnerabilidades críticas explotables** ni credenciales hardcoded en el
código fuente. Sin embargo, hay **6 hallazgos medios** y varios bajos
que conviene resolver antes de la entrega para dejar una postura de
seguridad sólida.

**Riesgos principales (en orden):**

1. CVE conocida en `python-multipart 0.0.6` (DoS via multipart form
   parsing). Fix trivial: pin a `0.0.27`.
2. CORS origin reflection en el handler de `Exception` (refleja
   `Origin` del request + `Allow-Credentials: true`). Mitigado en la
   práctica porque la app usa JWT en header, no cookies — pero es bad
   practice y se corrige con 2 líneas.
3. **Sin Security Headers** (CSP, X-Frame-Options, X-Content-Type-Options,
   Referrer-Policy, Permissions-Policy). Falta de defensa en profundidad
   ante XSS / clickjacking / MIME sniffing.
4. JWT en `localStorage` (decisión heredada del SDK de Supabase).
   Vulnerable a XSS-roba-token. Mitigación: CSP estricta. Migrar a
   cookies HttpOnly tiene alto coste y no es práctica habitual en
   Supabase JS SDK.
5. `CORS_ORIGINS=*` por defecto en `.env.example`. Riesgo de quedarse
   en producción por descuido. Defaultear a una lista explícita y
   documentar.
6. Schemas Pydantic de `DealCreate` / `DealUpdate` sin `max_length`
   en title, description, affiliate_url. Sólo expone a un admin
   malicioso, pero es bad practice.

**Recomendación general:** Aplicar las 6 mejoras de severidad media en
3-4 commits pequeños y seguros. Documentar el resto como deuda asumida.
Tras esos cambios el proyecto queda con una postura de seguridad
sólida y verificable.

---

## 2. Mapa del sistema y superficie de ataque

### Stack identificado

| Capa | Tecnología | Notas de seguridad |
|---|---|---|
| Frontend | React 19 · TS strict · Vite · TanStack Router/Query | SDK Supabase usa `localStorage` para JWT |
| Backend | FastAPI 0.136 · SQLAlchemy 2 async · asyncpg | SlowAPI, audit_log, request_id, Sentry |
| Auth | Supabase Auth (Google OAuth + email) | Backend valida JWT vía `supabase.auth.get_user()` |
| BD | PostgreSQL gestionado por Supabase | RLS activado en 12 tablas (PROJECT_STATUS §3.ter) |
| Storage | Supabase Storage | Subida directa desde frontend (excepción documentada en ADR-002) |
| External | Amazon Creators API · OpenAI · Telegram Bot API | Credenciales en `.env` del backend, nunca expuestas al cliente |
| Hosting | NAS Synology · Docker container | HTTPS vía DDNS Synology |
| CI/CD | GitHub Actions (pytest + Vitest + Playwright + Dependabot) | Secrets sólo en env del workflow |

### Superficie de ataque

| Área | Riesgo | Controles existentes | Controles faltantes | Severidad |
|---|---|---|---|---|
| `POST /v1/deals/admin/*` | Inyección, abuso CRUD | `require_admin` + audit_log + rate_limit | `max_length` en Pydantic schemas | 🟡 Media |
| `POST /v1/deals/comments` | Spam, XSS en contenido | `get_current_user` + rate_limit 10/min + `max_length=1000` + ownership check al borrar | — | 🟢 Baja |
| `POST /v1/deals/{id}/vote` | Spam, manipulación temperatura | rate_limit 30/min + `get_current_user` | — | 🟢 Baja |
| `POST /v1/deals/{id}/click` | Inflar contadores | rate_limit 60/min (público) | — | 🟢 Baja |
| `POST /v1/products/preview` | SSRF si el ASIN se sustituye por URL | Sólo acepta URLs de Amazon + extract_asin_from_url + rate_limit 10/min | Allowlist de dominios al hacer redirect follow | 🟡 Media |
| `POST /v1/telegram/*` | Spam canal Telegram | `require_admin` + rate_limit 5/min | — | 🟢 Baja |
| Supabase Auth (login/registro/recovery) | Bruteforce, enumeración | Gestionado por Supabase Auth (no FastAPI) | — | 🟢 Baja (delegado) |
| Supabase Storage (upload imágenes) | Subida malware, sobrescritura | Policies de Storage + frontend valida MIME y tamaño | Validación servidor de MIME real (no del header) | 🟡 Media (admin-only) |
| `/admin/*` rutas frontend | Bypass guard | `useAuth` + `useEffect` redirect + backend `require_admin` valida en cada call | — | 🟢 Baja (defense in depth) |
| Tokens en cliente | XSS-roba-token | `localStorage` (Supabase SDK default) | CSP + X-Frame-Options | 🟡 Media |
| `/health` y `/health/ready` | Reconocimiento | Endpoints públicos | Quizá restringir `/health/ready` para no exponer latencia BD | 🟢 Baja |
| Docker / NAS deployment | RCE, escalada | Container Manager Synology + DDNS HTTPS | Verificable manualmente; fuera del scope del repo | 🟡 Media (no verificable) |

---

## 3. Evaluación OWASP Top 10:2021

| # | Categoría | Aplica | Estado | Evidencia | Riesgo | Acción |
|---|---|---|---|---|---|---|
| A01 | Broken Access Control | Sí | 🟢 OK | `require_admin` en 47 ocurrencias, `get_current_user` validation, RLS Supabase activado, ADR-002 (frontend no toca BD), ownership check en `delete_comment` | Bajo | Mantener |
| A02 | Cryptographic Failures | Sí | 🟡 Parcial | JWT validado por Supabase; no passwords propios. **Tokens en localStorage**. Sin HSTS forzado (lo aporta NAS DDNS) | Medio | Añadir Security Headers (CSP/HSTS) |
| A03 | Injection | Sí | 🟢 OK | SQLAlchemy ORM + `text(... :param)` parametrizado; Pydantic en entrada; react-markdown sin `rehype-raw` (no permite HTML inline); no `eval`, no `innerHTML` | Bajo | Mantener |
| A04 | Insecure Design | Sí | 🟡 Parcial | Rate limit, audit log, RLS, expiración Supabase JWT. **Falta CSP** y allowlist de dominios para SSRF en preview | Medio | Añadir CSP + allowlist Amazon |
| A05 | Security Misconfiguration | Sí | 🟡 Parcial | CORS condicional con `*`; **origin reflection en unhandled_exception**; debug off en prod; sin debug routes. **Sin Security Headers** | Medio | Fix CORS reflect + Security Headers |
| A06 | Vulnerable Components | Sí | 🟡 Parcial | `python-multipart 0.0.6` con 5 CVEs; 17 npm moderate (sólo dev tooling) | Medio | Pin `python-multipart 0.0.27` |
| A07 | Identification/Auth Failures | Sí | 🟢 OK | Supabase Auth gestiona login/registro/recovery con rate limit y políticas configurables. Backend valida JWT en cada call. Logout invalida sesión Supabase | Bajo | Mantener |
| A08 | Software/Data Integrity | Sí | 🟢 OK | Lockfile versionado (npm + pip), Dependabot activado, no scripts remotos, imágenes Docker oficiales (`python:3.11-slim`) | Bajo | Mantener |
| A09 | Logging/Monitoring Failures | Sí | 🟢 OK | `request_id` en cada log + Sentry con `send_default_pii=False` + audit_log de acciones admin. **`logger.debug` loguea email del user** (sólo si LOG_LEVEL=DEBUG en prod) | Bajo | Forzar LOG_LEVEL≥INFO en prod |
| A10 | SSRF | Sí | 🟡 Parcial | `extract_asin_from_url` sigue redirect HTTP de URLs Amazon (amzn.to). Sin allowlist explícito de dominios destino, sólo regex del path | Medio | Allowlist + bloquear IPs privadas |

---

## 4. Hallazgos de seguridad

### [SEC-01] CVE en python-multipart 0.0.6 (5 vulnerabilidades conocidas)

- **Severidad**: 🟡 Media
- **Categoría**: Vulnerable Components (OWASP A06)
- **Archivos**: [`buenchollo-api/requirements.txt`](../buenchollo-api/requirements.txt#L10)
- **Evidencia** (output de `pip-audit`):
  ```
  python-multipart 0.0.6 → 5 CVEs:
    PYSEC-2024-38   (fix 0.0.7)
    CVE-2024-53981  (fix 0.0.18)
    CVE-2026-24486  (fix 0.0.22)
    CVE-2026-40347  (fix 0.0.26)
    CVE-2026-42561  (fix 0.0.27)
  ```
- **Riesgo**: DoS via parsing de multipart/form-data. La biblioteca la
  usa FastAPI internamente para procesar form data. Un atacante puede
  enviar payloads especialmente formados que cuelguen el worker.
- **Cómo se explota**: petición HTTP con body multipart malicioso.
  No requiere autenticación. Endpoints públicos que usen `Form()` o
  `UploadFile` son vulnerables. En este proyecto la mayoría usan JSON,
  pero la dep está cargada igualmente.
- **Impacto**: degradación del servicio (Denial of Service).
- **Recomendación**: actualizar a `python-multipart==0.0.27` (o quitar
  el pin y dejar que pip resuelva la última `>=0.0.27,<1`).
- **Cambio mínimo**: 1 línea en `requirements.txt`.
- **Riesgo del cambio**: bajo. La API pública del paquete es estable.
- **Validación**: `pytest -q -m "not integration"` debe seguir verde.
  `pip-audit -r requirements.txt` debe terminar con "No known vulnerabilities".

---

### [SEC-02] CORS origin reflection en handler de Exception genérica

- **Severidad**: 🟡 Media (mitigada por JWT-en-header)
- **Categoría**: Security Misconfiguration (OWASP A05)
- **Archivos**: [`buenchollo-api/app/main.py:140-148`](../buenchollo-api/app/main.py#L140)
- **Evidencia**:
  ```python
  @app.exception_handler(Exception)
  async def unhandled_exception_handler(request: Request, exc: Exception):
      ...
      origin = request.headers.get("origin", "*")  # ← refleja CUALQUIER origin
      return JSONResponse(
          status_code=500,
          content={"detail": "Error interno del servidor"},
          headers=_with_request_id_header({
              "Access-Control-Allow-Origin": origin,             # ← reflejado
              "Access-Control-Allow-Credentials": "true",        # ← true incondicional
          }),
      )
  ```
- **Riesgo**: el handler de 500 emite `Access-Control-Allow-Origin: <cualquier origin>`
  con `Allow-Credentials: true`. Esto permitiría a un sitio malicioso
  leer respuestas si las credenciales fueran cookies. Como en este
  proyecto el JWT viaja en `Authorization: Bearer` (header, no cookie),
  el riesgo real es bajo, pero es un patrón **explícitamente prohibido
  por la spec** y bandera roja en cualquier pentest.
- **Impacto**: bajo en la app actual; alto si en el futuro se migrara
  a cookies de sesión.
- **Recomendación**: usar la misma lógica que el `CORSMiddleware`
  principal (chequear si el origin está en `settings.cors_origins`).
- **Cambio mínimo**: 5 líneas en el handler.
- **Validación**: respuesta 500 con `Origin: https://evil.com` no debe
  llevar `Access-Control-Allow-Origin: https://evil.com`.

---

### [SEC-03] Faltan Security Headers globales

- **Severidad**: 🟡 Media (defensa en profundidad)
- **Categoría**: Security Misconfiguration (OWASP A05)
- **Archivos**: ningún middleware lo aporta. Verificar con curl `/health`.
- **Evidencia**: `grep -r "Content-Security-Policy\|X-Frame-Options" app/` → 0 hits.
- **Riesgo**: el backend responde sin:
  - `Content-Security-Policy` → no hay capa de defensa frente a XSS
    incluso aunque escape escape el render.
  - `X-Frame-Options: DENY` (o `frame-ancestors 'none'` en CSP) →
    clickjacking posible si alguien embebe la web en un iframe.
  - `X-Content-Type-Options: nosniff` → posible MIME confusion.
  - `Referrer-Policy: strict-origin-when-cross-origin` → fuga de URLs
    completas a destinos externos.
  - `Permissions-Policy` → no restringe APIs sensibles del navegador
    (cámara, micrófono, geo, payment).
  - `Strict-Transport-Security` → no fuerza HTTPS si el proxy delante
    no lo añade.
- **Impacto**: ampliaría la ventana de explotación de cualquier XSS o
  permitiría clickjacking.
- **Recomendación**: añadir un `SecurityHeadersMiddleware` mínimo en
  FastAPI que añada estos headers a TODAS las respuestas.
- **Cambio mínimo**: nuevo fichero `app/core/security_headers.py` (~30 líneas)
  registrado en `main.py`.
- **CSP propuesta** (laxa pero útil, hay que ajustar):
  ```
  default-src 'self';
  img-src 'self' data: https://*.amazon.com https://*.media-amazon.com
                  https://m.media-amazon.com https://*.supabase.co;
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  connect-src 'self' https://*.supabase.co https://embyzambu.synology.me:8000;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
  ```
  *(En el frontend, la CSP la sirve el reverse proxy del NAS o el
  hosting; el middleware del backend cubre las respuestas de la API).*
- **Validación**: `curl -I https://api/health` debe mostrar los headers.

---

### [SEC-04] `CORS_ORIGINS=*` como default en `.env.example`

- **Severidad**: 🟡 Media (riesgo de descuido en deploy)
- **Categoría**: Security Misconfiguration (OWASP A05)
- **Archivos**: [`buenchollo-api/.env.example:36`](../buenchollo-api/.env.example#L36)
- **Evidencia**:
  ```
  # ── CORS ───────────────────
  # ...
  CORS_ORIGINS=*
  ```
- **Riesgo**: si Pedro (o futuro mantenedor) hace `cp .env.example .env`
  en producción y no edita el CORS, el backend queda abierto a peticiones
  desde cualquier origen. El código condicional ya neutraliza
  `Allow-Credentials` cuando es `*`, así que el daño real está limitado,
  pero el patrón es peligroso.
- **Recomendación**:
  - Cambiar el default de `.env.example` a `CORS_ORIGINS=http://localhost:8080`.
  - Añadir comentario explícito de qué poner en producción.
  - Añadir un warning a `configure_logging` o al startup: si
    `app_env="production"` y `"*" in cors_origins`, log WARNING.
- **Cambio mínimo**: editar `.env.example` + 4 líneas de warning en `main.py`.

---

### [SEC-05] Schemas Pydantic sin `max_length` en deals

- **Severidad**: 🟢 Baja (admin-only)
- **Categoría**: Insecure Design (OWASP A04)
- **Archivos**: [`buenchollo-api/app/modules/deals/api/schemas.py`](../buenchollo-api/app/modules/deals/api/schemas.py)
- **Evidencia**: `DealCreate.title: str`, `description: str | None`,
  `affiliate_url: str` — sin `Field(max_length=…)`.
- **Riesgo**: un admin malicioso o token comprometido puede meter
  payloads de MB en cada campo. La BD acepta cualquier longitud
  (columnas `String` sin VARCHAR). No es exfiltración pero es bad practice.
- **Impacto**: limitado (sólo admin).
- **Recomendación**: añadir constraints razonables:
  ```python
  title: str = Field(min_length=3, max_length=200)
  description: str | None = Field(default=None, max_length=10_000)
  short_description: str | None = Field(default=None, max_length=300)
  affiliate_url: str = Field(max_length=2048)
  ```
- **Cambio mínimo**: 5-10 líneas en `schemas.py`.
- **Validación**: pytest `test_deals_api.py` (integración).

---

### [SEC-06] SSRF parcialmente mitigado en preview de productos

- **Severidad**: 🟡 Media
- **Categoría**: SSRF (OWASP A10)
- **Archivos**: [`buenchollo-api/app/modules/products/infrastructure/amazon_client.py:60-90`](../buenchollo-api/app/modules/products/infrastructure/amazon_client.py)
- **Evidencia**:
  ```python
  def extract_asin_from_url(url_or_asin: str) -> str | None:
      ...
      request = urllib.request.Request(url_or_asin, headers={"User-Agent": "Mozilla/5.0"})
      with urllib.request.urlopen(request, timeout=10) as response:
          final_url = response.geturl()
      match = ASIN_RE.search(final_url)
  ```
- **Riesgo**: el backend hace `urlopen()` sobre una URL aportada por el
  admin. Si el admin envía `http://192.168.1.1/admin` o `http://localhost:5000`,
  el servidor lo intenta. No hay allowlist de dominios ni bloqueo de
  rangos privados (RFC1918).
- **Cómo se explota**: un admin comprometido podría reconocer la red
  interna del NAS o atacar servicios LAN.
- **Mitigantes existentes**: el endpoint exige `require_admin`,
  `urlopen` no envía Authorization headers automáticamente, `regex`
  exige formato ASIN al final → la respuesta sólo se considera válida
  si el path final coincide con `/dp/[ASIN]/`.
- **Recomendación**:
  - Validar que el dominio del URL inicial está en
    `{"amazon.com", "amazon.es", "amzn.to", "amazon.de", "amazon.co.uk"}`
    antes de hacer el `urlopen`.
  - Tras el redirect, bloquear si la IP resuelta está en rangos privados
    (mejor: tras `socket.gethostbyname()` validar contra `ipaddress.ip_address(...).is_private`).
- **Cambio mínimo**: ~20 líneas en `extract_asin_from_url`.
- **Validación**: test unitario con URL fake `http://localhost/dp/B0XXXXXXXX/`
  debe ser rechazado.

---

### [SEC-07] Vulnerabilidades npm moderate (sólo tooling dev)

- **Severidad**: 🟢 Baja
- **Categoría**: Vulnerable Components (OWASP A06)
- **Archivos**: `buenchollo-web/package-lock.json`
- **Evidencia** (`npm audit`): 17 moderate.
  - `ws@8.0.0-8.20.0`: uninitialized memory disclosure (advisorías GHSA-58qx-3vcg-4xpx)
  - `postcss`, `miniflare`, `wrangler`, `@cloudflare/vite-plugin`
- **Riesgo**: TODAS son dependencias del entorno de dev/build (Cloudflare
  Workers tooling que **el proyecto no usa** para deploy — el deploy
  es Docker en NAS). Producción no las carga.
- **Recomendación**:
  - Ejecutar `npm audit fix` en una PR aparte y verificar que el suite
    completo sigue verde. Dependabot ya está propuesto auto-bumps
    semanales.
  - Considerar **eliminar** `@cloudflare/vite-plugin` si no se va a
    desplegar en Cloudflare (procede del scaffolding inicial del
    proyecto).
- **Cambio mínimo**: opcional, decisión de Pedro.

---

### [SEC-08] JWT del usuario en `localStorage` (decisión heredada de Supabase SDK)

- **Severidad**: 🟡 Media (sin solución sencilla)
- **Categoría**: Cryptographic Failures (OWASP A02)
- **Archivos**: [`buenchollo-web/src/integrations/supabase/client.ts:20`](../buenchollo-web/src/integrations/supabase/client.ts#L20)
- **Evidencia**: `storage: typeof window !== "undefined" ? localStorage : undefined`.
- **Riesgo**: cualquier XSS en la web roba el JWT → la atacante puede
  hacer llamadas a la API como el usuario hasta que el token expire.
- **Mitigantes existentes**: ESLint estricto sin `dangerouslySetInnerHTML`
  ni `eval`, React escapa por defecto, `react-markdown` sin `rehype-raw`.
- **Recomendación**:
  - Aceptar la decisión (cookies HttpOnly con Supabase JS SDK requiere
    custom storage + endpoint server-side de refresh). Documentado en
    SECURITY.md como deuda asumida.
  - **Mitigación real**: añadir CSP estricta (SEC-03) para reducir
    superficie de XSS.
- **Cambio mínimo**: ninguno. Documentar como deuda asumida.

---

### [SEC-09] `logger.debug()` puede loguear PII (email) si LOG_LEVEL=DEBUG

- **Severidad**: 🟢 Baja
- **Categoría**: Logging/Monitoring Failures (OWASP A09)
- **Archivos**: [`buenchollo-api/app/core/security.py:33`](../buenchollo-api/app/core/security.py#L33)
- **Evidencia**:
  ```python
  logger.debug("JWT validado OK — user_id=%s email=%s",
               user_response.user.id, user_response.user.email)
  ```
- **Riesgo**: si el deploy en NAS arranca con LOG_LEVEL=DEBUG, cada
  request loguea email del usuario. Es PII.
- **Recomendación**:
  - Quitar `email` del log (queda con `user_id` que es UUID, suficiente
    para correlacionar y no es PII directa).
  - Documentar en `SECURITY.md` que `LOG_LEVEL` en producción debe ser
    `INFO` o superior.
- **Cambio mínimo**: 1 línea.

---

### [SEC-10] (Informativo) Headers de seguridad del proxy NAS no verificables

- **Severidad**: 🔵 Informativa
- **Categoría**: Infrastructure / Despliegue
- **Evidencia**: el despliegue corre en NAS Synology con DDNS HTTPS.
  No tengo acceso al reverse proxy del NAS para verificar:
  - HSTS (`Strict-Transport-Security: max-age=...; includeSubDomains; preload`)
  - HTTP/2
  - certificado Let's Encrypt auto-renovado
  - rate limiting a nivel de proxy (defensa adicional)
- **Recomendación**: documentar checklist manual en `SECURITY.md`
  para que Pedro verifique antes del go-live al dominio definitivo.

---

## 5. Autenticación y autorización

| Aspecto | Estado |
|---|---|
| Login (Supabase Auth con Google OAuth + email) | ✅ |
| Validación JWT en cada request (`get_current_user` → `supabase.auth.get_user()`) | ✅ |
| Rol admin desde tabla `user_roles` con SQL parametrizado | ✅ |
| No confiar en `isAdmin` del cliente — backend re-valida | ✅ |
| Logout invalida sesión Supabase | ✅ |
| Recovery de contraseña | ✅ gestionado por Supabase |
| Ownership check en `delete_comment` | ✅ |
| Ownership check al votar (`upsert_vote` por `(deal_id, user_id)`) | ✅ |
| Rate limit en endpoints sensibles | ✅ |
| MFA para admin | ⚠️ no implementado. Defendible: el repo es pequeño y el admin es uno solo (Pedro). |
| IDOR en `GET /deals/{slug}` | ✅ Slug público; favoritos por session |
| IDOR en `GET /users/me/*` | ✅ resuelve por `current_user.id`, no por param |

**Veredicto**: postura de auth/authz **sólida**. Nada que añadir
salvo, opcionalmente, recomendar 2FA TOTP a Pedro en su cuenta admin
de Supabase (config externa al código).

---

## 6. Seguridad de APIs

| Aspecto | Estado |
|---|---|
| Versionado `/v1/` | ✅ |
| Autenticación en endpoints protegidos | ✅ |
| Autorización por rol/recurso | ✅ |
| Validación con Pydantic | 🟡 Falta `max_length` en deals — SEC-05 |
| Rate limiting | ✅ SEC-OK |
| Paginación + límites | ✅ `Query(limit=200, ge=1, le=500)` en admin |
| Errores genéricos al cliente | ✅ `unhandled_exception` devuelve "Error interno" |
| CORS restrictivo | 🟡 reflection bug — SEC-02 |
| CSRF | N/A (JWT en header, no cookies) |
| Headers de seguridad | ❌ SEC-03 |
| Eliminación endpoints test/debug | ✅ verificado en sprint anterior |

---

## 7. Validación y sanitización

- ✅ **Body JSON**: Pydantic schemas en CADA endpoint.
- ✅ **Query/Path params**: tipados con `Query(...)`/`Path(...)` con
  rangos.
- ✅ **Frontend forms**: Zod schemas (`deals.ts`, `alerts.ts`)
  validados antes del fetch.
- ✅ **react-markdown**: render sin `rehype-raw` → no HTML inline.
- ✅ **SQL**: SQLAlchemy ORM + `text(... :param)` parametrizado.
- ⚠️ **Uploads**: validación de MIME y tamaño se hace en frontend pero
  Storage de Supabase acepta lo que sea. Defendible porque sólo admin
  sube, pero conviene policy server-side.
- ⚠️ **`extract_asin_from_url`**: confía en URL del admin sin allowlist
  de dominios — SEC-06.

---

## 8. Secretos y configuración

| Check | Resultado |
|---|---|
| `.env` reales no trackeados (git ls-files) | ✅ sólo `.env.example` |
| `.gitignore` excluye `.env*.local` | ✅ |
| Service role key en backend, anon key en frontend | ✅ |
| No claves hardcoded en código fuente | ✅ verificado con grep `SECRET\|TOKEN\|API_KEY\|PRIVATE_KEY` |
| GitHub Actions usa env dummy para tests | ✅ no se exponen secrets reales en logs |
| Separación dev/prod via APP_ENV | ✅ |
| RLS activado en BD (12 tablas) | ✅ documentado en PROJECT_STATUS §3.ter |
| ADR-006 hardening RLS / service_role | ✅ |
| Rotación de claves | ⚠️ no procedimentado — añadir a SECURITY.md |

---

## 9. Dependencias y supply chain

- **Lockfile** versionado: ✅ (`package-lock.json`, `requirements*.txt` con pins).
- **Dependabot** activo: ✅ (`.github/dependabot.yml` semanal con grupos).
- **CVEs detectadas**:
  - Python: **5 en `python-multipart 0.0.6`** → SEC-01 (crítico arreglar).
  - npm: **17 moderate** todas en dev-tooling → SEC-07.
- **Imágenes Docker**: `python:3.11-slim` (oficial, mantenida).
- **Scripts postinstall sospechosos**: ninguno.
- **Dependencias innecesarias detectadas**:
  - `@cloudflare/vite-plugin`, `wrangler`, `miniflare` → no se usan
    para deploy. Considerar eliminar (Pedro decide).
- **SBOM**: no generado. No necesario para TFM; opcional a futuro con
  `cyclonedx-bom`.

---

## 10. Logging y monitoring

| Evento | ¿Se registra? | Notas |
|---|---|---|
| Login fallido | ✅ Supabase Auth (dashboard) | externalizado |
| Login exitoso | ✅ Sentry breadcrumb |
| Acciones admin (create/update/delete deals) | ✅ `admin_audit_log` con `request_id` |
| 4xx por acceso no autorizado | ✅ `domain_exception_handler` INFO log |
| 5xx errores backend | ✅ `unhandled_exception_handler` + Sentry |
| Cambios de rol | ⚠️ no hay UI; se hace en Supabase manualmente |
| Tokens/passwords/secrets en logs | ❌ ninguno (verificado por grep) |
| `email` en logs | ⚠️ SEC-09 sólo a nivel DEBUG |
| Alertas Sentry | ✅ habilitadas en producción |

**Plan mínimo de respuesta a incidentes** (a añadir en `SECURITY.md`):

1. **Si se filtra una key**: revocar y regenerar en Supabase /
   Amazon Creators / OpenAI / Telegram. Reiniciar contenedor.
2. **Si se detecta acceso no autorizado**: marcar usuario `is_blocked`
   en Supabase, revisar `admin_audit_log` cruzando con `request_id`
   en Sentry.
3. **Si una dep crítica está vulnerable**: aceptar PR de Dependabot,
   bumpear, redeploy en NAS.

---

## 11. DevSecOps / Shift Left

**Estado actual del pipeline** (`.github/workflows/ci.yml`):

| Check | Existe |
|---|---|
| Lint frontend | ✅ |
| Typecheck frontend | ✅ |
| Tests backend (pytest) | ✅ |
| Tests frontend (Vitest) | ✅ con coverage threshold CORE 90% |
| E2E (Playwright) | ✅ con artifacts |
| Husky pre-commit (lint + typecheck) | ✅ |
| Husky pre-push (test:run) | ✅ |
| **Dependency audit (`npm audit` / `pip-audit`)** | ❌ — FALTA |
| **Secret scanning** | ❌ — FALTA (gitleaks o trufflehog) |
| **Análisis estático seguridad (bandit / semgrep)** | ❌ — FALTA |
| Dependabot updates semanales | ✅ |
| Protección de ramas | ⚠️ no verificado en GitHub settings |

**Propuesta de checks adicionales** (todos opcionales para TFM):

- Job `security-audit` en CI que corre:
  - `pip-audit -r requirements.txt --strict` (fallar si CVE high+)
  - `npm audit --omit=dev --audit-level=high` (fallar si CVE high+)
  - `gitleaks detect --no-banner` (fallar si encuentra secretos)
  - `bandit -r app/` para análisis estático de seguridad Python

Si se quiere DAST: OWASP ZAP baseline contra `http://localhost:8080`
en CI. Coste +2 min, valor educativo alto para TFM.

---

## 12. Plan de acción priorizado

### 🔴 Imprescindible antes de entregar (4 commits)

1. **SEC-01 — Pin `python-multipart 0.0.27`** (1 línea, 0 riesgo).
   Verificar con `pip-audit` post-fix.
2. **SEC-02 — Fix CORS reflection en handler 500** (5 líneas en `main.py`).
3. **SEC-03 — Añadir `SecurityHeadersMiddleware`** con CSP, X-Frame-Options,
   X-Content-Type-Options, Referrer-Policy, Permissions-Policy
   (~30 líneas nuevas + 2 en `main.py`).
4. **SEC-04 — `CORS_ORIGINS=*` → default sensato + warning en startup**
   (4 líneas en `.env.example` + 5 en `main.py`).

### 🟡 Recomendable antes de entregar (2 commits)

5. **SEC-05 — `max_length` en schemas Pydantic de deals** (10 líneas).
6. **SEC-06 — Allowlist de dominios Amazon en `extract_asin_from_url`**
   + bloqueo de IPs privadas tras resolver DNS (~20 líneas) + 2 tests.
7. **SEC-09 — Quitar `email` de logger.debug en security.py** (1 línea).

### 🟢 Opcional / evolución futura (1 commit, sólo si hay tiempo)

8. **Job `security-audit` en CI** con `pip-audit` + `npm audit --omit=dev`
   + `gitleaks`. Falla si hay CVE high+ o secretos.
9. **Documento `docs/SECURITY.md`** (estilo SECURITY.md de GitHub)
   con:
   - Política de divulgación de vulnerabilidades.
   - Resumen de controles existentes (resumen del informe).
   - Deuda asumida (JWT en localStorage, MFA admin no implementado,
     etc.) con justificación.
   - Plan de respuesta a incidentes (§10).
   - Checklist pre-go-live al dominio definitivo (verificación NAS,
     HSTS, certificados Let's Encrypt).
   - Resumen para evaluación del proyecto (§14).
10. **`npm audit fix`** en `buenchollo-web` (corrige los 17 moderate
    de tooling).

### ⛔ No tocar

- Migrar a cookies HttpOnly (alto coste, no idiomático con Supabase JS SDK).
- 2FA TOTP para admins (decisión externa al código; recomendar a Pedro
  activarlo en Supabase Auth de su cuenta personal).
- DAST automatizado con OWASP ZAP (over-engineering para TFM).
- Generación SBOM (over-engineering).
- WAF / Cloudflare front (depende del dominio definitivo).

---

## 13. Checklist final para defensa del proyecto

Tras aplicar los puntos 1-7 del plan (imprescindible + recomendable):

- [x] Auth segura (Supabase + JWT validado server-side en cada call)
- [x] Permisos en servidor (47 ocurrencias `require_admin`/`get_current_user`)
- [x] No secretos en código (`.env*` no trackeados; verificado con grep)
- [x] Validación servidor (Pydantic + Zod, doble frontera ADR-005)
- [ ] CORS restringido (post SEC-02 + SEC-04)
- [ ] Headers de seguridad básicos (post SEC-03)
- [ ] Dependencias auditadas sin CVE high+ (post SEC-01 + SEC-07)
- [x] Logs sin datos sensibles (post SEC-09)
- [x] Errores genéricos al cliente
- [x] Pipeline con checks mínimos (Vitest + Playwright + pytest + Dependabot)
- [ ] Documentación de seguridad (post `SECURITY.md`)

---

## 14. Resumen para evaluación del proyecto (borrador)

> *Para incluir en la memoria una vez aplicado el plan.*

**Security by Design:**
La arquitectura limita la superficie de ataque desde el origen.
ADR-002 prohíbe llamadas directas del frontend a la BD: todo pasa por
la API Gateway FastAPI, donde se valida autenticación y autorización
en cada endpoint. La BD tiene RLS activado en sus 12 tablas (ADR-006);
el backend usa la `service_role` key, que bypassa RLS de forma
controlada y auditada. La separación de claves anon/service_role evita
exposición accidental.

**Security by Default:**
Los defaults son los seguros: rate limiting activado, audit log de
acciones admin, headers de seguridad globales (CSP, X-Frame-Options,
X-Content-Type-Options, Referrer-Policy, Permissions-Policy), CORS
restringido a la lista de orígenes configurada, errores genéricos al
cliente sin filtrar stack traces.

**OWASP Top 10 como marco:**
Se ha realizado una auditoría completa contra OWASP Top 10:2021. Los
hallazgos se documentan en `docs/reference/SECURITY_AUDIT.md` y se han resuelto
los 6 medios identificados. Quedan dos asunciones documentadas (JWT
en localStorage por requisito del Supabase JS SDK, MFA admin no
implementado por escala del proyecto).

**Amenazas consideradas (Threat Modeling §2):**
Actores: visitante anónimo, usuario registrado, admin, atacante
externo, bot/scraper. Activos: cuentas, ofertas, panel admin, tokens.
Para cada superficie de ataque (formularios, endpoints API, rutas
admin, login, integración con APIs externas, despliegue) se han
implementado controles documentados.

**Controles implementados:**
Auth JWT validado server-side, autorización por rol con consulta directa
a `user_roles` (no se confía en el cliente), rate limiting por IP, audit
log de acciones admin con `request_id` correlacionable a Sentry, CSP +
Security Headers, validación Pydantic en cada endpoint, validación Zod
en cliente, SQL parametrizado, secrets en `.env` no trackeados,
Dependabot semanal, CI con pytest + Vitest + Playwright + pip-audit +
npm audit + secret scanning.

**Mejoras futuras documentadas:**
- Migración JWT a cookies HttpOnly cuando el SDK de Supabase lo soporte
  idiomáticamente.
- 2FA TOTP para administradores.
- DAST automatizado con OWASP ZAP en CI.
- SBOM con CycloneDX.

**Decisiones razonables para TFM:**
El proyecto tiene un único administrador (el autor), opera sobre un
NAS doméstico con tráfico bajo, y maneja datos no críticos (ofertas
públicas, no datos financieros). El nivel de control aplicado es
proporcional al riesgo real y defendible al nivel "senior junior" /
"sysadmin con visión de seguridad", no se exige nivel CISO ni
auditoría externa.

---

*Documento generado tras auditoría manual del repositorio.*
*Próximo paso: aprobación de Pedro para implementar las fases 🔴 y 🟡.*
