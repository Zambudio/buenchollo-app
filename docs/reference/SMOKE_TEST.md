# Smoke Test — BuenCholloTech

Guion exhaustivo de pruebas manuales para validar un release.

**Cuándo ejecutarlo**: antes de cualquier tag `v*` y tras cambios en
rutas críticas (auth, deals, admin).

**Entorno**: producción NAS (`https://embyzambu.synology.me:8000`) o
local (`http://localhost:8000`).

Cada sección lleva el resultado esperado entre paréntesis. Marca con
✅ / ❌ según resultado.

---

## 0. Pre-flight (backend)

| # | Check | Esperado |
|---|---|---|
| 0.1 | `GET /health` | `200 {"status":"ok"}` |
| 0.2 | `GET /health/ready` | `200` con `db_latency_ms < 500` |
| 0.3 | `GET /v1/deals/latest` | `200` con array de deals |
| 0.4 | `GET /deals/latest` (sin `/v1`) | `404` |
| 0.5 | Headers `X-Request-ID` presente en respuesta | sí, UUID |
| 0.6 | Logs del backend muestran `request_id` en cada línea | sí, JSON estructurado |

---

## 1. Home pública (sin login)

- [ ] Carga `/` sin parpadeos. Hero + grid de últimos chollos.
- [ ] Las imágenes de los chollos cargan.
- [ ] Click en una card → navega a `/chollo/<slug>`.
- [ ] Header muestra `[ ACCEDER ]`, no avatar.
- [ ] Footer presente, enlaces funcionan.
- [ ] `/explorar`, `/categorias`, `/contacto` cargan sin error.
- [ ] Búsqueda desde el header con texto → redirige a `/explorar?q=...`.

## 2. Detalle de chollo

- [ ] Título, precio, descripción visibles.
- [ ] Botón ir a la tienda funciona (target=_blank, rel=noopener).
- [ ] Caja de compartir (ShareBox) muestra enlace y botones.
- [ ] Comentarios cargan. Sin login → "Inicia sesión para comentar".
- [ ] Botón de voto deshabilitado sin login (o redirige a login).
- [ ] Meta tags OG correctos (verifica con view-source).

## 3. Autenticación

- [ ] `/login` muestra botón de Google OAuth.
- [ ] Login con Google redirige a `/` con sesión activa.
- [ ] Header muestra avatar + dropdown.
- [ ] Badge de notificaciones aparece en el icono campana (si hay no leídas).
- [ ] Refrescar la página mantiene la sesión.
- [ ] Cerrar sesión vuelve a estado anónimo.

## 4. Funciones de usuario autenticado

- [ ] `/perfil` muestra datos del usuario.
- [ ] `/favoritos` lista vacía → mensaje claro.
- [ ] Marcar un chollo como favorito → aparece en `/favoritos`.
- [ ] Desmarcar funciona.
- [ ] Comentar en un chollo crea el comentario.
- [ ] Spam: 10 comentarios seguidos → rate limit kick-in (error 429).
- [ ] Votar (positivo/negativo) en un chollo actualiza el contador.

## 5. Alertas

- [ ] `/alertas` muestra alertas del usuario (o vacío).
- [ ] `/alertas/nueva` permite crear alerta con título, keywords, precio.
- [ ] Alerta creada aparece en `/alertas`.
- [ ] Eliminar alerta funciona.

## 6. Notificaciones

- [ ] `/notificaciones` carga (puede estar vacío).
- [ ] Al entrar en `/notificaciones`, el badge del Header baja a 0.
- [ ] Recargar página: badge sigue en 0 si no hay nuevas.
- [ ] Click en una notificación con `link_url` → navega al destino.

## 7. Panel admin (requiere rol admin)

- [ ] `/admin` muestra el dashboard con stats (6 KPIs).
- [ ] Stats reflejan números coherentes con la BD.
- [ ] `/admin/chollos` lista chollos con paginación.
- [ ] Crear chollo desde admin → aparece en home pública.
- [ ] Editar chollo → cambios visibles.
- [ ] Borrar chollo → desaparece.
- [ ] Promoción a Telegram desde panel funciona (TelegramPanel).
- [ ] `/admin/categorias`, `/admin/tiendas`, `/admin/usuarios` cargan.
- [ ] Usuario no admin que accede a `/admin` → redirigido o 403.
- [ ] Audit log: cada acción admin queda registrada con `user_id` y `request_id`
      (verificable vía SQL: `SELECT * FROM admin_audit_log ORDER BY created_at DESC LIMIT 10;`).

## 8. Seguridad

- [ ] Token caducado → frontend pide re-login.
- [ ] Endpoint `/v1/admin/*` sin Bearer → 401.
- [ ] Endpoint `/v1/admin/*` con Bearer de usuario normal → 403.
- [ ] Sentry recibe errores (forzar un error en cualquier endpoint y
      verificar en el dashboard Sentry).
- [ ] CORS: una request desde origen no permitido → bloqueada.

## 9. Robustez frontend

- [ ] `tsc --noEmit` 0 errores.
- [ ] `eslint .` 0 errores (warnings permitidos).
- [ ] Build de producción (`npm run build`) completa sin warnings críticos.
- [ ] Lighthouse en home: Performance > 80, A11y > 90.
- [ ] No errores en consola del navegador en navegación normal.

## 10. Robustez backend

- [ ] `pytest -q` todos verdes.
- [ ] Migraciones limpias: `alembic current` apunta a head.
- [ ] Reinicio del contenedor: `alembic upgrade head` no falla.
- [ ] Tras reiniciar, todas las features de la app siguen operativas.

---

## Resultado del run

| Fecha | Versión | Operador | Veredicto |
|---|---|---|---|
| _YYYY-MM-DD_ | _v1.0.0-tfm_ | _Pedro_ | _PASS / FAIL_ |
