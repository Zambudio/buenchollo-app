# ADR-003 — Autenticación con Supabase Auth y validación de JWT en el backend

| Campo        | Valor                                            |
|--------------|--------------------------------------------------|
| **Estado**   | Aceptado                                         |
| **Fecha**    | 2026-05-27                                       |
| **Autores**  | Pedro Zambudio                                   |
| **Relacionado** | [ADR-001](ADR-001-monolito-modular-fastapi.md), [ADR-002](ADR-002-migracion-baas-a-api-gateway.md), [ADR-006](ADR-006-rls-service-role.md) |

---

## Contexto

BuenCholloTech necesita autenticación con dos tipos de usuarios (usuario
normal y administrador), inicio de sesión vía email/password y vía Google
OAuth, gestión de sesión persistente entre cierres de navegador, recuperación
de contraseña y, a futuro, verificación de email y MFA.

Las opciones evaluadas fueron:

1. **Auth propio con FastAPI Users / FastAPI Login Manager** — control total
   pero hay que construir y mantener: hash de contraseñas, flujo OAuth, envío
   de correos, tokens de reseteo, MFA, rate limit anti-bruteforce, etc.
2. **Auth0 / Clerk** — IdP comercial, calidad alta, coste por MAU que se
   convierte en limitante si la app crece.
3. **Supabase Auth** — incluido en el plan free de Supabase, soporta OAuth
   social, email/password, magic links y MFA. JWTs estándar firmados por
   Supabase con claims en el formato esperado.
4. **Firebase Auth** — alternativa similar pero acoplaría el resto del stack
   (la BD ya está en Supabase).

---

## Decisión

**Supabase Auth en el cliente + validación de JWT en el backend con
`service_role key`**.

El flujo concreto:

```
1. Usuario inicia sesión en el frontend con Supabase JS SDK
   (email/password u OAuth Google).

2. Supabase devuelve un access_token (JWT firmado) y un refresh_token.
   El SDK los guarda en localStorage y los renueva automáticamente.

3. El frontend adjunta el access_token en cada petición a FastAPI:
       Authorization: Bearer <jwt>

4. FastAPI valida el JWT contra Supabase llamando a
   supabase.auth.get_user(token) con su service_role key.
   - Si es válido, get_current_user devuelve el User de Supabase.
   - Si falla, se devuelve 401 con mensaje genérico (ver ADR-006).

5. Para endpoints admin, require_admin consulta directamente la tabla
   public.user_roles con una query parametrizada y comprueba que el
   user_id tiene role='admin'.

6. Storage (subida de imágenes) usa el JWT del cliente directamente
   contra Supabase Storage. Es la única excepción al patrón API Gateway
   (ver ADR-002).
```

Implementación:

- **Frontend**: [`buenchollo-web/src/integrations/supabase/client.ts`](../../buenchollo-web/src/integrations/supabase/client.ts), [`buenchollo-web/src/hooks/useAuth.tsx`](../../buenchollo-web/src/hooks/useAuth.tsx), [`buenchollo-web/src/services/api/client.ts`](../../buenchollo-web/src/services/api/client.ts) (adjunta el Bearer automáticamente).
- **Backend**: [`buenchollo-api/app/core/security.py`](../../buenchollo-api/app/core/security.py) con `get_current_user` y `require_admin`. Endpoint `GET /auth/me` en `users/api/router.py` resuelve el rol en una sola llamada y se cachea en el frontend vía `authApi.me()`.

---

## Consecuencias

### Positivas

- **Cero código propio de gestión de identidades**: hash, OAuth, magic links,
  recuperación de contraseña y futuro MFA vienen de fábrica.
- **JWT estándar**: si mañana se migra el IdP, sigue siendo un Bearer token.
  Sólo cambia el verifier del backend.
- **`service_role key` sólo en el servidor**: el cliente nunca toca esa key.
  Esto, combinado con RLS activado (ADR-006), blinda el acceso al `anon key`.
- **JWTs cortos + refresh tokens**: Supabase rota el access_token cada hora.
  No mantenemos sesiones server-side; el sistema es naturalmente stateless.
- **Plan gratuito generoso** (50.000 MAU en Supabase free tier al cierre de
  2026): no es coste hasta crecer mucho.

### Negativas

- **Dependencia operativa de Supabase**: caída de Supabase Auth = no login.
  Mitigación: el JWT ya emitido sigue siendo válido hasta su expiración
  (1 hora); el backend lo valida sin red durante ese rango (el SDK de Supabase
  hace verificación local de firma).
- **Acoplamiento del frontend al SDK de Supabase para Auth/Storage**:
  excepciones aprobadas a ADR-002 documentadas explícitamente.
- **Migración futura a otro IdP requeriría tres cambios coordinados**:
  1. Reescribir `useAuth.tsx` y los flujos de `login.tsx`/`registro.tsx`.
  2. Cambiar el verifier en `get_current_user` (10 líneas).
  3. Migrar la base de usuarios (Supabase exporta JSON estándar).

---

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Auth propio | Demasiado código de seguridad sensible para un proyecto solo. Riesgo de bugs en zonas críticas (hash, rate-limit anti-bruteforce, recuperación de contraseña). |
| Auth0 / Clerk | Mejores que Supabase Auth en ergonomía pero coste por MAU. Si BuenChollo crece a 10k usuarios, son ~50 €/mes que se ahorran con Supabase. |
| Firebase Auth | Significaría tener la BD en Postgres (Supabase) y el IdP en Google. Doble proveedor, doble panel, doble facturación, complejidad CORS añadida. |
| Session cookies server-side | Requeriría un store de sesiones (Redis o similar). Para un monolito que ya es naturalmente stateless con JWT, es complejidad sin valor. |

---

## Notas de seguridad relacionadas

- Los errores de validación de JWT devuelven mensaje **genérico** al cliente
  (`"Credenciales inválidas"`) y log detallado en servidor (ADR-006 / fix
  2026-05-26).
- El `anon key` viaja en el bundle del frontend y es público por diseño;
  toda tabla está protegida por RLS (ADR-006).
- El `service_role key` vive sólo en `.env` del backend (NAS) y bypassa RLS.
  Nunca se expone al cliente.

---

## Evolución prevista

- **Corto plazo**: añadir verificación de email obligatoria antes de comentar
  o votar (configurable en el panel de Supabase Auth, sin cambios de código).
- **Medio plazo**: MFA opcional para cuentas admin.
- **Largo plazo**: si crece a escala que justifique IdP dedicado, migrar a
  Auth0/Clerk con el plan documentado arriba.
