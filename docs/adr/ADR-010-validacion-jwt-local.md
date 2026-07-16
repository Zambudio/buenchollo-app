# ADR-010 — Validación local de JWT con JWKS (sin round-trip a Supabase)

## Estado

**Aceptado** · 2026-07-16 · resuelve el hallazgo H-02 / TD-12 de la
auditoría técnica (`AUDIT_REPORT.md`).

## Contexto

Hasta este cambio, `get_current_user` (core/security.py) validaba el token
de cada request autenticada llamando a `supabase.auth.get_user(token)`:
**un round-trip HTTP a Supabase por request**, encima del salto
NAS↔Cloudflare Tunnel↔cliente. Consecuencias:

1. **Latencia**: contribuía a la lentitud general medida en producción
   (TD-11) — cada endpoint autenticado pagaba ~100-300 ms extra.
2. **Punto único de fallo**: si Supabase Auth no responde, TODA la API
   autenticada cae, aunque la BD esté sana.
3. **Cuota**: consumo innecesario del plan de Supabase.

Un JWT está diseñado precisamente para validarse sin preguntar al emisor:
firma criptográfica + expiración + audiencia. El proyecto Supabase firma
los access tokens con **ES256** y publica la clave pública en su JWKS
(`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`), verificado el 2026-07-16.

## Decisión

Verificar los JWT **en local** en `get_current_user`:

1. **ES256/RS256** (caso actual): firma verificada contra el JWKS público de
   Supabase vía `PyJWT[crypto]` + `PyJWKClient` con caché de claves de 1 h —
   red hacia Supabase solo en el primer request y al expirar la caché.
2. **HS256** (legacy): si el proyecto rotara a secreto simétrico, se valida
   con `SUPABASE_JWT_SECRET` (nueva variable opcional de entorno).
3. **Fallback remoto**: si no hay material de firma local (HS256 sin secreto,
   JWKS inaccesible, algoritmo desconocido), se degrada al
   `supabase.auth.get_user()` de siempre en vez de tumbar la API.

Se valida siempre: firma, `exp` y `aud == "authenticated"`. Los routers
reciben un `AuthenticatedUser(id, email)` — la misma superficie (`.id`,
`.email`) que ya consumían del objeto de gotrue, así que ningún endpoint
cambia.

## Consecuencias

**Positivas**
- Cero llamadas a Supabase en el camino caliente de cada request.
- Supabase Auth deja de ser punto único de fallo para tokens ya emitidos.
- 9 tests nuevos cubren firma inválida, expiración, audiencia, token sin
  `sub`, token malformado, HS256 con/sin secreto y JWKS caído.

**Negativas / trade-offs asumidos**
- **Revocación no inmediata**: un token sigue siendo válido hasta su `exp`
  (1 h por defecto en Supabase) aunque el usuario cierre sesión o sea
  baneado. Con `get_user` remoto la revocación era inmediata. Se asume:
  la ventana es corta y las operaciones admin siguen re-verificando el rol
  contra la BD en cada request (`require_admin`).
- La primera petición tras el arranque (o tras 1 h) paga la descarga del
  JWKS (bloqueante, ~1 vez/hora — irrelevante).
- Si Supabase **rota** las claves de firma, la caché del JWKS se refresca
  sola en ≤1 h; ante un `kid` desconocido se hace fallback remoto, así que
  no hay ventana de corte.

## Alternativas consideradas

- **Seguir con `get_user` remoto**: simple y con revocación inmediata, pero
  es el problema que se quiere resolver (latencia + SPOF).
- **HS256 con `SUPABASE_JWT_SECRET` como vía principal**: requiere gestionar
  un secreto más en local y NAS; el proyecto ya firma con ES256, así que la
  clave pública es suficiente y no hay secreto que custodiar.
- **Cachear respuestas de `get_user`** (TTL corto): mantiene la dependencia
  de red y añade complejidad de invalidación; descartada.
