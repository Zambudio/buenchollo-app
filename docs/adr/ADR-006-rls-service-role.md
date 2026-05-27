# ADR-006 — Hardening de seguridad: RLS y separación `anon` / `service_role`

| Campo        | Valor                                            |
|--------------|--------------------------------------------------|
| **Estado**   | Aceptado                                         |
| **Fecha**    | 2026-05-27                                       |
| **Autores**  | Pedro Zambudio                                   |
| **Relacionado** | [ADR-002](ADR-002-migracion-baas-a-api-gateway.md), [ADR-003](ADR-003-autenticacion-supabase-jwt.md), [ADR-004](ADR-004-persistencia-sqlalchemy-pgbouncer.md) |

---

## Contexto

Supabase emite **dos claves** por proyecto:

- **`anon key`** — pública, viaja en el bundle del frontend. Permite operar
  contra Supabase Auth, Storage y BD respetando RLS.
- **`service_role key`** — privada, vive **sólo en el servidor**. Bypassa
  RLS por diseño. Si se filtra, equivale a comprometer toda la BD.

El 2026-05-27 el dashboard de Supabase reportó la vulnerabilidad
`rls_disabled_in_public` como **crítica**. La consulta diagnóstica reveló
que **las 12 tablas de `public` tenían RLS desactivado**. Como el `anon key`
es público, **cualquiera podía leer/borrar/modificar todas las tablas** sin
autenticación: bastaba con instalar el SDK de Supabase y usar la key del
bundle.

Esto sucedió a pesar de que:
- Las migraciones SQL **sí** declaran `ENABLE ROW LEVEL SECURITY` en cada
  tabla. Por algún motivo (probablemente RLS deshabilitada manualmente
  durante alguna depuración), el estado de producción había divergido del
  declarado en migraciones.
- El cumplimiento del ADR-002 al 100% (no hay `supabase.from()` desde el
  frontend) garantizaba que **ningún flujo legítimo de la app** dependía
  del acceso directo. Pero un atacante con `anon key` sí podía hacerlo.

---

## Decisión

**Hardening de seguridad por capas, en dos planos:**

### Plano 1 — Activar RLS en todas las tablas de `public`

Migración versionada
[`20260527090000_enable_rls_all_tables.sql`](../../buenchollo-web/supabase/migrations/20260527090000_enable_rls_all_tables.sql)
(pendiente de mover al backend en F2.1) que ejecuta
`ALTER TABLE public.X ENABLE ROW LEVEL SECURITY` en las 12 tablas:
`alerts, categories, comment_votes, deal_comments, deal_votes, deals,
favorites, import_logs, notifications, profiles, stores, user_roles`.

Las **políticas RLS** existentes definidas en migraciones anteriores
(`"Comments public read"`, `"Stores public read"`, `"Users manage own ..."`,
etc.) **siguen vigentes** y se aplican automáticamente al activar RLS.

### Plano 2 — Separación estricta `anon` / `service_role`

| Capa | Key usada | Bypass RLS |
|---|---|:---:|
| Frontend (browser) | `anon key` (público, en bundle) | ❌ |
| Backend FastAPI (NAS) | `service_role key` (`.env`) | ✅ |
| Triggers y funciones SQL (handle_new_user, recalc_comment_votes) | `SECURITY DEFINER` (postgres) | ✅ |

Implicaciones:

- El backend opera con `service_role` y por tanto **ignora RLS**. Toda la
  lógica de autorización vive en el código del backend (`require_admin`,
  ownership checks en repos). RLS es la **defensa de último recurso** si
  el backend cae o se filtra el `anon key`.
- El `anon key` sólo permite ahora: Supabase Auth (login, refresh) y las
  policies `public read` sobre `comments`, `comment_votes`, `stores`,
  `categories`. Cualquier otra operación devuelve `permission denied`.
- Storage tiene su propio sistema de policies (no usa RLS de tablas). Las
  bucket policies de `deal-images` permiten upload sólo a usuarios
  autenticados y read público. Sin cambios.

---

## Consecuencias

### Positivas

- **El `anon key` ya no es una llave universal**: aunque alguien lo extraiga
  del bundle (cosa trivial), no puede tocar datos sensibles.
- **Defensa en profundidad real**: RLS + backend con `service_role` + auth
  por JWT (ADR-003) + validación en doble frontera (ADR-005) + errores
  sanitizados. Cuatro capas que un atacante tiene que atravesar.
