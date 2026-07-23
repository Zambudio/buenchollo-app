import { describe, expect, it } from "vitest";
import { slugify } from "./slugify";

describe("slugify", () => {
  it("normaliza acentos, mayúsculas y espacios", () => {
    expect(slugify("Los 10 Mejores Cascos Bluetooth")).toBe("los-10-mejores-cascos-bluetooth");
    expect(slugify("Ñoño & Cía: análisis")).toBe("nono-cia-analisis");
  });

  it("es estable (mismo input, mismo output)", () => {
    expect(slugify("Guía de compra")).toBe(slugify("Guía de compra"));
  });
});
