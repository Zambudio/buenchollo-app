# Diseño: Tareas programadas — Revisión de precios de chollos publicados

**Fecha**: 2026-08-09
**Estado**: Aprobado (pendiente de plan de implementación)

## 1. Problema

Los chollos publicados **con** `expires_at` se limpian solos (`DealCleanerService`, borrado a los 2 días de caducar — ver nota en §7). Pero los chollos **sin** fecha de expiración se quedan publicados indefinidamente, y muchos acaban con precio desactualizado o dejan de estar en oferta en Amazon sin que nadie lo detecte.

Se necesita una tarea programada que revise semanalmente (frecuencia configurable) esos chollos contra la API de Amazon y borre los que ya no cumplen el criterio de "oferta vigente al precio publicado", dejando siempre un registro auditable y recuperable.

## 2. Alcance

- Aplica solo a chollos con `status='active' AND expires_at IS NULL AND external_id IS NOT NULL` (external_id = ASIN; sin ASIN no se puede consultar Amazon, así que quedan fuera del alcance de esta tarea).
- Motor **genérico** de tareas programadas (tabla de configuración + tabla de registros con `task_type` discriminador), para poder añadir otras tareas en el futuro sin rediseñar el esquema. Los jobs automáticos ya existentes (marcar/borrar caducados, publicar programados, publicar posts de blog) **no** se migran a este motor — siguen tal cual están hoy.
- Fuera de alcance: notificaciones (email/Telegram) al ejecutarse la tarea; selector de día de la semana/mes fijo (la frecuencia es "cada N días desde la última ejecución", no un día de calendario concreto); selección múltiple/borrado en bloque de *items* dentro de un registro (solo se seleccionan y borran *registros* completos, no items sueltos).

## 3. Arquitectura

Nuevo módulo `app/modules/scheduled_tasks/`, independiente de `deals/`, siguiendo el mismo patrón de capas del resto del proyecto (`api → application → domain ← infrastructure`).

**Patrón "handler registrable"**: cada tipo de tarea implementa un `TaskHandler` (Protocol):

```python
class TaskHandler(Protocol):
    def preview(self, config: dict) -> list[Candidate]: ...
    def execute(self, candidates: list[Candidate]) -> RunResult: ...
```

Un registro `TASK_HANDLERS: dict[str, TaskHandler]` mapea `task_type → handler`. El scheduler y los endpoints del panel son genéricos: no conocen la lógica de "precio de Amazon", solo invocan el handler que corresponda a `task_type`.

`PriceCheckHandler` (primer y único handler implementado) reutiliza el mismo patrón ya usado en `ScheduledPublicationWorker._process_one` (`app/modules/scheduled_deals/application/publication_worker.py:68-94`): `Protocol ProductVerifier` inyectado con `AmazonProductClient.get_product_preview(external_id)`.

**Scheduler**: un único job nuevo en `build_deals_scheduler()` (`app/modules/deals/application/scheduler.py`), tipo `interval`, cada 1 hora. En cada disparo:
1. Lee filas de `scheduled_tasks` con `enabled=true`.
2. Para cada una, calcula si toca ejecutar: `last_run_at IS NULL OR now >= last_run_at + frequency_interval(frequency_preset)` y `now.hour >= run_hour` (para no disparar antes de la hora configurada el día que toca). Mapeo de `frequency_preset` a días: `daily=1, weekly=7, biweekly=14, monthly=30`.
3. Si toca, ejecuta el handler correspondiente en modo automático (ver §5) y actualiza `last_run_at = now`.

`run_hour` se interpreta en la misma zona horaria del servidor que usan ya los demás jobs cron del scheduler (ej. limpieza diaria a las 3:00) — sin conversión adicional.

Este enfoque de "auto-chequeo horario" evita tener que reprogramar dinámicamente un job de APScheduler cada vez que el usuario cambia la frecuencia desde el panel (que exigiría lógica de `reschedule_job` y persistencia adicional); en su lugar, cambiar la config en la tabla `scheduled_tasks` se refleja solo en el siguiente chequeo horario, sin reiniciar nada.

## 4. Modelo de datos (Alembic)

### `scheduled_tasks`
Configuración de cada tarea (hoy solo existirá una fila, `task_type='price_check'`, creada por la migración con `enabled=false` por defecto).

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID (`as_uuid=False`) | PK |
| task_type | str, unique | `"price_check"` |
| enabled | bool, default `false` | |
| frequency_preset | str | `"daily"` \| `"weekly"` \| `"biweekly"` \| `"monthly"` |
| run_hour | int | 0–23 |
| config | JSONB | parámetros específicos del tipo de tarea, ej. `{"price_tolerance_percent": 10}` |
| last_run_at | datetime, nullable | |
| created_at, updated_at | datetime | |

