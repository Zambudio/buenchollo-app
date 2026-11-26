# ADR-025: Publicación automática en la página de Facebook

- **Estado:** aceptada (2026-11-26)
- **Relacionadas:** [ADR-022](ADR-022-publicacion-instagram.md) (Instagram, mismo patrón y misma app de Meta),
  [ADR-023](ADR-023-bus-de-eventos-entre-modulos.md) (bus de eventos),
  [ADR-024](ADR-024-publicacion-canal-whatsapp.md) (WhatsApp)

## Contexto

Los chollos ya salen solos en Telegram, Instagram y el Canal de WhatsApp. Se crea la página de Facebook
«Buenchollo Tech» y se quiere lo mismo allí. Para Instagram ya existen el porfolio empresarial «Buenchollotech», la
app «BuenCholloTech Publicador» y el usuario del sistema `bct-publicador`.

## Opciones

1. **Publicar a mano o con el programador de Meta Business Suite.** Sin código, pero es el trabajo que se quiere quitar.
2. **Reutilizar el módulo de Instagram** con un segundo destino. Mezcla dos APIs distintas (contenedor + publish en
   Instagram, subida directa en Facebook), textos distintos (en Facebook el enlace sí se pulsa) y estados distintos.
3. **Módulo propio `facebook`** con el mismo patrón que Instagram y WhatsApp: suscriptor de `DealPostPublished`,
   cola en BD y job del scheduler.

## Decisión

Opción 3.

- **Token:** el del usuario del sistema del porfolio (`EAA…`, sin caducidad) con `pages_manage_posts`,
  `pages_read_engagement` y `pages_show_list`. En cada pasada con pendientes se pide el token de la página
  (`GET /{page_id}?fields=access_token`); no se guarda en BD ni se renueva.
- **Publicación:** `POST /{page_id}/photos` en multipart (la imagen va en la petición; no hace falta la URL pública
  que necesita Instagram).
- **Texto:** el de Telegram con emojis estándar, **conservando el enlace de compra** y con un aviso de afiliado al pie
  (`FACEBOOK_DISCLOSURE`), porque en Facebook los enlaces se pueden pulsar. La web se enlaza con `/facebook`
  (`utm_source=facebook`) y la analítica tiene la fuente «Facebook».
- **Fallos:** como Instagram: 5 intentos o 24 h, aviso `AdminAlert`; tiempo agotado al publicar = se da por publicada
  (sin duplicados); token inválido o sin permisos = la cola se para y avisa como mucho cada 12 h (en memoria del
  scheduler, sin tabla de cuenta).

## Consecuencias

- Una red más sin tocar Telegram: solo se registra el suscriptor en `app/core/bootstrap.py` y el job en el scheduler.
- El id de la página para la API (`1407115035828198`) **no es** el de la URL del perfil (`61596676873757`).
- Un mismo token de `bct-publicador` sirve para Instagram y Facebook; regenerarlo no revoca el anterior.
- Cambiar el `.env` exige recrear los contenedores (`docker-compose up -d --force-recreate`); `docker restart` no
  recarga el `env_file`.
