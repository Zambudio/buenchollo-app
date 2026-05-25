/** Convierte cualquier valor capturado en un catch a un mensaje legible.
 *  Centraliza el manejo: en TypeScript moderno los catch son `unknown`, y
 *  hacer `e.message` revienta si lo lanzado no es un Error. */
export function errorMessage(e: unknown, fallback = "Error inesperado"): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  return fallback;
}
