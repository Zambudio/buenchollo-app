# 📋 Architecture Decision Records (ADRs)

> **TL;DR** · Nueve decisiones arquitectónicas firmadas, datadas y
> justificadas con contexto + alternativas evaluadas + consecuencias.
> Si quieres entender **por qué** se tomó una decisión técnica del
> proyecto, está aquí.

---

## 📚 Índice de ADRs

<table>
<thead>
<tr><th>#</th><th>Decisión</th><th>Estado</th><th>Fecha</th></tr>
</thead>
<tbody>
<tr>
  <td><a href="ADR-001-monolito-modular-fastapi.md">001</a></td>
  <td>📐 Monolito Modular con FastAPI y Clean Architecture pragmática</td>
  <td>✅ Aceptado</td>
  <td>2026-05-13</td>
</tr>
<tr>
  <td><a href="ADR-002-migracion-baas-a-api-gateway.md">002</a></td>
  <td>🚪 Migración de BaaS directo a API Gateway</td>
  <td>✅ Aceptado · 100% cumplido</td>
  <td>2026-05-21</td>
</tr>
<tr>
  <td><a href="ADR-003-autenticacion-supabase-jwt.md">003</a></td>
  <td>🔐 Autenticación con Supabase Auth + validación JWT en backend</td>
  <td>✅ Aceptado</td>
  <td>2026-05-27</td>
</tr>
<tr>
  <td><a href="ADR-004-persistencia-sqlalchemy-pgbouncer.md">004</a></td>
  <td>💾 Persistencia con SQLAlchemy async + asyncpg + PgBouncer</td>
  <td>✅ Aceptado</td>
  <td>2026-05-27</td>
</tr>
<tr>
  <td><a href="ADR-005-validacion-doble-frontera.md">005</a></td>
  <td>🛡️ Validación en doble frontera (Zod + Pydantic)</td>
  <td>✅ Aceptado</td>
  <td>2026-05-27</td>
</tr>
<tr>
  <td><a href="ADR-006-rls-service-role.md">006</a></td>
  <td>🔒 Hardening de RLS y separación <code>anon</code> / <code>service_role</code></td>
  <td>✅ Aceptado</td>
  <td>2026-05-27</td>
</tr>
<tr>
  <td><a href="ADR-007-di-fastapi-depends.md">007</a></td>
  <td>🧬 Inyección de dependencias con <code>Depends</code> de FastAPI</td>
  <td>✅ Aceptado</td>
  <td>2026-05-27</td>
</tr>
<tr>
  <td><a href="ADR-008-estrategia-calidad-testing.md">008</a></td>
  <td>🧪 Estrategia de calidad y testing 100/80/0</td>
  <td>✅ Aceptado</td>
  <td>2026-06-02</td>
</tr>
<tr>
  <td><a href="ADR-009-uso-de-ia-en-desarrollo.md">009</a></td>
  <td>🤖 Uso de IA como apoyo supervisado al desarrollo</td>
  <td>✅ Aceptado</td>
  <td>2026-06-02</td>
</tr>
</tbody>
</table>

---

## 🧭 Mapa por bloque del máster

> Si te interesa un bloque concreto, salta directamente a los ADRs
> relevantes:

| Bloque | ADRs |
|---|---|
| 📐 **Arquitectura de Software** | [001](ADR-001-monolito-modular-fastapi.md) · [002](ADR-002-migracion-baas-a-api-gateway.md) · [004](ADR-004-persistencia-sqlalchemy-pgbouncer.md) · [007](ADR-007-di-fastapi-depends.md) |
| 🧪 **Calidad del Software** | [008](ADR-008-estrategia-calidad-testing.md) |
| 🛡️ **Seguridad** | [003](ADR-003-autenticacion-supabase-jwt.md) · [005](ADR-005-validacion-doble-frontera.md) · [006](ADR-006-rls-service-role.md) |
| 🤖 **Desarrollo con IA** | [009](ADR-009-uso-de-ia-en-desarrollo.md) |

---

## 📝 Formato estándar de un ADR

Cada ADR sigue esta estructura:

```markdown
# ADR-XXX — Título de la decisión

## Estado
Aceptado | Propuesto | Reemplazado por ADR-YYY

## Contexto
Qué problema o decisión había que resolver.

## Decisión
Qué se decidió.

## Motivo
Por qué se eligió esa opción.

## Alternativas consideradas
Qué otras opciones se valoraron y por qué se descartaron.

## Consecuencias
Ventajas, inconvenientes y efectos futuros.
```

---

## 🛠️ Cómo usar este directorio

| Necesito... | Hacer... |
|---|---|
| 💡 Entender **por qué** algo se hizo así | Leer el ADR correspondiente |
| 🆕 Tomar una **nueva decisión** importante | Crear `ADR-XXX-slug.md` siguiendo el formato |
| 🔄 **Reemplazar** una decisión anterior | Marcar el ADR antiguo como `Reemplazado por ADR-XXX` y crear el nuevo con el contexto del cambio |

---

<p align="center">
  <a href="../project/00-index.md">📘 Operativa</a> ·
  <a href="../master/00-index.md">🎓 Bloque académico</a> ·
  <a href="../reference/">📚 Referencias</a> ·
  <a href="../archive/">🗄️ Histórico</a>
</p>
