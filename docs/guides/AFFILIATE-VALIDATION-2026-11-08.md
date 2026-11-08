# Validación Awin / Tradedoubler — 2026-11-08

## Estado recuperado
Integración en develop, commit 54320e0. Comentarios del .env legibles en UTF-8 y token Awin configurado. Sin despliegue realizado en esta continuación.

## Comprobaciones reales
- Awin: cuatro consultas de adhesión HTTP 200. Ningún joined; 13 pending, incluidos PcComponentes, Coolmod, Fnac, Samsung y Miravia 37166.
- Link Builder de PcComponentes: HTTP 200, devuelve url y shortUrl (tidd.ly). Que genere un enlace NO prueba aprobación ni atribución de comisiones. La aplicación conserva la comprobación de adhesión.
- Promotions API: HTTP 200 para los seis programas Awin consultados. Ejemplos devueltos: PcComponentes «iPad Mini A20 Pro» (página de categoría), Coolmod «BLACK FRIDAY» (portada), Fnac «Pre Black» (campaña), Samsung «Galaxy Watch Ultra2 LTE por 602,10€» (página de compra). Son textos del proveedor, no precios ni productos verificados independientemente. Miravia 37166 y 37168: sin promociones en la respuesta.
- Promotions no sustituye los feeds de producto; no se importaron esas campañas como fichas completas ni se enviaron publicaciones a Telegram.
- Todas las credenciales configuradas en NAS y copia local. Awin feedList: HTTP 200, 944 feeds, ninguno de las tiendas objetivo. Tradedoubler productFeeds: HTTP 200, cero feeds accesibles. No hay fichas reales autorizadas para validar.

## Corrección y pruebas
El cliente solicita shorten=true y prefiere shortUrl, validando el dominio como antes. Si Awin omite shortUrl conserva el enlace oficial largo: no se garantiza acortamiento en ese caso.
Prueba nueva observada fallar antes de corregir; 81 pruebas de afiliación pasan tras el cambio (clientes, dominio, importación y publicación/sincronización).

## Revisión local
Copia independiente: C:\Users\fadwe\BuenCholloTech-local.
Web: http://localhost:8080 — API: http://localhost:8000/docs.
PostgreSQL local, scheduler y Telegram apagados por el lanzador. Auth y Storage siguen siendo servicios reales según LOCAL-ENV.md.
La copia NAS permanece en la rama develop que dejó la sesión anterior; no se ha cambiado de rama ni reiniciado producción.

## Pendiente y siguientes pasos
1. Obtener la clave de feeds Awin y esperar aprobación de al menos un programa.
2. Comprobar de nuevo los feeds Tradedoubler cuando se apruebe MediaMarkt.
3. Comprobar adhesión, seleccionar feed y permisos reales de imágenes/canales en Admin > Afiliación.
4. Validar una ficha real por tienda: variante, precio, imagen autorizada y enlace; guardar borrador y revisar el mensaje antes de enviar.
5. La programación de estas redes sigue pendiente de validación; la integración anterior documenta una restricción por ASIN. No se declara completo el flujo solicitado de programación/publicación.

Referencia del contrato de enlace: https://help.awin.com/apidocs/generatelink

## Revisi?n previa al despliegue

Correcciones con pruebas de regresi?n que fallaban antes del cambio:
- Awin solicita enlace corto y prefiere shortUrl; mantiene el largo si el proveedor no devuelve uno corto.
- Tradedoubler solicita sourceproducturl=true y priceHistory=true: la comparaci?n exacta por URL y el historial necesitan esos campos opcionales.
- Se conserva shippingCost=0 como env?o gratuito, sin confundirlo con un dato ausente.
- La lista de feeds reconoce lastModifiedTime documentado por Tradedoubler.
- Los feeds deseleccionados o marcados como no disponibles dejan de participar en las b?squedas.
- supports_import=false impide consultar el cat?logo, conservando el flujo de solo enlace.
- Los enlaces de seguimiento requieren HTTPS, host exacto permitido, sin credenciales y puerto est?ndar; se rechazan dominios que solo terminan en tradedoubler.com.
- NaN se trata como precio ausente en lugar de lanzar una excepci?n.
- El test de estado usa credenciales expl?citas de fixture, independiente de las credenciales reales del equipo.

Revisados: detecci?n por dominio/ruta, estados de adhesi?n, selecci?n de variantes, importaci?n y procedencia, sincronizaci?n por generaciones, guarda de publicaci?n y Telegram, formulario y conflictos de reimportaci?n, migraci?n aditiva, configuraci?n Docker y CI.

Limitaciones que siguen abiertas: validaci?n de cada feed real (especialmente formato Google frente a CSV Awin); programaci?n no Amazon (TD-49); acortamiento Tradedoubler no implementado; cuota Awin limitada por proceso, no global entre workers; las condiciones e im?genes deben verificarse por programa. No se promete que la aceptaci?n de un programa baste para publicar autom?ticamente.

Contrato contrastado: https://dev.tradedoubler.com/products/publisher/

- Un CSV con esquema desconocido falla expl?citamente y conserva el cat?logo anterior.

Validaci?n local: 484 Vitest, 37 Playwright, TypeScript, lint (9 avisos existentes) y build SSR correctos. Integraci?n: 59 pruebas correctas sobre base local con esquema ORM de CI; sobre copia Supabase, 57 correctas y dos errores de fixtures preexistentes por FK auth.users.
`pytest -m "not integration"`: 800 correctos tras las correcciones finales; integración: 59 correctos.