### `scheduled_task_runs`
Un registro por ejecución (manual o automática).

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| task_id | UUID, FK → scheduled_tasks | |
| trigger_type | str | `"manual"` \| `"automatic"` |
| status | str | `"completed"` \| `"failed"` |
| started_at, finished_at | datetime | |
| total_checked | int | candidatos evaluados |
| total_affected | int | candidatos que cumplían el criterio de borrado (= borrados, ya que en confirm no hay descarte adicional) |
| triggered_by | UUID, FK → users, nullable | admin que ejecutó manualmente; `null` en automáticas |
| error_message | text, nullable | solo relevante si `status="failed"` |

`status="failed"` se da únicamente en la ejecución **automática**, si ocurre un error no controlado a mitad de la evaluación (ej. la API de Amazon deja de responder por completo). En ese caso se guarda el run con los contadores parciales alcanzados hasta el fallo y `error_message` con el detalle; no se reintenta hasta el siguiente disparo del job horario. En el flujo **manual**, un fallo en `preview` no crea ningún run (se muestra el error directamente en el panel); un fallo en `confirm` es un caso no esperado (los datos ya fueron validados en el preview) y se trata como error 500 estándar de la API, sin crear run parcial.

### `scheduled_task_run_items`
Una fila por chollo borrado en esa ejecución. `ON DELETE CASCADE` respecto a `scheduled_task_runs`.

| Columna | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| run_id | UUID, FK → scheduled_task_runs (cascade) | |
| deal_id_snapshot | str | id que tenía el `Deal` original (no FK — el deal ya no existe) |
| title, slug, image_url, description | str | snapshot |
| store_id, category_id, subcategory_id | UUID, nullable | para poder recrear el deal en la misma tienda/categoría |
| external_id (ASIN), affiliate_url, source_url | str | snapshot |
| old_price | numeric(10,2) | precio publicado antes de borrar |
| new_price | numeric(10,2), nullable | precio detectado en Amazon; `null` si el motivo es `no_longer_deal`/`out_of_stock` |
| reason | str | `"price_increase"` \| `"no_longer_deal"` \| `"out_of_stock"` |
| restored_at | datetime, nullable | |
| restored_deal_id | str, nullable | id del nuevo `Deal` si se restauró |
| created_at | datetime | |

## 5. Lógica de evaluación

Candidatos: `DealRepository.get_active_without_expiry_with_asin()` (método nuevo) → `WHERE status='active' AND expires_at IS NULL AND external_id IS NOT NULL`.

Por cada candidato, `PriceCheckHandler` llama `AmazonProductClient.get_product_preview(external_id)` y decide borrar si se cumple **cualquiera** de:

1. `product.in_stock is False` → `reason="out_of_stock"`.
2. Amazon ya no reporta precio original / porcentaje de descuento (ya no está catalogado como oferta) → `reason="no_longer_deal"`.
3. `product.current_price > deal.current_price * (1 + tolerancia/100)`, con tolerancia = `config.price_tolerance_percent` de `scheduled_tasks` → `reason="price_increase"`.

Si Amazon no devuelve datos para el ASIN (producto no encontrado, error de API), el chollo se deja intacto: no cuenta como afectado ni se borra por fallo de consulta.

## 6. Flujos de ejecución

### Automática (job horario detecta que toca)
1. `handler.preview(config)` evalúa todos los candidatos (llamadas a Amazon incluidas).
2. `handler.execute(candidatos_afectados)` sin confirmación — borra los `Deal` correspondientes.
3. Se crea `scheduled_task_runs` (`trigger_type="automatic"`) + sus `scheduled_task_run_items`.
4. Se actualiza `scheduled_tasks.last_run_at`.
5. Cada borrado individual se registra también en `admin_audit_log` (`action="deal.auto_delete_price_check"`, `user_id=None`, `target_type="deal"`, `target_id=<id>`, `payload={old_price, new_price, reason}`), consistente con el resto de acciones sobre `deals`.

### Manual ("Ejecutar ahora" desde el panel)
1. `POST /admin/scheduled-tasks/{id}/preview` → evalúa candidatos (llama a Amazon), devuelve la lista de afectados **sin borrar nada**.
2. Si `total_affected == 0`: se informa "no hay chollos que borrar", no se crea registro.
3. Si `total_affected > 0`: modal de confirmación (`AlertDialog`, mismo componente que `AdminPostsTable.tsx`) — *"Se van a borrar X chollos, ¿deseas continuar?"* con la lista (imagen, título, tienda, precio anterior → nuevo, motivo).
4. Si confirma: frontend reenvía esa misma lista (los mismos datos recibidos del preview) a `POST /admin/scheduled-tasks/{id}/confirm` → backend borra esos deals exactos (usando los datos ya evaluados, sin re-consultar Amazon una segunda vez) y crea el registro (`trigger_type="manual"`, `triggered_by=<admin_id>`).
5. Si cancela: no se borra nada, no se crea registro.

