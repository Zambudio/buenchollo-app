/** Tests del schema Zod del formulario de alertas. */
import { describe, expect, it } from "vitest";
import { alertFormSchema } from "@/lib/validation/alerts";

describe("alertFormSchema", () => {
  it("acepta una alerta sólo con keyword", () => {
    const result = alertFormSchema.safeParse({
      keyword: "monitor 27",
      category_id: "",
      store_id: "",
      brand: "",
      max_price: "",
      min_discount: "",
    });
    expect(result.success).toBe(true);
  });

  it("acepta sólo max_price como criterio", () => {
    const result = alertFormSchema.safeParse({
      keyword: "",
      category_id: "",
      store_id: "",
      brand: "",
      max_price: "250",
      min_discount: "",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.max_price).toBe(250);
    }
  });

  it("rechaza la alerta cuando no se pone ningún criterio", () => {
    const result = alertFormSchema.safeParse({
      keyword: "",
      category_id: "",
      store_id: "",
      brand: "",
      max_price: "",
      min_discount: "",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.message).toBe(
        "Escribe un producto o elige al menos un criterio",
      );
    }
  });

  it("max_price negativo falla", () => {
    const result = alertFormSchema.safeParse({
      keyword: "x",
      category_id: "",
      store_id: "",
      brand: "",
      max_price: "-5",
      min_discount: "",
    });
    expect(result.success).toBe(false);
  });

  it("min_discount fuera del rango 1-100 falla", () => {
    const fueraBajo = alertFormSchema.safeParse({
      keyword: "x",
      category_id: "",
      store_id: "",
      brand: "",
      max_price: "",
      min_discount: "0",
    });
    expect(fueraBajo.success).toBe(false);

    const fueraAlto = alertFormSchema.safeParse({
      keyword: "x",
      category_id: "",
      store_id: "",
      brand: "",
      max_price: "",
      min_discount: "150",
    });
    expect(fueraAlto.success).toBe(false);
  });

  it("min_discount válido (entre 1 y 100) se acepta", () => {
    const result = alertFormSchema.safeParse({
      keyword: "",
      category_id: "",
      store_id: "",
      brand: "",
      max_price: "",
      min_discount: "30",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.min_discount).toBe(30);
    }
  });

  it("strings vacíos se normalizan a null en la salida", () => {
    const result = alertFormSchema.safeParse({
      keyword: "test",
      category_id: "",
      store_id: "   ",
      brand: undefined,
      max_price: "",
      min_discount: "",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.category_id).toBeNull();
      expect(result.data.store_id).toBeNull();
      expect(result.data.brand).toBeNull();
    }
  });
});
