# WhatsApp: publicación automática en el Canal

> Decisión: [ADR-024](../adr/ADR-024-publicacion-canal-whatsapp.md). Código: `buenchollo-api/app/modules/whatsapp/`
> (cola y job) y `whatsapp-gateway/` (pasarela).
>
> **Estado:** activo desde el 2026-11-26 en el Canal «Buenchollo Tech» (`120363409389054215@newsletter`), cuenta propietaria vinculada.

Cada chollo que sale en los canales de Telegram de `WHATSAPP_CHANNELS` (panel o programado) se publica también en
el **Canal de WhatsApp** (`https://whatsapp.com/channel/0029VbD7ZIt4dTnQlrLmfs0Y`): la misma tarjeta de oferta y el
texto de la «versión WhatsApp» (emojis estándar, `*negritas*`, enlace visible a `/whatsapp`, la editada en el panel si
se tocó).

**Copia manual al canal Admin.** Si un canal de Telegram publica solo en WhatsApp (`WHATSAPP_ENABLED` y está en
`WHATSAPP_CHANNELS`, comprobación común en `app/core/channels.py`), ya no se manda la copia «versión WhatsApp» al canal
Admin. Si no, sigue llegando como antes, para no perder ninguna publicación. El panel lo dice al publicar
(`whatsapp_queued` en la respuesta de `/v1/telegram/notify`: «Saldrá en el Canal de WhatsApp en unos minutos»).

| Qué | Canal de WhatsApp | Copia al canal Admin |
|---|---|---|
| Chollo desde el panel o programado (canal en `WHATSAPP_CHANNELS`) | Automático | No |
| Chollo en un canal fuera de `WHATSAPP_CHANNELS` | No | Sí |
| Resumen del domingo (sale en el Admin) | Automático si `admin` cuenta: collage y texto completo, sin repetir el mismo texto en 24 h | Solo si `admin` no cuenta |
| Republicación por bajada de precio | No (pide revisión antes de reenviar) | No, con `WHATSAPP_ENABLED` |

