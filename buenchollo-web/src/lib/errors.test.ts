/** Tests unitarios de errorMessage().
 *
 *  Convierte un `unknown` capturado en un catch a string legible. Crítico:
 *  toda la UI lo usa para mostrar errores de la API; un fallo aquí filtra
 *  "[object Object]" o cosas peores al usuario.
 */
import { describe, expect, it } from "vitest";
import { errorMessage } from "@/lib/errors";

describe("errorMessage", () => {
  it("extrae el mensaje de una instancia de Error", () => {
    expect(errorMessage(new Error("conexión perdida"))).toBe("conexión perdida");
  });

  it("devuelve un string tal cual cuando lo lanzado es un string", () => {
    expect(errorMessage("fallo manual")).toBe("fallo manual");
  });

  it("usa el fallback por defecto con un valor desconocido", () => {
    expect(errorMessage({ raw: "objeto random" })).toBe("Error inesperado");
  });

  it("usa el fallback personalizado cuando lo damos", () => {
    expect(errorMessage(null, "no se pudo cargar")).toBe("no se pudo cargar");
  });

  it("trata undefined como desconocido y aplica el fallback", () => {
    expect(errorMessage(undefined, "vacío")).toBe("vacío");
  });

  it("subclases de Error también se procesan", () => {
    class CustomError extends Error {}
    expect(errorMessage(new CustomError("custom"))).toBe("custom");
  });
});
