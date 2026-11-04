/** Serializa datos estructurados para un `<script type="application/ld+json">`.
 *
 *  `JSON.stringify` no escapa `<`: un título con `</script><img onerror=…>`
 *  cerraría el bloque y el resto se interpretaría como HTML (XSS almacenado en
 *  la ficha pública; los títulos llegan de usuarios y de Amazon). Escapar `<`,
 *  `>`, `&` y los separadores de línea U+2028/U+2029 como secuencias `\uXXXX`
 *  deja un JSON equivalente que el HTML no puede romper. */
const UNSAFE = new RegExp(`[<>&${String.fromCharCode(0x2028)}${String.fromCharCode(0x2029)}]`, "g");

export function serializeJsonLd(data: unknown): string {
  return JSON.stringify(data).replace(
    UNSAFE,
    (ch) => `\\u${ch.charCodeAt(0).toString(16).padStart(4, "0")}`,
  );
}
