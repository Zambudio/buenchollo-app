# CambiosAlertasCodex

Fecha: 2026-05-24

Documento de auditoria de los cambios realizados por Codex en el modulo de alertas, notificaciones y feed del home.

## Objetivo funcional

Se trabajo sobre dos lineas principales:

1. Convertir el panel de alertas en una experiencia tipo Chollometro: el usuario escribe palabras clave o productos, crea una alerta, y cuando se publique un chollo que coincida se genera una notificacion in-app.
2. Cambiar la seccion `TRANSMISION_EN_VIVO` del home para que muestre todos los chollos publicados, cargando mas elementos al bajar por la pagina.

No se integro envio de correo. La decision fue dejar la notificacion por campana/in-app como primer paso, y reservar email para una fase posterior.

## Archivos creados

### Backend

- `buenchollo-api/app/modules/alerts/application/__init__.py`
- `buenchollo-api/app/modules/alerts/application/alert_matcher.py`
- `buenchollo-api/app/modules/notifications/__init__.py`
- `buenchollo-api/app/modules/notifications/api/__init__.py`
- `buenchollo-api/app/modules/notifications/api/router.py`
- `buenchollo-api/app/modules/notifications/api/schemas.py`
- `buenchollo-api/app/modules/notifications/domain/__init__.py`
- `buenchollo-api/app/modules/notifications/domain/models.py`
- `buenchollo-api/app/modules/notifications/infrastructure/__init__.py`
- `buenchollo-api/app/modules/notifications/infrastructure/repository.py`

### Frontend

- `buenchollo-web/src/routes/alertas_.nueva.tsx`
- `buenchollo-web/src/services/api/notifications.ts`

## Archivos modificados

### Backend

- `buenchollo-api/app/main.py`
- `buenchollo-api/app/modules/alerts/domain/models.py`
- `buenchollo-api/app/modules/alerts/infrastructure/repository.py`
- `buenchollo-api/app/modules/deals/api/router.py`
- `buenchollo-api/app/modules/deals/application/deal_service.py`
- `buenchollo-api/app/modules/deals/infrastructure/repository.py`

### Frontend

- `buenchollo-web/src/components/Header.tsx`
- `buenchollo-web/src/routeTree.gen.ts`
- `buenchollo-web/src/routes/alertas.tsx`
- `buenchollo-web/src/routes/index.tsx`
- `buenchollo-web/src/routes/notificaciones.tsx`
- `buenchollo-web/src/services/api/deals.ts`

### Archivo eliminado

- `buenchollo-web/src/routes/alertas.nueva.tsx`

Motivo: en TanStack Router, `alertas.nueva.tsx` se estaba resolviendo como ruta hija de `/alertas`. Como `alertas.tsx` no renderiza un `Outlet`, al navegar a `/alertas/nueva` se mostraba la pagina padre `Mis alertas`. Se sustituyo por `alertas_.nueva.tsx`, que mantiene la URL publica `/alertas/nueva` pero evita el anidamiento.

## Cambios de backend

### Registro de routers

En `buenchollo-api/app/main.py` se registraron los routers:

- `alerts_router`
- `notifications_router`

Esto expone:

- `GET /alerts`
- `POST /alerts`
- `PUT /alerts/{alert_id}`
- `DELETE /alerts/{alert_id}`
- `GET /notifications`
- `GET /notifications/unread-count`
- `POST /notifications/mark-read`

### Modelo de notificaciones

Se creo `Notification` en `buenchollo-api/app/modules/notifications/domain/models.py`.

Campos principales:

- `id`
- `user_id`
- `type`
- `title`
- `body`
- `link_url`
- `deal_id`
- `alert_id`
- `is_read`
- `created_at`

Decision tecnica:

- Se uso el enum PostgreSQL existente `notification_type` mediante `ENUM(..., create_type=False)` para no intentar recrear el tipo en BD.
- Se mantuvieron relaciones opcionales con `Deal` y `Alert`.

### Repositorio de notificaciones

Se creo `NotificationRepository` con:

- `get_by_user(user_id, limit)`
- `count_unread(user_id)`
- `exists_for_alert_deal(alert_id, deal_id)`
- `create(data)`
- `mark_unread_as_read(user_id)`

Decision tecnica:

- Se evita duplicar notificaciones para el mismo par `alert_id + deal_id`.
- La escritura se hace con `flush()` para respetar la transaccion abierta por `get_db`.

### API de notificaciones

Se creo `buenchollo-api/app/modules/notifications/api/router.py`.

Endpoints:

- `GET /notifications`: lista las ultimas notificaciones del usuario autenticado.
- `GET /notifications/unread-count`: devuelve `{ "count": number }` para la campana.
- `POST /notifications/mark-read`: marca como leidas las notificaciones pendientes.

Decision tecnica:

- Todos los endpoints usan `get_current_user`.
- No se permite insertar notificaciones desde el frontend. Las crea el sistema cuando hay match de alertas.

### Modelo de alertas

Se ampliaron campos del modelo `Alert`:

- `frequency`
- `notify_email`
- `notify_in_app`
- `last_triggered_at`

