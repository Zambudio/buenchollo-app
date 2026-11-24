# ADR-022 — Publicación automática de los chollos en el feed de Instagram

## Estado

Aceptado · 2026-11-24 · código en producción; se activa con `INSTAGRAM_ENABLED=true` cuando haya token.

## Contexto

Pedro pasó la cuenta de Instagram a profesional y quiere publicar en el feed los mismos chollos que en el canal de
Telegram (unos 10 al día): la misma tarjeta de oferta (1200 × 800, ya comprobada en el feed) y el texto adaptado,
con «enlace en la bio» apuntando a la web y el tráfico medido aparte. Las historias quedan para más adelante.

Restricciones de Instagram:

- Publicar por API exige que **Instagram descargue la imagen de una URL pública** (no admite subirla).
- La publicación es en dos pasos (contenedor → `media_publish`) y el contenedor puede tardar en procesarse.
- Los enlaces del pie de foto no se pueden pulsar.
- El token de larga duración caduca a los 60 días si no se renueva.

La API (contenedor `buenchollo-api`) y los jobs (`buenchollo-scheduler`) son procesos distintos en el NAS: no
comparten memoria ni disco de trabajo.

## Decisión

1. **API de Instagram con inicio de sesión de Instagram** (`graph.instagram.com`), sin página de Facebook, con una app
   de Meta en modo desarrollo (solo publicamos en nuestra cuenta, sin revisión de Meta).
2. **Cola en la BD** (`instagram_posts`): al publicar un chollo en los canales de Telegram de `INSTAGRAM_CHANNELS`
   (en producción el principal y el Admin, donde salen las programadas), el panel y el worker de
   programadas encolan el texto adaptado y el JPEG. Un job del scheduler (cada 2 min) los publica. Telegram nunca
   espera a Instagram ni falla por él, y la cola funciona igual venga el post de la API o del scheduler.
3. **La imagen se sirve desde la propia API** (`GET /v1/instagram/media/{id}.jpg`, pública): id aleatorio, solo
   mientras está pendiente y 48 h como mucho, sin caché; se borra de la BD al publicarse. Sin almacenamiento externo.
4. **Misma imagen que Telegram**: la tarjeta de oferta; si el post salió con la foto original, esa foto encajada en un
   lienzo blanco 1200 × 800 (Instagram rechaza proporciones extremas).
5. **Texto** derivado del que salió en Telegram: sin enlaces, emojis estándar, «🔗 Enlace al chollo en nuestra bio» y
   hashtags (los de categoría y los fijos de `INSTAGRAM_HASHTAGS`).
6. **Fallos**: hasta 5 intentos en 24 h y aviso al canal Admin. Si `media_publish` no responde, se da por publicado y se
   avisa (como en Telegram: antes un aviso que un duplicado).
7. **Token**: `INSTAGRAM_ACCESS_TOKEN` siembra `instagram_account`; el job lo renueva cada 7 días y guarda el vigente
   en la BD (RLS sin políticas). Un token nuevo en el `.env` se detecta por su hash. Va en la cabecera
   `Authorization`, nunca en URLs ni logs.
8. **Medición**: la bio enlaza a `/instagram` (redirige con `utm_source=instagram`) y la analítica first-party tiene
   la fuente `instagram`, como ya ocurría con WhatsApp.

## Consecuencias

- **Positivas:** un canal más sin trabajo manual y con la misma imagen; aislado de Telegram; sin servicios ni
  dependencias nuevas; tráfico de Instagram medible.
- **Negativas:** la imagen pasa por la API pública (si Cloudflare bloquease a Meta habría que permitirlo); hay que
  regenerar el token a mano si Meta lo invalida (llega un aviso); el post de Instagram sale con hasta ~2 min de retraso.
- **Alternativas descartadas:** publicar directamente en la petición del panel (lento y acoplado a Instagram);
  guardar las imágenes en disco compartido o en Supabase Storage (más piezas que una tabla con caducidad);
  herramientas de terceros de programación (coste y dependencia externa).
