# WhatsApp: publicación automática en el Canal

> Decisión: [ADR-024](../adr/ADR-024-publicacion-canal-whatsapp.md). Código: `buenchollo-api/app/modules/whatsapp/`
> (cola y job) y `whatsapp-gateway/` (pasarela).
>
> **Estado:** listo para activar; falta vincular la cuenta y poner las variables en el `.env` del NAS.

Cada chollo que sale en los canales de Telegram de `WHATSAPP_CHANNELS` (panel o programado) se publica también en
el **Canal de WhatsApp** (`https://whatsapp.com/channel/0029VbD7ZIt4dTnQlrLmfs0Y`): la misma tarjeta de oferta y el
texto de la «versión WhatsApp» (emojis estándar, `*negritas*`, enlace visible a `/whatsapp`). La copia al canal Admin
de Telegram sigue saliendo igual, por si hay que publicar a mano.

WhatsApp no tiene API oficial para Canales. La pasarela se vincula a la cuenta que administra el Canal como un
**dispositivo vinculado** más (lo mismo que WhatsApp Web) con [Baileys](https://github.com/WhiskeySockets/Baileys),
sin navegador. Solo publica en el Canal: no lee ni contesta chats.

## Cómo funciona

1. Telegram emite `DealPostPublished` (bus de eventos, [ADR-023](../adr/ADR-023-bus-de-eventos-entre-modulos.md)).
   El suscriptor de WhatsApp comprueba el canal y deja el post en `whatsapp_posts` con un margen aleatorio de
   45-180 s (`not_before`). El mismo chollo no se encola dos veces en 24 h (p. ej. Admin y principal).
2. El job `publish_whatsapp_queue` (scheduler, cada minuto) publica **como mucho una** por paso y solo si:
   - han pasado `WHATSAPP_MIN_INTERVAL_MINUTES` (20) desde la anterior, y
   - hoy (hora de Madrid) no se ha llegado a `WHATSAPP_DAILY_LIMIT` (15).
   Lo que no cabe espera al siguiente hueco; a las 12 h se descarta y se avisa.
3. Pide a la pasarela (`http://buenchollo-whatsapp:3000/send`, red interna, `WHATSAPP_GATEWAY_TOKEN`) que la publique.
4. Errores, con aviso al canal Admin (`AdminAlert`):
   - pasarela caída o WhatsApp sin vincular: no gasta intentos; aviso como mucho cada 6 h;
   - fallo al publicar: hasta 5 intentos; desde el 3.º sale **solo el texto** (con su enlace);
   - tiempo agotado tras enviar: se da por publicada y se avisa para revisar el Canal (sin duplicados);
   - la cuenta vinculada no es propietaria ni administradora del Canal: no publica y avisa.

Ritmo real: ~10 al día, una por hora. Con los límites por defecto nunca salen dos seguidas en menos de 20 min.

### Imágenes en Canales

Los Canales no van cifrados: la imagen se sube en claro a `/newsletter/newsletter-image` y el mensaje sale como
`<plaintext mediatype="image">`. Baileys 7.0.0-rc14 aún lo hace como en un chat y la imagen no se ve
([#2199](https://github.com/WhiskeySockets/Baileys/issues/2199), PR #2434 sin integrar), así que
`whatsapp-gateway/src/newsletter.js` lo hace como WhatsApp Web. Si algún día falla, el job publica solo el texto.

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
   `20261126120000`), por SSH ([NAS-SSH.md](NAS-SSH.md)):
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
