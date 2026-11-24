# ADR-023 — Bus de eventos en proceso para desacoplar módulos

## Estado

Aceptado · 2026-11-24 · en producción.

## Contexto

Al conectar Instagram, la primera versión hacía que `telegram` (router de `/notify`) y `scheduled_deals` (worker de
publicaciones programadas) importasen la cola de `instagram`, e `instagram` importaba `TelegramBot` para avisar al
administrador. Cada red nueva (X, Threads, otra) habría obligado a tocar Telegram y el worker, y los módulos
acabarían dependiendo unos de otros en cadena. La aplicación va a seguir creciendo: un módulo no debe conocer a los
que reaccionan a lo que hace.

## Decisión

1. **Bus de eventos mínimo en `app/core/events.py`**, en memoria y dentro del mismo proceso:
   `subscribe(tipo, handler)` y `publish(evento)`. Los handlers pueden ser síncronos o asíncronos; se ejecutan en
   orden y **un suscriptor que falla nunca afecta al emisor ni a los demás** (se registra en el log).
2. **Eventos como dataclasses inmutables** en el mismo fichero:
   - `DealPostPublished`: un chollo acaba de salir en un canal de Telegram (canal, texto enviado, chollo, tarjeta,
     URL de la foto, descargador seguro y la sesión de BD del emisor, para que lo que guarde el suscriptor entre en
     la misma transacción en un savepoint propio).
   - `AdminAlert`: aviso para el administrador.
3. **Raíz de composición única** (`app/core/bootstrap.py → register_subscribers()`): es el único sitio que sabe quién
   escucha a quién. La llaman los dos procesos que emiten eventos: la API (`app/main.py`, al cargarse) y el
   scheduler dedicado (`app/run_scheduler.py`). Es idempotente. Un test en proceso aparte comprueba que ambos lo hacen.
4. **Suscriptores actuales**: `instagram.application.subscriber.on_deal_post_published` (encola si el canal está en
   `INSTAGRAM_CHANNELS`) y `telegram.application.admin_alerts.send_admin_alert` (envía el aviso al canal Admin).
5. **Regla**: un módulo no importa la aplicación o la infraestructura de otro para reaccionar a lo que hace; emite o
   escucha un evento. (Las relaciones ORM entre modelos siguen la regla existente de importar el modelo destino.)

## Consecuencias

- **Positivas:** añadir una red es crear su módulo, un suscriptor y una línea en `bootstrap.py`; Telegram y el worker
  no cambian. `instagram` no importa nada de `telegram` y viceversa. Los fallos de una red no rompen las demás.
- **Negativas:** el flujo ya no se lee de corrido en un solo fichero (hay que mirar `bootstrap.py`). Es en proceso:
  si en el futuro hiciera falta repartir el trabajo entre procesos o máquinas, se sustituye `publish` por una cola
  (los emisores no cambian).
- **Alternativas descartadas:** llamadas directas entre módulos (acoplamiento que crece con cada red); una cola
  externa (Redis, RabbitMQ) — más infraestructura en el NAS sin necesidad con el volumen actual.
