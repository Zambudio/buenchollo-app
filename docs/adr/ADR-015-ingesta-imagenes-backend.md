# ADR-015 — Ingesta de imágenes de usuarios por el backend (Pillow → WebP → Storage)

## Estado

**Aceptado** · 2026-11-04 · decisión tomada al implementar las propuestas de chollos de
usuarios ([spec](../superpowers/specs/2026-11-03-chollos-de-usuarios-design.md)).

## Contexto

Los usuarios pueden adjuntar imágenes a una propuesta: subiéndolas, pegándolas del
portapapeles o indicando una URL externa. Hasta ahora solo el admin publicaba imágenes.
Aceptar imágenes de usuarios abre tres riesgos: ficheros adversarios o inmanejables (bombas
de descompresión, formatos raros, metadatos), SSRF cuando el backend descarga una URL
elegida por el usuario (la API corre en el NAS, dentro de la red doméstica) y hotlinking de
URLs externas arbitrarias en fichas públicas.

## Decisión

El backend es el único que escribe imágenes de propuestas en Storage; el navegador nunca
sube directamente a Supabase.

- **Normalización con Pillow** (`submissions/application/image_processing.py`): se
  decodifica, se aplica la orientación EXIF, se reduce a lado mayor ≤ 1600 px y se
  re-codifica a **WebP** (calidad 82). Límites: 5 MB por imagen, 40 megapíxeles máx.
  (se comprueba antes de decodificar) y 8 imágenes por propuesta. Cualquier excepción del
  parser de Pillow se traduce a 400. La re-codificación descarta metadatos y cargas útiles
  embebidas.
- **Destino**: bucket público `deal-images`, ruta `submissions/{user_id}/{uuid}.webp`. Una
  propuesta solo acepta URLs que empiecen por el prefijo público de ese bucket (allowlist
  con tests contra bypasses con `\`, `../` y userinfo).
- **Importar por URL** (`POST /submissions/images/from-url`) usa un fetcher endurecido
  (`submissions/infrastructure/image_fetcher.py`): solo http(s); comprobación SSRF en
  cada salto (`core/ssrf.py`: privadas, loopback, link-local, multicast, CGNAT
  `100.64.0.0/10` por Tailscale, `192.0.0.0/24`, IPv4 mapeada en IPv6); máx. 3
  redirecciones revalidadas; `Accept-Encoding: identity`; tope de bytes en streaming;
  timeout por petición (10 s) y plazo total de 20 s. El resultado pasa por el mismo
  pipeline Pillow → WebP.
- **Límite de cuerpo antes del parseo**: `BodyLimitMiddleware` (ASGI puro,
  `core/body_limit.py`) corta `POST /v1/submissions/images` por encima de ~5,5 MB (por
  `Content-Length` o contando bytes en chunked), porque Starlette parsea todo el multipart
  antes de ejecutar dependencias o handler. Su 413 incluye cabeceras CORS.
- **Sin conexión de BD retenida**: el endpoint libera la conexión (`rollback`) antes del
  trabajo lento de Pillow y Storage para no agotar el pool (3+2).

## Motivo

Un único punto de control aplica siempre límites y sanitización, con el mismo formato
(WebP ligero) y sin depender del navegador. Re-codificar es la defensa más simple y robusta
frente a ficheros adversarios, y el bucket propio elimina el hotlinking y el contenido que
cambia después de la moderación.

## Alternativas consideradas

- **Subida directa del navegador a Storage con políticas RLS**: menos carga en la API, pero
  sin validación de contenido ni límite de píxeles, y deja el bucket expuesto a abuso.
- **Guardar la URL externa sin descargarla**: sin SSRF, pero con hotlinking, imágenes que
  desaparecen o cambian tras aprobar y tracking al lector.
- **Procesar en un worker/cola aparte**: innecesario para el volumen actual; añade
  infraestructura. Se mantiene síncrono con límites estrictos.
- **Validar solo `Content-Type`/extensión**: trivialmente falsificable.

## Consecuencias

- Dependencia nueva `Pillow==13.0.0`: el NAS necesita **rebuild** de la imagen. `limits`
  queda fijado en `requirements.txt` porque `rate_limit.py` lo importa directamente.
- Límite conocido: la comprobación SSRF resuelve el DNS y luego `httpx` vuelve a resolverlo
  (ventana de DNS rebinding) — TD-25.
- Las imágenes subidas y nunca enviadas en una propuesta quedan huérfanas en
  `deal-images/submissions/`; no hay limpieza automática — TD-24.
- El endpoint de imágenes consume CPU del NAS; se acota con rate limit por usuario (30/min)
  y límite de cuerpo.
- Detalle operativo en [`07-security.md`](../project/07-security.md).
