# Instagram: publicación automática en el feed

> Decisión: [ADR-022](../adr/ADR-022-publicacion-instagram.md). Código: `buenchollo-api/app/modules/instagram/`.

Cada chollo que sale en los canales de Telegram de `INSTAGRAM_CHANNELS` (desde el panel o programado) se publica
también en el **feed de Instagram**: la misma imagen (tarjeta de oferta 1200 × 800, que encaja en el feed) y el texto adaptado.
Hoy `INSTAGRAM_CHANNELS=main,admin`: las publicaciones programadas salen en el canal Admin («BuenChollo Admin») y
de ahí pasan al público, así que cuentan los dos. Nunca van a Instagram la versión WhatsApp, las republicaciones por
bajada de precio ni el resumen semanal (no pasan por la cola).

## Cómo funciona

1. Al publicar en Telegram, la API deja el post en la tabla `instagram_posts` (texto adaptado y JPEG). Nunca
   bloquea ni hace fallar la publicación de Telegram.
2. El job `publish_instagram_queue` del contenedor scheduler (cada 2 min) lo publica con la API oficial:
   crea el contenedor con la URL pública de la imagen
   (`https://api.buenchollotech.com/v1/instagram/media/{id}.jpg`, que Instagram descarga), espera a que esté
   `FINISHED` y lo publica.
3. Errores: se reintenta hasta 5 veces o 24 h; después queda en `error` y se avisa al canal Admin de Telegram. Si
   Instagram no confirma la publicación (tiempo agotado), se da por publicada y se avisa para revisar el feed (no se
   arriesga un duplicado).
4. La imagen solo se sirve mientras el post está pendiente y como mucho 48 h (id aleatorio, `no-store`, `noindex`).

### Texto

A partir del texto que salió de verdad en Telegram (`domain/caption.py`):

- Emojis estándar: 🍄 → 🔥, ✏️ → 📝, ⚠️ → ⏰ (y 💶/💰 → 🏷️/💸 si el post salió sin tarjeta).
- Sin enlaces (en Instagram no se pueden pulsar): fuera la línea 🛒, la de la web y cualquier URL.
- Al final, «🔗 Enlace al chollo en nuestra bio» y los hashtags: los de categoría del post más los fijos
  (`INSTAGRAM_HASHTAGS`), sin repetir y como mucho 30. Límite de 2.200 caracteres.

### Bio y medición

El enlace de la bio es **`https://buenchollotech.com/instagram`**: redirige a la portada con
`utm_source=instagram&utm_medium=social&utm_campaign=bio` y la analítica lo cuenta como fuente **Instagram**
(también las visitas con referer `instagram.com`). Migración `20261124120000`.

## Configuración (hecha el 2026-11-24)

Meta ya no ofrece la «configuración de la API con inicio de sesión de Instagram» a las apps nuevas: obliga al
**inicio de sesión unificado**, que exige un porfolio empresarial. Lo que hay montado:

- **App de Meta** «BuenCholloTech Publicador» (id `1600101988548764`, modo desarrollo), caso de uso «Administrar
  mensajes y contenido en Instagram», con `instagram_business_basic` e `instagram_business_content_publish`.
- **Porfolio empresarial** «Buenchollotech» (id `2027078151294511`, sin verificar: no hace falta para publicar en
  nuestra cuenta) con la app y la cuenta de Instagram **@buenchollotech** (id `17841480234900028`), que además es
  evaluadora de la app.
- **Usuario del sistema** `bct-publicador` del porfolio, con acceso a la app y acceso total a la cuenta de
  Instagram. Su token (`EAA…`, caducidad «Nunca», permisos `instagram_basic` e `instagram_content_publish`) es el
  de `INSTAGRAM_ACCESS_TOKEN`.

Con un token `EAA…` el cliente usa `graph.facebook.com` (misma API de publicación) y no lo renueva; con uno de
Instagram (`IG…`) usa `graph.instagram.com` y lo renueva cada semana.

### Regenerar el token

Meta Business Suite → Configuración del porfolio «Buenchollotech» → Usuarios del sistema → `bct-publicador` →
**Generar identificador**: app «BuenCholloTech Publicador», caducidad «Nunca», permisos `instagram_basic` e
`instagram_content_publish`. Pegarlo en `buenchollo-api/.env` del NAS (lo edita el administrador; el token no se
pega en el chat ni en el repo):

```env
INSTAGRAM_ENABLED=true
INSTAGRAM_USER_ID=17841480234900028
INSTAGRAM_ACCESS_TOKEN=<token>
```

y reiniciar: `docker restart buenchollo-api buenchollo-scheduler`. Comprobar con `GET /v1/instagram/status` (admin):
`connected: true` y el usuario de la cuenta a los 2 min.

### Token

El del `.env` solo **siembra** la tabla `instagram_account`; si se cambia en el `.env`, se detecta (hash) y se usa
el nuevo. Si deja de valer (revocado, permisos retirados), la cola se para y llega un aviso al canal Admin (como
mucho cada 12 h): regenerarlo como arriba.

Las tablas `instagram_posts` e `instagram_account` tienen RLS activado sin políticas: el token nunca es legible por
PostgREST.

## Variables

| Variable | Por defecto | Uso |
|---|---|---|
| `INSTAGRAM_ENABLED` | `false` | Interruptor general (encolar y publicar) |
| `INSTAGRAM_ACCESS_TOKEN` | — | Token del usuario del sistema (`EAA…`) o de Instagram (`IG…`); solo siembra la BD |
| `INSTAGRAM_USER_ID` | — | Id de la cuenta profesional (`17841480234900028`); obligatorio con token `EAA…` |
| `INSTAGRAM_CHANNELS` | `main` | Canales de Telegram cuyos chollos van a Instagram: `main`, `admin` o `main,admin` (en prod, `main,admin`) |
| `INSTAGRAM_GRAPH_VERSION` | `v23.0` | Versión de la Graph API |
| `INSTAGRAM_HASHTAGS` | `chollos ofertas tecnologia chollostecnologicos buenchollotech` | Hashtags fijos, sin `#` (en un `.env` empieza un comentario) |
| `PUBLIC_API_URL` | `https://api.buenchollotech.com` | Base de la URL de la imagen que descarga Instagram |

## Límites y avisos

- Instagram permite **100 publicaciones por API cada 24 h** (algunas páginas de Meta aún dicen 50); publicamos ~10.
- Solo JPEG y proporciones entre 4:5 y 1,91:1: la tarjeta es 3:2. Si un post sale en Telegram con la foto original,
  se encaja en un lienzo blanco 1200 × 800.
- Si Cloudflare bloqueara la descarga de la imagen por parte de Meta (`facebookexternalhit`), el contenedor fallaría
  con «Media download failed»: permitir ese agente o la ruta `/v1/instagram/media/` en las reglas de bots.
- Historias (p. ej. el resumen semanal) quedan para más adelante: necesitan formato 9:16.
