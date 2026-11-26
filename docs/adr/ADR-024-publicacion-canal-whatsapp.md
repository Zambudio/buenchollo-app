# ADR-024: Publicación automática en el Canal de WhatsApp

- **Estado:** aceptada (2026-11-26)
- **Relacionadas:** [ADR-022](ADR-022-publicacion-instagram.md) (Instagram, mismo patrón de cola),
  [ADR-023](ADR-023-bus-de-eventos-entre-modulos.md) (bus de eventos)

## Contexto

Desde el 2026-11-20 cada publicación de Telegram manda al canal Admin una «versión WhatsApp» para copiarla a mano
al Canal de WhatsApp. En la práctica es lento: hay que copiar la imagen, pegarla en WhatsApp y luego el texto (en
Telegram basta con reenviar del Admin al canal principal). Son ~10 publicaciones al día, una por hora.

WhatsApp no ofrece API oficial para Canales: la WhatsApp Business Cloud API solo envía mensajes a usuarios.

## Opciones

1. **Seguir a mano.** Sin riesgo, pero es lo que se quiere quitar.
2. **Servicio de pago de terceros** (Whapi, etc.). Igual de no oficial y, además, la sesión de WhatsApp en
   servidores ajenos y una cuota mensual.
3. **whatsapp-web.js / WAHA (WEBJS)**: WhatsApp Web real en Chromium. Más pesado en el NAS (navegador permanente,
   ~400 MB) y el envío de imágenes a Canales tampoco está confirmado en sus versiones públicas.
4. **Baileys en un contenedor propio** (protocolo de dispositivo vinculado por WebSocket, sin navegador).

## Decisión

Opción 4: contenedor `buenchollo-whatsapp` (`whatsapp-gateway/`, Node 22 + Baileys 7.0.0-rc14 fijada) con una API
HTTP mínima en la red interna de Docker (`/status`, `/channel`, `/send`, con token). La API mantiene toda la lógica
en un módulo `whatsapp`, igual que Instagram: suscriptor de `DealPostPublished` → cola `whatsapp_posts` → job del
scheduler cada minuto.

- **Ritmo de persona**: una publicación por paso como mucho, ≥ 20 min entre dos, ≤ 15 al día, margen aleatorio de
  45-180 s tras Telegram, nada de mensajes a contactos. Configurable (`WHATSAPP_MIN_INTERVAL_MINUTES`,
  `WHATSAPP_DAILY_LIMIT`).
- **Imágenes**: Baileys aún sube las de Canales por la ruta de chats y no se ven (issue #2199). La pasarela lo hace
  como WhatsApp Web (`/newsletter/newsletter-image`, `mediatype="image"`) en código propio, sin bifurcar la
  librería. Si la imagen falla dos veces, el chollo sale solo con texto.
- **Sin duplicados**: el mismo chollo no se encola dos veces en 24 h; un tiempo agotado tras enviar cuenta como
  publicado y se avisa (como en Telegram e Instagram).
- La copia manual al canal Admin de Telegram se mantiene como respaldo.

## Consecuencias

- Un servicio más en el NAS (sin puerto publicado). Su sesión (`whatsapp-gateway/data`) es un secreto: fuera de git.
- Riesgo asumido por Pedro: automatizar una cuenta de WhatsApp va contra sus condiciones y puede acabar en
  limitación o bloqueo. Se mitiga con el ritmo y con `WHATSAPP_ENABLED=false` como interruptor.
- Baileys es una librería no oficial: actualizarla cuando WhatsApp cambie el protocolo (la pasarela deja de
  conectar y llega un aviso).
- Puesta en marcha y operación: [`docs/guides/WHATSAPP.md`](../guides/WHATSAPP.md).
