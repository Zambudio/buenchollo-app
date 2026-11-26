# Facebook: publicación automática en la página

> Código: `buenchollo-api/app/modules/facebook/`. Mismo patrón que Instagram ([INSTAGRAM.md](INSTAGRAM.md)):
> suscriptor de `DealPostPublished` en el bus de eventos, cola en BD y job del scheduler.
>
> **Estado:** código listo y apagado (`FACEBOOK_ENABLED=false`) hasta tener el token de la página.

Cada chollo que sale en los canales de Telegram de `FACEBOOK_CHANNELS` (panel o programado) se publica también
en la página **Buenchollo Tech** (id `61596676873757`): la misma imagen (tarjeta de oferta) y el texto adaptado.

## Cómo funciona

1. Telegram emite `DealPostPublished`; el suscriptor (`application/subscriber.py`) comprueba el canal y deja el post
   en `facebook_posts` (texto y JPEG). Nunca bloquea ni hace fallar Telegram.
2. El job `publish_facebook_queue` (scheduler, cada 2 min), si hay pendientes, pide el token de la página
   (`GET /{page_id}?fields=name,access_token`) con el del usuario del sistema y sube cada foto con su texto
   (`POST /{page_id}/photos`, multipart: no hace falta URL pública).
3. Errores: hasta 5 intentos o 24 h; después queda en `error` y llega un `AdminAlert` al canal Admin. Si Facebook no
   confirma la publicación (tiempo agotado), se da por publicada y se avisa para revisarla (no se arriesga un
   duplicado). Token inválido o sin permisos: la cola se para y se avisa (como mucho cada 12 h).

### Texto (`domain/text.py`)

- Emojis estándar: 🍄 → 🔥, ✏️ → 📝, ⚠️ → ⏰ (y 💶/💰 → 🏷️/💸 si el post salió sin tarjeta).
- **Se conserva el enlace de compra (🛒)**: en Facebook se puede pulsar.
- La línea de la web pasa a `🌐 Todos los chollos en nuestra web: https://buenchollotech.com/facebook`
  (redirige con `utm_source=facebook`; la analítica lo cuenta como fuente **Facebook**, también el referer
  `facebook.com`).
- Aviso de afiliación (`FACEBOOK_DISCLOSURE`) y hashtags: los de categoría más los fijos (`FACEBOOK_HASHTAGS`).

## Configuración en Meta

Se reutiliza lo de Instagram: porfolio «Buenchollotech», app «BuenCholloTech Publicador» y usuario del sistema
`bct-publicador`.

1. Porfolio → Cuentas → **Páginas** → Añadir → «Añadir una página» → Buenchollo Tech.
2. Usuarios del sistema → `bct-publicador` → **Asignar activos** → la página, con control total (o al menos
   «Contenido»).
3. App «BuenCholloTech Publicador» → Casos de uso → añadir **«Administrar todo en tu página»** (permisos
   `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`).
4. `bct-publicador` → **Generar identificador**: la app, caducidad «Nunca», esos tres permisos. Pegarlo en
   `buenchollo-api/.env` del NAS (no en el chat ni en el repo):

```env
FACEBOOK_ENABLED=true
FACEBOOK_PAGE_ID=61596676873757
FACEBOOK_ACCESS_TOKEN=<token>
FACEBOOK_CHANNELS=main,admin
```

y reiniciar: `docker restart buenchollo-api buenchollo-scheduler`. Comprobar con `GET /v1/facebook/status` (admin):
`page.connected: true` y el nombre de la página.

## Variables

| Variable | Por defecto | Uso |
|---|---|---|
| `FACEBOOK_ENABLED` | `false` | Interruptor general (encolar y publicar) |
| `FACEBOOK_ACCESS_TOKEN` | — | Token del usuario del sistema (`EAA…`) con permisos de página |
| `FACEBOOK_PAGE_ID` | — | Id de la página (`61596676873757`) |
| `FACEBOOK_GRAPH_VERSION` | `v23.0` | Versión de la Graph API |
| `FACEBOOK_CHANNELS` | `main` | Canales de Telegram que cuentan: `main`, `admin` o `main,admin` (en prod, `main,admin`) |
| `FACEBOOK_HASHTAGS` | `chollos ofertas tecnologia` | Hashtags fijos, sin `#` |
| `FACEBOOK_DISCLOSURE` | aviso de afiliado | Línea al pie; vacío = sin aviso |

La tabla `facebook_posts` (migración `20261127120000`, que también añade la fuente `facebook` a la analítica) tiene
RLS sin políticas. El token no se guarda en BD.
