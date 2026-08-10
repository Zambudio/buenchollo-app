# ADR-012 — Motor genérico de tareas programadas (handler registrable)

## Estado

**Aceptado** · 2026-08-10 · decisión tomada al implementar la revisión periódica de
precios de Amazon (`docs/superpowers/specs/2026-08-09-tareas-programadas-revision-precios-design.md`).

## Contexto

Los chollos con `expires_at` ya se limpian solos (`DealCleanerService`), pero los
publicados **sin** fecha de expiración quedaban vivos indefinidamente aunque Amazon
subiera el precio o dejara de tenerlos en oferta. Hacía falta una tarea periódica que
los revisara y los borrara cuando dejaran de ser una oferta válida — configurable desde
el panel (frecuencia, activar/desactivar, tolerancia de precio) y con ejecución manual
bajo confirmación.

El proyecto ya tenía un `BackgroundScheduler` de APScheduler con jobs cableados a mano
(`build_deals_scheduler()`), y era la opción obvia para colgar el nuevo job. La pregunta
de diseño real era otra: ¿se construye esta tarea como un job más, específico y aislado,
o como la primera pieza de un motor genérico capaz de admitir futuras tareas programadas
sin rediseñar el esquema ni el scheduler?

## Decisión

Motor genérico con **handler registrable**, en un módulo nuevo
`app/modules/scheduled_tasks/` (Clean Architecture: domain/application/infrastructure/api):

- **Esquema genérico en dos tablas**: `scheduled_tasks` (config: `task_type`, `enabled`,
  `frequency_preset`, `run_hour`, `config` JSON libre por tipo de tarea) y
  `scheduled_task_runs` (registro de cada ejecución: disparo manual/automático,
  contadores, estado). Ambas no asumen nada sobre qué hace la tarea.
- **`TaskHandler` (Protocol)**: `evaluate(deals, config) -> PreviewResult` (síncrono,
  pensado para ejecutarse en threadpool porque hace llamadas HTTP bloqueantes) y
  `execute(candidates) -> list[Candidate]` (async, efectos reales). El router y el
  scheduler son genéricos — resuelven el handler por `task_type` desde un diccionario
  (`{"price_check": handler}`) y no conocen la lógica de negocio de ninguna tarea
  concreta.
- **Un único job horario de auto-chequeo** (`run_due_scheduled_tasks`, `interval`,
  `hours=1`) en vez de un cron por tarea: en cada disparo, calcula qué tareas están
  `enabled` y a las que les toca según `frequency_preset`/`run_hour`/`last_run_at`
  (`is_task_due`, función pura). Cambiar la frecuencia desde el panel no requiere
  reiniciar nada ni reprogramar un job de APScheduler — el siguiente chequeo horario ya
  lo recoge.
- **`PriceCheckHandler`** (primer y único handler implementado) reutiliza el patrón ya
  usado en `ScheduledPublicationWorker._process_one`: `Protocol ProductVerifier`
  inyectado con `AmazonProductClient`.
- **`scheduled_task_run_items`** (snapshot de cada chollo afectado, sin FK hacia
  `deals`/`stores`/`categories` — debe sobrevivir aunque esas filas cambien o se borren)
  es, deliberadamente, **específica de `deals`** (columnas `NOT NULL` como
  `external_id`/`affiliate_url`), no una tabla JSONB genérica — ver "Consecuencias".

## Motivo

- Las dos tablas de config/registro son baratas de mantener genéricas desde el día uno
  y no cuestan nada si al final solo hay una tarea.
- El patrón *handler registrable* es el punto de extensión real: añadir una segunda
  tarea (ej. "revisar enlaces de afiliado rotos") solo exige un nuevo
  `TaskHandler` + una entrada en el diccionario de handlers — sin tocar el scheduler,
  el router genérico ni el esquema de `scheduled_tasks`/`scheduled_task_runs`.
- El job horario de auto-chequeo evita reprogramar APScheduler en caliente (complejidad
  real: `reschedule_job`, persistencia del estado del scheduler) a cambio de una
  latencia máxima de una hora entre "cambiar la config" y "que se aplique" — aceptable
  para una tarea que como mucho corre a diario.

## Alternativas consideradas

- **Job específico y aislado** (sin motor genérico): más simple hoy, pero cualquier
  tarea programada futura repetiría desde cero el patrón config/registro/confirmación
  manual. Descartada porque el coste de generalizar las dos tablas de arriba es casi
  nulo.
- **`scheduled_task_run_items` como columna JSONB genérica** en vez de tabla relacional
  tipada: más genérico de verdad (cualquier tarea guarda cualquier snapshot), pero
  restaurar un item necesita estado mutable por fila (`restored_at`, `restored_deal_id`)
  que un blob JSON no da sin reescribirlo entero cada vez, y el resto del proyecto usa
  tablas normales, no blobs, salvo casos puntuales (`admin_audit_log.payload`).
  Descartada — ver ADR-002 y el principio de "tablas, no blobs" ya asentado.
- **Reprogramar el job de APScheduler dinámicamente al cambiar la config** (`add_job`/
  `reschedule_job` por tarea): más "reactivo", pero añade complejidad de persistencia
  del scheduler y gestión de fallos de reprogramación. El auto-chequeo horario logra el
  mismo resultado práctico con muchísimo menos código.

## Consecuencias

**Positivas**
- Añadir una tarea nueva no requiere tocar el scheduler ni los endpoints del panel de
  "tareas programadas" (listado de config, registros, borrado, historial) — solo el
  handler y su entrada en el registro de handlers.
- Cambiar frecuencia/tolerancia/activar-desactivar desde el panel se aplica sin
  redeploy ni reinicio de contenedor.

**Negativas / trade-offs asumidos**
- `scheduled_task_run_items` es deal-shaped, no genérica de verdad: una futura tarea
  que no borre chollos necesitaría su propia tabla de items o una migración del
  esquema actual. Documentado como deuda técnica (TD-17,
  `docs/project/10-technical-debt.md`) en vez de resolverse especulativamente sin un
  segundo caso de uso real que lo justifique (YAGNI).
- El registro de handlers (`{"price_check": handler}`) está hardcodeado por duplicado
  en `scheduled_tasks/api/router.py` y `scheduled_tasks/application/scheduler.py` en
  vez de una fábrica centralizada — asumible con un solo handler, a revisar si aparece
  el segundo.
- Latencia de hasta 1 hora entre cambiar la config y que el cambio surta efecto en modo
  automático (aceptable dado que la frecuencia mínima es diaria).
