/** Paleta controlada de color de texto, compartida por la barra de
 * herramientas del editor y por el filtro de pegado (paste). Debe coincidir
 * exactamente con `ALLOWED_TEXT_COLORS` del backend
 * (`app/modules/blog/domain/content.py`) — si un color no está aquí, el
 * backend rechaza el artículo al guardar/publicar. */
export const ALLOWED_TEXT_COLORS = [
  { value: "#22d3ee", label: "Cian" },
  { value: "#f87171", label: "Rojo" },
  { value: "#4ade80", label: "Verde" },
  { value: "#facc15", label: "Amarillo" },
  { value: "#a78bfa", label: "Violeta" },
  { value: "#f8fafc", label: "Blanco" },
  { value: "#94a3b8", label: "Gris" },
] as const;

function hexToRgb(hex: string): [number, number, number] | null {
  const match = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  const group = match?.[1];
  if (!group) return null;
  const n = parseInt(group, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function parseAnyColor(input: string): [number, number, number] | null {
  const trimmed = input.trim().toLowerCase();
  const rgbMatch = /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/.exec(trimmed);
  if (rgbMatch?.[1] && rgbMatch[2] && rgbMatch[3]) {
    return [Number(rgbMatch[1]), Number(rgbMatch[2]), Number(rgbMatch[3])];
  }
  return hexToRgb(trimmed);
}

/** Pegar contenido (p. ej. desde un chat de IA) puede traer cualquier color
 * inline. En vez de descartarlo (perdiendo la intención del formato) o
 * aceptarlo tal cual (rompiendo la validación del backend al guardar), lo
 * ajustamos al color permitido más cercano. Devuelve `null` si el string de
 * entrada no es un color reconocible. */
export function nearestAllowedColor(input: string | null | undefined): string | null {
  if (!input) return null;
  const rgb = parseAnyColor(input);
  if (!rgb) return null;

  let closest: string = ALLOWED_TEXT_COLORS[0].value;
  let bestDistance = Infinity;
  for (const { value } of ALLOWED_TEXT_COLORS) {
    const candidate = hexToRgb(value);
    if (!candidate) continue;
    const distance =
      (rgb[0] - candidate[0]) ** 2 + (rgb[1] - candidate[1]) ** 2 + (rgb[2] - candidate[2]) ** 2;
    if (distance < bestDistance) {
      bestDistance = distance;
      closest = value;
    }
  }
  return closest;
}
