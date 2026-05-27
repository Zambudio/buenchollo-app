# ADR-005 — Validación en doble frontera con Zod y Pydantic

| Campo        | Valor                                            |
|--------------|--------------------------------------------------|
| **Estado**   | Aceptado                                         |
| **Fecha**    | 2026-05-27                                       |
| **Autores**  | Pedro Zambudio                                   |
| **Relacionado** | [ADR-002](ADR-002-migracion-baas-a-api-gateway.md), [ADR-003](ADR-003-autenticacion-supabase-jwt.md) |

---

## Contexto

Tras el cumplimiento del ADR-002 (API Gateway), cualquier dato que entra al
sistema cruza dos fronteras explícitas:

1. **Frontera de UX** (cliente → servicio frontend): formulario en el
   navegador. El usuario espera feedback inmediato sin esperar al servidor.
2. **Frontera de contrato** (servicio frontend → API FastAPI): es la única
   que importa para la integridad del dato. El servidor no puede confiar en
   el cliente.

Opciones:

- **Validar sólo en cliente** — UX rápida pero el servidor queda expuesto.
  Cualquiera que use `curl` o el navegador con el JS desactivado puede
  enviar basura. Inaceptable.
- **Validar sólo en servidor** — robusto pero los errores cuestan un
  round-trip y mensajes a veces poco amigables al usuario.
- **Validar en ambas fronteras con esquemas separados** — duplicación de
  código y riesgo de divergencia.
- **Validar en ambas fronteras con un único esquema compartido**
  (`zod ↔ openapi-typescript`, `tRPC`, generadores) — elegante pero acopla
  el frontend a la generación o requiere un build step que actualice los
  tipos cada vez que cambia el backend.

---

## Decisión

**Validar en ambas fronteras manteniendo esquemas separados pero análogos**,
declarando explícitamente que **el backend es la fuente de verdad** y que la
duplicación es un coste aceptado para evitar acoplamientos prematuros.

| Capa | Tecnología | Rol |
|---|---|---|
| Cliente (React) | **Zod** | Validación inmediata de formularios. Feedback al usuario antes de tocar la red. Mensajes en español. |
| Servicio HTTP (FastAPI) | **Pydantic v2** | Contrato de la API. Garantiza tipos, rangos y formato. Si Zod falla, Pydantic también debe fallar; si Zod pasa, Pydantic puede aún rechazar y el frontend mostrará el `errorMessage()` correspondiente. |

Implementación actual:

- **Frontend**:
  [`lib/validation/deals.ts`](../../buenchollo-web/src/lib/validation/deals.ts) —
  `dealFormSchema` (título 3-200, URL afiliada válida, current_price > 0,
  previous_price > current_price).
  [`lib/validation/alerts.ts`](../../buenchollo-web/src/lib/validation/alerts.ts) —
  `alertFormSchema` (al menos un criterio, max_price > 0, min_discount 1-100).
- **Backend**:
  [`deals/api/schemas.py`](../../buenchollo-api/app/modules/deals/api/schemas.py) —
  `DealCreate`, `DealUpdate`, `VoteRequest`, etc.
  [`alerts/api/schemas.py`](../../buenchollo-api/app/modules/alerts/api/schemas.py)
  define `AlertCreate`/`AlertUpdate` con `Field(..., ge=0)`, `min_length`, etc.
  Pydantic devuelve 422 con detalle estructurado que `apiClient.ts` formatea
  como string legible.

Convención de mensajes:

- Zod usa textos en español por validación; el primer issue del array es
  el que se muestra como toast (`toast.error(parsed.error.issues[0].message)`).
- Pydantic devuelve los detalles en su formato `[{loc, msg, type}, ...]`;
  el `extractErrorMessage()` del `apiClient` concatena `loc.join(".") + ": " + msg`.

---

## Consecuencias

### Positivas

- **Defensa en profundidad**: si un usuario manipula el JS para saltarse Zod,
  el backend lo detiene. Si añadimos un cliente nuevo (CLI, móvil) sin Zod,
  el backend sigue protegiendo el dato.
- **Feedback inmediato**: el usuario ve "El precio anterior debe ser mayor
  que el actual" en cuanto teclea, sin esperar 200 ms al servidor.
- **Mensajes amigables en cliente, mensajes técnicos en logs**: el frontend
  no expone errores de servidor crudos (ADR-006 limpió los `str(exc)`).
- **OpenAPI gratis del lado del backend**: Pydantic genera `/docs` con los
  schemas. Útil para defender contratos en la memoria del TFM.
- **Cada lado evoluciona a su ritmo**: si añadimos un campo opcional al
  backend, no rompemos el frontend hasta que decidamos usarlo.

### Negativas

- **Duplicación controlada**: cuando cambia una regla (ej. "el título ahora
  permite 250 caracteres en vez de 200"), hay que tocar dos sitios: el
  schema Zod y el schema Pydantic.
- **Riesgo de divergencia**: si el backend acepta `previous_price <= current_price`
  pero el frontend lo rechaza, el usuario no lo verá hasta que use otro
  cliente. Mitigación: revisar el contrato como parte del PR (lista en
  el plan de hardening F7.1) y, a futuro, evaluar tests de contrato.

---

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Validar sólo en cliente | Insegura por definición. Rompe el principio "el servidor no confía en el cliente". |
| Validar sólo en servidor | UX pobre; cada error cuesta un round-trip; algunos errores son del cliente puro (típico "campos vacíos") y no merecen golpear la API. |
| tRPC / esquema único compartido | Acoplaría frontend y backend en el mismo lenguaje (Node + tRPC, no compatible con FastAPI). Cambiar a tRPC implicaría reescribir el backend en Node. |
| Generadores OpenAPI → TS | Es válido y se podría incorporar en el futuro como derivación del schema Pydantic (vía `openapi-typescript`). Por ahora la duplicación es manejable (6 schemas relevantes). |
| Pydantic en el cliente | Pydantic no corre en navegador. |
| AJV/JSON Schema en el cliente | Sintaxis verbose, peor DX que Zod. Sin ventaja real. |

---

## Notas de implementación

- **Helper de errores del cliente**: [`lib/errors.ts`](../../buenchollo-web/src/lib/errors.ts)
  con `errorMessage(e, fallback)` extrae el mensaje de cualquier valor capturado
  (Error, string, unknown). Centraliza el patrón en todos los catch del
  frontend tras el refactor 2026-05-26.
- **Transformación de strings de inputs a number**: Zod hace `.transform()`
  para convertir el `string` de un `<input type="number">` a `number | null`.
  El resultado de `safeParse(...)` ya es el payload listo para enviar.
- **`refine()` para reglas cross-field**: ejemplo
  `previous_price > current_price` en `dealFormSchema`. Pydantic en el
  backend hace la misma comprobación con un `@field_validator` o
  `@model_validator`.

---

## Evolución prevista

- **Corto plazo**: cuando se añadan formularios nuevos (categorías, tiendas
  desde admin si se quita el shadcn-only actual), aplicar el mismo patrón:
  un schema Zod en `lib/validation/<dominio>.ts` + Pydantic en
  `<modulo>/api/schemas.py`.
- **Medio plazo**: evaluar generador `openapi-typescript` para derivar
  tipos del backend automáticamente, sin perder Zod (Zod sigue siendo el
  validador con mensajes; los tipos generados serían sólo para la capa
  `services/api/`).
- **Largo plazo**: si se añade un endpoint público de terceros (API key),
  documentar los schemas en `/docs` con ejemplos y rate limits, y considerar
  versionado de schema independiente del versionado de URL (`v1` actual).