WhatsApp no tiene API oficial para Canales. La pasarela se vincula a la cuenta que administra el Canal como un
**dispositivo vinculado** más (lo mismo que WhatsApp Web) con [Baileys](https://github.com/WhiskeySockets/Baileys),
sin navegador. Solo publica en el Canal: no lee ni contesta chats.

## Cómo funciona

1. Telegram emite `DealPostPublished` con su versión WhatsApp ya preparada (`whatsapp_text`; el módulo `whatsapp` no
   conoce el formato de Telegram). Bus de eventos: [ADR-023](../adr/ADR-023-bus-de-eventos-entre-modulos.md). El
   resumen semanal llega como `WhatsAppPostRequested` y se encola con su propia sesión de BD.
   El suscriptor comprueba el canal y deja el post en `whatsapp_posts` con un margen aleatorio de 45-180 s
   (`not_before`). El mismo chollo no se encola dos veces en 24 h (p. ej. Admin y principal); lo que no es de un chollo,
   tampoco con el mismo texto. Todo lo que toca la BD va en un savepoint: un fallo de WhatsApp nunca aborta la
   transacción de Telegram.
2. El job `publish_whatsapp_queue` (scheduler, cada minuto) publica **como mucho una** por paso y solo si:
   - han pasado `WHATSAPP_MIN_INTERVAL_MINUTES` (20) desde la anterior, y
   - hoy (hora de Madrid) no se ha llegado a `WHATSAPP_DAILY_LIMIT` (15).
   Lo que no cabe espera al siguiente hueco; a las 12 h se descarta y se avisa.
3. Pide a la pasarela (`http://buenchollo-whatsapp:3000/send`, red interna, `WHATSAPP_GATEWAY_TOKEN`) que la publique.
   La pasarela solo responde 200 cuando **WhatsApp acusa recibo** del mensaje (no basta con escribirlo en el socket).
   Respuestas de la pasarela y qué hace el job:

   | HTTP | Significado | Job |
   |---|---|---|
   | 200 | WhatsApp lo aceptó | Publicada |
   | 502 / 500 | Subida fallida (tope de 75 s) o WhatsApp lo rechazó | Intento fallido; desde el 3.º, solo texto; al 5.º, error y aviso |
   | 503 | WhatsApp sin vincular | Sin intento; aviso como mucho cada 6 h |
   | 504 | Enviado, pero sin acuse en 20 s | Se da por publicada y se avisa para revisar el Canal (sin duplicados) |
   | 401 / 403 | Token distinto entre API y pasarela | Sin intento; aviso de configuración |
   | sin respuesta tras enviar | Igual que 504 (la API espera hasta 120 s, más que la subida y el acuse juntos) | |
4. El Canal (`WHATSAPP_CHANNEL`, JID o enlace) y el rol de la cuenta (propietaria o administradora) se comprueban al
   empezar y cada 6 h. Si no se encuentra o la cuenta no lo administra: no publica, no gasta intentos y avisa.

Ritmo real: ~10 al día, una por hora. Con los límites por defecto nunca salen dos seguidas en menos de 20 min.

### Imágenes en Canales

Los Canales no van cifrados: la imagen se sube en claro a `/newsletter/newsletter-image` y el mensaje sale como
`<plaintext mediatype="image">`. Baileys 7.0.0-rc14 aún lo hace como en un chat y la imagen no se ve
([#2199](https://github.com/WhiskeySockets/Baileys/issues/2199), PR #2434 sin integrar), así que
`whatsapp-gateway/src/newsletter.js` lo hace como WhatsApp Web. Si algún día falla, el job publica solo el texto.

Detalles que no se ven en el código a primera vista:

- Por **enlace de invitación** WhatsApp no devuelve el rol de quien pregunta (`viewer_metadata`); la pasarela repite la
  consulta por JID. En producción `WHATSAPP_CHANNEL` es directamente el JID.
- El acuse llega como `<ack id="…">` (evento `CB:ack,id:<id>` del socket de Baileys); con `error` es un rechazo. La
  espera se arma antes de enviar para no perder un acuse rápido.

### Secretos

La pasarela **no** recibe el `.env` de la API: solo `WHATSAPP_GATEWAY_TOKEN` y `WHATSAPP_PAIRING_PHONE`, que
`docker-compose` toma del `.env` del proyecto (`environment:` con `${…}`). Si se lanzara desde la interfaz de Container
Manager, que no sustituye `${…}`, el token quedaría vacío y la pasarela se quedaría en espera sin conectar (falla segura).
La sesión vinculada (`whatsapp-gateway/data/auth`) equivale a tener WhatsApp abierto: fuera de git.

## Puesta en marcha (una vez)

1. **Variables** en el `.env` del NAS (`buenchollo-api/.env`):
   ```
   WHATSAPP_ENABLED=true
   WHATSAPP_GATEWAY_TOKEN=<aleatorio, ≥ 24 caracteres: python -c "import secrets;print(secrets.token_urlsafe(32))">
   WHATSAPP_CHANNEL=https://whatsapp.com/channel/0029VbD7ZIt4dTnQlrLmfs0Y
   WHATSAPP_CHANNELS=main,admin
   # Opcional: vincular con número en vez de QR (con prefijo, sin «+»)
   # WHATSAPP_PAIRING_PHONE=34600000000
   ```
2. **Levantar la pasarela** y recrear API y scheduler (leen el `.env` nuevo y aplican la migración
   `20261126120000`), por SSH ([NAS-SSH.md](NAS-SSH.md)). Synology no crea las carpetas de los volúmenes: antes,
   crear `whatsapp-gateway/data` (vacía).
   ```
   $DC build buenchollo-whatsapp && $DC up -d buenchollo-whatsapp
   $DC up -d --force-recreate buenchollo-api buenchollo-scheduler
   ```
3. **Vincular** con el móvil que administra el Canal: WhatsApp → *Dispositivos vinculados* → *Vincular un
   dispositivo* y escanear `whatsapp-gateway/data/qr.png` (se abre desde el PC en el share; se renueva cada ~20 s).
   Con `WHATSAPP_PAIRING_PHONE`, el código de 8 letras sale en el log de `buenchollo-whatsapp`: *Vincular con número
   de teléfono*. Al conectar, el log dice «WhatsApp conectado» y `qr.png` desaparece.
4. **Comprobar**: `GET /v1/whatsapp/status` (admin) → `gateway.connection = "open"`. El primer chollo que salga en
   Telegram aparecerá en el Canal unos minutos después.

La sesión vinculada se guarda en `whatsapp-gateway/data/auth` (fuera de git: equivale a tener WhatsApp abierto en
ese dispositivo). Si se cierra la sesión desde el móvil, la pasarela la borra, genera un QR nuevo y llega un aviso.

## Operación

- **Apagar**: `WHATSAPP_ENABLED=false` y `$DC up -d --force-recreate buenchollo-scheduler`. Lo pendiente se queda en
  la cola (caduca a las 12 h).
- **Estado y cola**: `GET /v1/whatsapp/status`; tabla `whatsapp_posts` (`pending`/`published`/`error`, `last_error`).
- **Desvincular**: desde el móvil (*Dispositivos vinculados* → cerrar sesión) o borrar `whatsapp-gateway/data/auth`
  con el contenedor parado.
- **Actualizar Baileys**: subir la versión fijada en `whatsapp-gateway/package.json`, `npm install`, `npm test` y
  `$DC build buenchollo-whatsapp && $DC up -d buenchollo-whatsapp`. Si WhatsApp cambia el protocolo, la pasarela
  deja de conectar y llegan avisos: hay que actualizar.

## Riesgos asumidos

- **No es una API oficial**: WhatsApp puede limitar o bloquear cuentas que automatizan. Se reduce con un uso como
  el de una persona (≤ 15 al día, ≥ 20 min entre publicaciones, margen aleatorio, solo el propio Canal, sin
  mensajes a contactos) y con una sola sesión estable (no se vincula y desvincula a menudo). Si WhatsApp avisa o
  bloquea, apagar con `WHATSAPP_ENABLED=false` y volver a la copia manual desde el canal Admin.
- **Dependencia de una librería no oficial** (Baileys, versión fijada): puede romperse con cambios de WhatsApp.
