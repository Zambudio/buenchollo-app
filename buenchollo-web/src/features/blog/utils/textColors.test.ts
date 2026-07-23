import { describe, expect, it } from "vitest";
import { ALLOWED_TEXT_COLORS, nearestAllowedColor } from "./textColors";

describe("nearestAllowedColor", () => {
  it("devuelve el mismo color si ya está en la paleta", () => {
    expect(nearestAllowedColor("#22d3ee")).toBe("#22d3ee");
  });

  it("ajusta un color rgb() (formato que devuelve el DOM) al más cercano de la paleta", () => {
    expect(nearestAllowedColor("rgb(255, 0, 0)")).toBe("#f87171");
  });

  it("ajusta un hexadecimal arbitrario (p. ej. pegado desde un chat de IA) a uno de la paleta", () => {
    const allowedValues = new Set<string>(ALLOWED_TEXT_COLORS.map((c) => c.value));
    expect(allowedValues.has(nearestAllowedColor("#0000ff") as string)).toBe(true);
  });

  it("devuelve null si no es un color reconocible", () => {
    expect(nearestAllowedColor("not-a-color")).toBeNull();
    expect(nearestAllowedColor(null)).toBeNull();
    expect(nearestAllowedColor(undefined)).toBeNull();
  });

  it("el resultado siempre pertenece a la paleta permitida", () => {
    const allowedValues = new Set<string>(ALLOWED_TEXT_COLORS.map((c) => c.value));
    for (const probe of ["#123456", "rgb(10, 200, 30)", "#ffffff", "#000000"]) {
      expect(allowedValues.has(nearestAllowedColor(probe) as string)).toBe(true);
    }
  });
});
