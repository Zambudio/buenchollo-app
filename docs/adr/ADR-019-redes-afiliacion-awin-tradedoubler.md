# ADR-019 — Redes de afiliación (Awin y Tradedoubler) en el editor de chollos

## Estado

Aceptado · 2026-11-08. En producción desde PR #78; pendiente de validación en vivo hasta que alguna tienda apruebe la solicitud (ver `docs/guides/AFFILIATE-ACTIVATION-RUNBOOK.md`).

## Contexto

Además de Amazon queremos publicar chollos de tiendas que trabajan con Awin
(PcComponentes, Coolmod, Fnac, Samsung, Miravia) y Tradedoubler (MediaMarkt). En Awin
los enlaces (Publisher API, Link Builder) y los datos de producto (feeds descargables con
una clave distinta) son integraciones separadas; ninguna API recibe una URL arbitraria y
devuelve su ficha. Tradedoubler ofrece una Products API consultable por feed e
identificadores, sin búsqueda por URL. Los programas pueden no estar aprobados y cada uno
impone condiciones (imágenes, canales, avisos).

## Decisión

- Ampliar el módulo `affiliates` del monolito (ADR-001) con dominio, aplicación,
  infraestructura y API, sin servicios ni colas nuevas ni dependencias nuevas (httpx y
  stdlib).
- **Registro de programas** (`affiliate_programs`) separado de `stores`: una tienda puede
  tener varios programas; se guarda red, ID, dominios, adhesión con fecha y fuente,
  espacios, feeds, restricciones, aviso y política de caducidad. Los IDs iniciales se
  siembran deshabilitados y sin verificar.
- **Catálogo local de feeds Awin** (`affiliate_feed_products`) escrito por generaciones;
  la generación activa vive en el JSON del feed del programa. Sincronización acotada en el
  scheduler existente / panel / CLI, nunca en la petición del editor.
- **Tradedoubler** se consulta en el momento (no se descarga el catálogo).
- Modelo común `ImportedOffer` (proveedor, tienda, producto, oferta, procedencia); lo
  ausente queda ausente.
- Procedencia y evidencia de precio en `deals` (`affiliate_program_id`, `data_source`,
  fechas, `price_reference_type/evidence`, `import_snapshot`). `PublicationGuard` aplica
  las reglas en `DealService` y en `/telegram/notify`; los borradores siempre se guardan.
  Los chollos de Amazon no pasan por la guarda.
- Seguridad: allowlist de hosts por integración con validación de cada redirección,
  timeouts, topes de descarga/descompresión/filas, límite de 20 llamadas/min a Awin,
  redacción de secretos, texto externo convertido a texto plano y tratado como dato (sin
  IA en esta versión).

## Alternativas descartadas

- Scraping de la tienda o de Amazon para completar datos: prohibido por las condiciones y
  frágil. Lo que falta lo aporta una persona con evidencia.
- Construir deeplinks concatenando parámetros: solo con confirmación expresa del propietario
  (Tradedoubler) y nunca como sustituto de un fallo.
- Ampliar `stores` con las columnas de afiliación: mezcla datos públicos con configuración
  de cuenta y no admite varios programas por tienda.

## Consecuencias

- Hasta tener credenciales y programas aprobados solo hay validación con fixtures.
- El formato real de columnas del feed Awin y de la respuesta de Tradedoubler debe
  contrastarse en la primera prueba en vivo (los parsers aceptan las variantes conocidas).
- La programación de publicaciones (`scheduled_deals`) sigue exigiendo ASIN: los chollos de
  redes se publican a mano tras revisar.
- La migración `20261108120000` es aditiva; el downgrade elimina el registro, el catálogo
  local y la procedencia de los chollos.