Decision tecnica:

- `notify_email` queda preparado para una futura integracion de correo.
- `notify_in_app` permite activar/desactivar notificaciones por campana.
- `last_triggered_at` permite auditar o limitar frecuencia en una fase posterior.

### Matching de alertas

Se creo `AlertMatcher` en `buenchollo-api/app/modules/alerts/application/alert_matcher.py`.

Responsabilidad:

- Recibe un `Deal`.
- Busca alertas activas que coincidan.
- Crea notificaciones in-app para los usuarios con alertas compatibles.
- Marca la alerta como disparada actualizando `last_triggered_at`.

Criterios de coincidencia:

- El chollo debe estar `active`.
- La alerta debe estar activa.
- La alerta debe tener `notify_in_app = true`.
- Si la alerta tiene categoria, debe coincidir con `category_id` o `subcategory_id`.
- Si tiene tienda, debe coincidir con `store_id`.
- Si tiene precio minimo/maximo, se compara con `current_price`.
- Si tiene descuento minimo, se compara con `discount_percentage`.
- Si tiene marca, se comprueba contra `deal.brand`.
- Si tiene palabra clave, se compara contra titulo, descripcion y short description.

Decision tecnica:

- El matching de keyword se hizo tolerante:
  - Si la frase exacta aparece, hay match.
  - Si no aparece la frase exacta, se exige que todos los tokens aparezcan en el texto.
- Se normaliza texto para reducir problemas con mayusculas/minusculas y acentos.

### Integracion con creacion/actualizacion de chollos

En `DealService`:

- `create_deal()` llama a `AlertMatcher.notify_matching_alerts()` tras crear un chollo.
- `update_deal()` tambien lo llama si el resultado queda `active`.

Decision tecnica:

- La logica de alertas queda en application layer, no en router.
- El router solo inyecta dependencias (`DealRepository`, `AlertRepository`, `NotificationRepository`).
- Se mantiene el patron modular del proyecto.

### Paginacion de chollos

Se modifico `DealRepository.search_active()` para aceptar:

- `limit`
- `offset`

Y `GET /deals` ahora acepta:

- `category_id`
- `store_id`
- `search`
- `limit`
- `offset`

Decision tecnica:

- Se usa `offset + limit` por simplicidad y compatibilidad con el estado actual.
- Es suficiente para el volumen inicial del proyecto.
- Si el volumen crece mucho, se puede migrar a paginacion por cursor usando `published_at` e `id`.

## Cambios de frontend

### Nueva pantalla de crear alerta

Se reemplazo la ruta anterior por `buenchollo-web/src/routes/alertas_.nueva.tsx`.

La URL publica sigue siendo:

```text
/alertas/nueva
```

Nuevo enfoque de UX:

- Titulo principal: `No te pierdas ninguna oferta`.
- Input principal: `Crea tu alerta`.
- Chips de inspiracion:
  - `consola ps5`
  - `iphone`
  - `nintendo switch 2`
  - `rtx 5090`
  - `macbook air`
  - `ssd 2tb`
  - `monitor 4k`
  - `airpods pro`
  - `tv oled`
  - `steam deck`
  - `portatil gaming`
- Opcion `Ofertas super calientes`, que crea una alerta basada en descuento minimo.
- Seccion secundaria `Afina tu alerta` con:
  - Categoria
  - Tienda
  - Marca
  - Precio maximo
  - Descuento minimo

Decision tecnica:

- La alerta se crea mediante `alertsApi.create()`.
- No se llama directamente a Supabase desde esta pantalla.
- Se conserva la posibilidad de filtrar, pero el flujo principal es palabra clave/producto.

### Pagina de alertas

En `buenchollo-web/src/routes/alertas.tsx`:

- Se mantiene listado de alertas.
- Se mejoro el manejo de errores para que si falla la API se muestre un estado de error y boton `REINTENTAR`, en vez de simular que no hay alertas.

### Campana del header

En `buenchollo-web/src/components/Header.tsx`:

- Se elimino la consulta directa a `supabase.from("notifications")`.
- Se usa `notificationsApi.unreadCount()`.
- La campana se actualiza:
  - al cargar,
  - al recuperar foco de ventana,
  - cada 60 segundos,
  - al recibir el evento `notifications:changed`.

Decision tecnica:

- Se avanza en el cumplimiento de ADR-002: el frontend no consulta Supabase DB directamente.

### Pagina de notificaciones

En `buenchollo-web/src/routes/notificaciones.tsx`:

- Se elimino la lectura directa a Supabase.
- Se usa `notificationsApi.list()`.
- Tras cargar, se llama a `notificationsApi.markRead()`.
- Luego se emite `window.dispatchEvent(new Event("notifications:changed"))` para refrescar la campana.
- Si `link_url` existe, el titulo de la notificacion enlaza al chollo.

### Servicio de notificaciones

Se creo `buenchollo-web/src/services/api/notifications.ts`.

Funciones:

- `list()`
- `unreadCount()`
- `markRead()`

### Home con feed infinito

En `buenchollo-web/src/routes/index.tsx`:

