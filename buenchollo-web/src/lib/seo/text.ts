/** Utilidades de texto para títulos y descripciones de buscadores. */

/** Recorta en el último espacio antes de `max` y añade «…». Normaliza espacios
 *  y saltos de línea (las descripciones llegan con Markdown o texto de Amazon). */
export function clampText(text: string, max: number): string {
  const clean = text
    .replace(/[#*_`>]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (clean.length <= max) return clean;
  const cut = clean.slice(0, max - 1);
  const lastSpace = cut.lastIndexOf(" ");
  const base = lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut;
  return `${base.replace(/[\s,.;:–-]+$/, "")}…`;
}

/** Longitud recomendada de la meta description (Google corta hacia 155-160). */
export const DESCRIPTION_MAX = 158;

export function clampDescription(text: string): string {
  return clampText(text, DESCRIPTION_MAX);
}

/** Precio para títulos y textos: «199 €» o «199,99 €» (formato español). */
export function priceText(value: number): string {
  const decimals = Number.isInteger(value) ? 0 : 2;
  return `${value.toLocaleString("es-ES", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: 2,
  })} €`;
}