`preview` y `confirm` son stateless: no hay caché ni token temporal en el servidor — el frontend simplemente conserva en memoria el resultado del preview y lo reenvía tal cual al confirmar.

## 7. API (`app/modules/scheduled_tasks/api/router.py`, todos los endpoints con `require_admin`)

```
GET    /admin/scheduled-tasks
PUT    /admin/scheduled-tasks/{id}
POST   /admin/scheduled-tasks/{id}/preview
POST   /admin/scheduled-tasks/{id}/confirm
GET    /admin/scheduled-tasks/{id}/runs
GET    /admin/scheduled-tasks/runs/{run_id}
DELETE /admin/scheduled-tasks/runs/{run_id}
POST   /admin/scheduled-tasks/runs/bulk-delete
POST   /admin/scheduled-tasks/runs/items/{item_id}/restore
```

`restore` recrea un `Deal` activo a partir del snapshot del item (mismos datos: título, precio, imagen, categoría, tienda, ASIN, urls), marca `restored_at` y guarda `restored_deal_id`. Casos borde:
- **Slug duplicado** (otro deal ocupa ya ese slug desde que se borró el original): al restaurar se genera un slug nuevo con `auto_slug(title)` (`app/modules/deals/domain/utils.py`) en vez de reusar el slug guardado en el snapshot — esa función ya añade un sufijo temporal único a cada slug que genera, igual que en toda alta normal, así que no hay colisión posible.
- **Categoría/tienda ya no existe** (borrada tras el run): la restauración falla con un error explícito ("no se puede restaurar: la tienda/categoría original ya no existe"); no se crea el deal a medias.

## 8. Frontend (`buenchollo-web/`)

- Nueva entrada **"Tareas programadas"** en el nav de `src/routes/admin.tsx`, nueva ruta `src/routes/admin.tareas-programadas.tsx`.
- **Panel de configuración**: toggle activar/desactivar, selector de frecuencia (diario/semanal/quincenal/mensual), hora del día, campo de tolerancia de precio (%), botón "Ejecutar ahora".
- **Modal de confirmación** al ejecutar manualmente: reutiliza `AlertDialog` (`src/components/ui/alert-dialog.tsx`), lista los candidatos con estilo de tabla similar a `AdminDealsTable.tsx` (imagen, título, tienda, precio, motivo).
- **Tabla de registros** (nueva, sin precedente de selección múltiple en el proyecto — se construye desde cero): columnas fecha, tipo (manual/automática), revisados, afectados/borrados, acciones (ver detalle / eliminar). Checkbox por fila + "seleccionar todos" + botón "eliminar seleccionados" (bulk-delete), con `AlertDialog` de confirmación reutilizado.
- **Detalle de un registro**: tabla con el mismo estilo que `AdminDealsTable.tsx` (imagen, título, tienda, precio, motivo, fecha) + botón "Restaurar" por fila que se deshabilita/oculta si `restored_at` ya está seteado.

## 9. Testing

- **Unitarios**: `PriceCheckHandler` (evaluación de candidatos con `AmazonProductClient` mockeado — casos: sube de precio, dentro de tolerancia, sin stock, ya no es oferta, ASIN no encontrado); cálculo de "próxima ejecución debida" según `frequency_preset`/`run_hour`/`last_run_at`.
- **Integración**: `DealRepository.get_active_without_expiry_with_asin`; endpoints `preview`/`confirm`/`runs`/`restore` con BD real de test; verificar que borrar un run hace cascade sobre sus items.
- **E2E**: no se contempla — panel admin interno, no flujo crítico de usuario final.

## 10. Decisiones descartadas / notas

- **Ítems como JSONB en el run** en vez de tabla relacional: descartado — se necesita estado mutable por item (`restored_at`), y la tabla relacional es más consistente con el resto del proyecto (que ya usa tablas normales en vez de blobs, salvo `config`/`payload` puntuales).
- **Migrar los jobs automáticos existentes al motor genérico**: descartado por ahora — no aporta valor inmediato y añade riesgo de romper algo que ya funciona. Se revisará si en el futuro se añaden más tareas al motor y conviene unificar.
- **Tolerancia de precio fija en código (10%, igual que `ScheduledPublicationWorker`)**: descartado — el usuario quiere poder ajustarla desde el panel sin desplegar código.
- **Nota sobre el borrado de caducados existente**: el docstring de `DealCleanerService.clean_expired_deals` dice "3 días" pero el código actual filtra `expires_at` de hace más de 2 días (`timedelta(days=2)`). No es objeto de este diseño, pero queda anotado por si se quiere corregir aparte.