- La seccion `TRANSMISION_EN_VIVO` ya no carga solo `getLatest(8)`.
- Ahora usa `dealsService.search({ limit, offset })`.
- Carga chollos en bloques de 16.
- Usa `IntersectionObserver` con un sentinel al final del grid.
- Al bajar por la pagina, carga mas chollos publicados.

Estados de UI:

- `CARGANDO_CHOLLOS...`
- `FIN_DE_TRANSMISION`
- `SIN_CHOLLOS_PUBLICADOS`

Decision tecnica:

- Se mantiene la seccion `MAS_POPULARES` separada.
- La transmision en vivo representa el feed general por `published_at desc`.
- Se incluyo un fallback defensivo: si el backend viejo ignora `offset`, el frontend detecta duplicados y evita un bucle infinito. Esto permite que no se rompa mientras se despliega el backend actualizado.

### Servicio de chollos

En `buenchollo-web/src/services/api/deals.ts`:

- `search()` acepta ahora `offset`.
- El home usa `favoritesApi.getFavorites()` para cargar favoritos del usuario en vez de consultar Supabase directamente.

## Decisiones tecnicas relevantes

### 1. Notificacion in-app antes que email

No se implemento correo porque el proyecto aun no tiene proveedor ni configuracion SMTP/API. Se dejo preparado el modelo con `notify_email`, pero el primer canal funcional es la campana.

### 2. Sistema de alertas en application layer

La generacion de notificaciones por match vive en `AlertMatcher`, dentro de `alerts/application`.

Motivo:

- Evitar logica de negocio en routers.
- Mantener Clean Architecture pragmatica.
- Facilitar extender a email en el futuro.

### 3. Evitar duplicados

Antes de crear una notificacion se comprueba si ya existe una notificacion `alert_match` para ese `alert_id` y `deal_id`.

Motivo:

- Si un chollo se actualiza varias veces, no debe llenar la campana con duplicados.

### 4. Ruta `alertas_.nueva.tsx`

Se uso la convencion de TanStack Router con `_` para evitar anidamiento bajo `/alertas`.

Motivo:

- `alertas.nueva.tsx` estaba generando conflicto visual: la URL era `/alertas/nueva`, pero se renderizaba la pagina padre.

### 5. Paginacion offset/limit

Se eligio `offset` por simplicidad.

Motivo:

- Encaja con el endpoint existente.
- Es facil de auditar.
- No requiere cambiar contratos de respuesta.

## Verificaciones ejecutadas

Backend:

```bash
python -m compileall app\modules\alerts app\modules\notifications
python -m compileall app\modules\deals
pytest app/tests/test_deals_api.py -q
pytest app/tests/test_deals_api.py app/tests/test_categories_stores_api.py -q
```

Frontend:

```bash
npm run build
```

Comprobaciones manuales:

- Se comprobo que `GET /openapi.json` expone:
  - `/alerts`
  - `/alerts/{alert_id}`
  - `/notifications`
  - `/notifications/unread-count`
  - `/notifications/mark-read`
- Se comprobo que `localhost:8080/alertas/nueva` renderiza la pantalla nueva y no la pagina `Mis alertas`.
- Se comprobo que el home renderiza la seccion `TRANSMISION_EN_VIVO` con el nuevo sentinel de carga.

## Riesgos y pendientes

### Despliegue backend NAS

El frontend puede mostrar la nueva UI, pero las funciones nuevas dependen del backend actualizado.

Pendiente:

- Desplegar cambios de `buenchollo-api` en el NAS.
- Reiniciar el contenedor backend.

Sin ese despliegue:

- Crear/listar alertas puede fallar si el backend desplegado no tiene `/alerts`.
- La campana puede fallar si el backend desplegado no tiene `/notifications/unread-count`.
- La paginacion real del home no funcionara si el backend desplegado no soporta `offset`.

### Email

Queda pendiente decidir proveedor:

- SMTP propio
- Resend
- Sendgrid
- Mailgun
- Supabase Edge Function

Punto natural de integracion:

- `AlertMatcher.notify_matching_alerts()`

### Matching avanzado

El matching actual es suficiente para MVP, pero no incluye:

- sinonimos,
- tolerancia a typos,
- stemming,
- busqueda semantica,
- preferencias por usuario,
- frecuencia diaria/semanal.

### Rutas y generado automatico

`buenchollo-web/src/routeTree.gen.ts` fue regenerado por TanStack Router tras mover `alertas.nueva.tsx` a `alertas_.nueva.tsx`.

## Resumen ejecutivo

Se implemento una base funcional para alertas:

- El usuario crea alertas por palabra clave/producto.
- Las alertas se guardan via FastAPI.
- Cuando se crea o activa un chollo que coincide, se crea una notificacion in-app.
- La campana del header muestra el numero de notificaciones sin leer via API.
- La pagina de notificaciones lista y marca como leidas via API.
- El home pasa a mostrar un feed de chollos publicados con carga progresiva.

La funcionalidad queda lista para auditar en local y pendiente de despliegue en NAS para que funcione en el entorno servido por `https://embyzambu.synology.me:8000`.
