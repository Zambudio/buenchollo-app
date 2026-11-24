# 📋 Architecture Decision Records (ADRs)

> **TL;DR** · Diecinueve decisiones arquitectónicas firmadas, datadas y
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
  <td>🔄 Superado parcialmente (por <a href="ADR-002-migracion-baas-a-api-gateway.md">002</a>, en la arquitectura de datos)</td>
  <td>2026-03</td>
</tr>
<tr>
  <td><a href="ADR-002-migracion-baas-a-api-gateway.md">002</a></td>
  <td>🚪 Migración de BaaS directo a API Gateway</td>
  <td>✅ Aceptado · 100% cumplido</td>
  <td>2026-05-19</td>
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
<tr>
  <td><a href="ADR-010-validacion-jwt-local.md">010</a></td>
  <td>🔑 Validación local de JWT con JWKS (sin round-trip a Supabase)</td>
  <td>✅ Aceptado</td>
  <td>2026-07-16</td>
</tr>
<tr>
  <td><a href="ADR-011-blog-tiptap-editor.md">011</a></td>
  <td>📝 Editor de blog con Tiptap y JSON como fuente de verdad</td>
  <td>✅ Aceptado</td>
  <td>2026-07-22</td>
</tr>
<tr>
  <td><a href="ADR-012-motor-tareas-programadas.md">012</a></td>
  <td>⏱️ Motor genérico de tareas programadas (handler registrable)</td>
  <td>✅ Aceptado</td>
  <td>2026-08-10</td>
</tr>
<tr>
  <td><a href="ADR-013-motor-ia-unificado-omniroute-modelos-gratuitos.md">013</a></td>
  <td>🤖 Motor de IA unificado con OmniRoute, fallback de modelos gratuitos y base para Chatbot</td>
  <td>✅ Aceptado</td>
  <td>2026-08-12</td>
</tr>
<tr>
  <td><a href="ADR-014-analitica-first-party-atribucion-sesiones.md">014</a></td>
  <td>📊 Analítica first-party con atribución por sesión y contador público del blog</td>
  <td>✅ Aceptado</td>
  <td>2026-09-26</td>
</tr>
<tr>
  <td><a href="ADR-015-ingesta-imagenes-backend.md">015</a></td>
  <td>🖼️ Ingesta de imágenes de usuarios por el backend (Pillow → WebP → Storage, fetcher anti-SSRF, límite de cuerpo)</td>
  <td>✅ Aceptado</td>
  <td>2026-11-04</td>
</tr>
<tr>
  <td><a href="ADR-016-propuestas-comunidad-y-afiliados.md">016</a></td>
  <td>🤝 Propuestas de comunidad en tabla separada, registro de reescritores de afiliado y bloqueo de acortadores</td>
  <td>✅ Aceptado</td>
  <td>2026-11-04</td>
</tr>
<tr>
  <td><a href="ADR-017-catalogo-permanente.md">017</a></td>
  <td>🗃️ Catálogo permanente: los chollos ya no se borran (productos, listings y ofertas)</td>
  <td>✅ Aceptado</td>
  <td>2026-11-06</td>
</tr>
<tr>
  <td><a href="ADR-018-tops-comunitarios-productos.md">018</a></td>
  <td>🏆 Tops comunitarios de productos permanentes con votos de usuarios</td>
  <td>✅ Aceptado</td>
  <td>2026-11-06</td>
</tr>
<tr>
  <td><a href="ADR-019-redes-afiliacion-awin-tradedoubler.md">019</a></td>
  <td>🔗 Redes de afiliación (Awin y Tradedoubler) en el editor de chollos</td>
  <td>✅ Aceptado · pendiente de validación en vivo</td>
  <td>2026-11-08</td>
</tr>
<tr>
  <td><a href="ADR-020-historico-de-precios.md">020</a></td>
  <td>📈 Histórico de precios propio para todas las tiendas</td>
  <td>✅ Aceptado</td>
  <td>2026-11-20</td>
</tr>
<tr>
  <td><a href="ADR-021-tarjeta-oferta-telegram.md">021</a></td>
  <td>🖼️ Tarjeta de oferta (Pillow) como imagen de cada chollo en Telegram</td>
  <td>✅ Aceptado</td>
  <td>2026-11-23</td>
</tr>
<tr>
  <td><a href="ADR-022-publicacion-instagram.md">022</a></td>
  <td>📸 Publicación automática de los chollos en el feed de Instagram</td>
  <td>✅ Aceptado</td>
  <td>2026-11-24</td>
</tr>
<tr>
  <td><a href="ADR-023-bus-de-eventos-entre-modulos.md">023</a></td>
  <td>🔀 Bus de eventos en proceso para desacoplar módulos</td>
  <td>✅ Aceptado</td>
  <td>2026-11-24</td>
</tr>
</tbody>
</table>

---

## 🧭 Mapa por área técnica

> Si te interesa un área técnica concreta, salta directamente a los ADRs
> relevantes:

| Bloque | ADRs |
|---|---|
| 📐 **Arquitectura de Software** | [001](ADR-001-monolito-modular-fastapi.md) · [002](ADR-002-migracion-baas-a-api-gateway.md) · [004](ADR-004-persistencia-sqlalchemy-pgbouncer.md) · [007](ADR-007-di-fastapi-depends.md) · [011](ADR-011-blog-tiptap-editor.md) · [012](ADR-012-motor-tareas-programadas.md) · [013](ADR-013-motor-ia-unificado-omniroute-modelos-gratuitos.md) · [014](ADR-014-analitica-first-party-atribucion-sesiones.md) · [016](ADR-016-propuestas-comunidad-y-afiliados.md) · [017](ADR-017-catalogo-permanente.md) · [018](ADR-018-tops-comunitarios-productos.md) · [019](ADR-019-redes-afiliacion-awin-tradedoubler.md) · [020](ADR-020-historico-de-precios.md) · [021](ADR-021-tarjeta-oferta-telegram.md) · [022](ADR-022-publicacion-instagram.md) · [023](ADR-023-bus-de-eventos-entre-modulos.md) |
| 🧪 **Calidad del Software** | [008](ADR-008-estrategia-calidad-testing.md) |
| 🛡️ **Seguridad** | [003](ADR-003-autenticacion-supabase-jwt.md) · [005](ADR-005-validacion-doble-frontera.md) · [006](ADR-006-rls-service-role.md) · [010](ADR-010-validacion-jwt-local.md) · [015](ADR-015-ingesta-imagenes-backend.md) · [016](ADR-016-propuestas-comunidad-y-afiliados.md) |
| 🤖 **Desarrollo con IA** | [009](ADR-009-uso-de-ia-en-desarrollo.md) · [013](ADR-013-motor-ia-unificado-omniroute-modelos-gratuitos.md) |

---

## 📝 Formato estándar de un ADR

Cada ADR sigue esta estructura:

```markdown
# ADR-XXX — Título de la decisión

## Estado
Aceptado | Propuesto | Superado parcialmente o Reemplazado por ADR-YYY

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
  <a href="../guides/README.md">🔐 Guías</a> ·
  <a href="../../PROJECT_STATUS.md">🗒️ Bitácora</a>
</p>