- **Cumplimos los avisos de Supabase**: el `rls_disabled_in_public` queda
  resuelto y el dashboard ya no marca alertas críticas.
- **Coherencia entre migraciones y producción**: la migración explícita
  versiona el estado. Si en el futuro alguien desactiva RLS manualmente
  para debuggear, basta con `git pull` + replay para restaurarlo.

### Negativas

- **El equipo de backend queda **único responsable de autorización**: si
  hay un bug en `require_admin` o en un ownership check, RLS no salva a
  los datos (porque el backend usa `service_role`). Mitigación: tests
  unitarios y de integración de los flujos críticos; revisar las
  consultas SQL parametrizadas de `users/api/router.py`.
- **No podemos usar el SDK de Supabase desde el frontend** para
  operaciones de datos (cosa que ya no hacemos por ADR-002, así que no
  cambia nada en la práctica).
- **Si alguien revierte RLS manualmente** desde el dashboard de Supabase,
  el aviso volverá a saltar y los datos se exponen. Mitigación: la
  migración del 2026-05-27 queda como recordatorio; añadir checklist en
  `LAUNCH_CHECKLIST.md` (F3 incluye revisar policies antes del go-live).

---

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Confiar sólo en ADR-002 (el frontend ya no llama) | No protege contra atacantes con el `anon key`. ADR-002 es un patrón arquitectónico, no un control de acceso. |
| Definir policies muy restrictivas en cada tabla en vez de "sólo activar RLS" | Doble fuente de verdad (lógica en código del backend + lógica en SQL). Las policies actuales (lectura pública de comments/stores/categories) son las únicas que aportan valor; el resto se cierra con RLS sin policies adicionales. |
| Cambiar el `anon key` por uno custom firmado | Supabase no lo soporta. El `anon key` es estructural en su modelo. |
| Servir el frontend con un proxy que reemplace el `anon key` por uno corto | Sobreingeniería. No aporta seguridad real porque el reemplazo sigue siendo público. |

---

## Notas operativas

### Cómo verificar el estado en cualquier momento

```sql
-- Lanzar en Supabase SQL Editor
SELECT schemaname, tablename, rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY rowsecurity, tablename;
```

Todas las filas deben mostrar `rls_enabled = true`.

### Cómo reaplicar si vuelve a desactivarse

Ejecutar la migración `20260527090000_enable_rls_all_tables.sql` (idempotente).

### Cómo añadir una tabla nueva sin volver a caer

Cualquier `CREATE TABLE public.X` debe ir acompañado de
`ALTER TABLE public.X ENABLE ROW LEVEL SECURITY;` en la misma migración.
Documentar en `CLAUDE.md` como regla obligatoria — pendiente de cerrarse
con la check de F7.1 (smoke test).

### Auditoría del `anon key`

El `anon key` puede regenerarse desde el dashboard de Supabase si se
sospecha de uso indebido. Tras regenerarlo:

1. Sustituir `VITE_SUPABASE_PUBLISHABLE_KEY` en el `.env` del frontend.
2. Re-desplegar.
3. Los usuarios con sesión activa **no necesitan re-loguear** (el JWT es
   independiente del anon key).

### Auditoría del `service_role key`

Si se sospecha que el `service_role key` se ha filtrado:

1. Regenerar desde el dashboard de Supabase.
2. Actualizar `SUPABASE_KEY` en el `.env` del backend en el NAS.
3. Reiniciar el contenedor.
4. **No** queda ninguna instancia legítima de ese key fuera del backend.

---

## Evolución prevista

- **Corto plazo** (parte de F3): añadir un **audit log** para acciones
  admin críticas (crear/borrar deal, cambiar rol). Junto con la
  observabilidad básica (request_id) permite reconstruir qué pasó si algo
  sale mal.
- **Medio plazo**: revisar las policies `public read` sobre `comments`
  cuando se añada moderación. Posiblemente cambiar a "lectura pública de
  comentarios aprobados" con un campo `is_published`.
- **Largo plazo**: si BuenChollo se escala a múltiples administradores con
  permisos granulares (editor, moderator, admin), considerar mover parte
  de la lógica de autorización a RLS con `auth.uid()` y custom claims en
  el JWT. Coste: complejidad creciente. Beneficio: doble red de seguridad
  si el backend tiene bug.
