import { describe, expect, it } from "vitest";
import { isInStock } from "./offer-status";

describe("isInStock", () => {
  it("una oferta activa está en stock", () => {
    expect(isInStock({ status: "active", offer_end_reason: null })).toBe(true);
  });

  it("sin oferta por precio sigue a la venta", () => {
    expect(isInStock({ status: "expired", offer_end_reason: "price_increase" })).toBe(true);
    expect(isInStock({ status: "expired", offer_end_reason: "no_longer_deal" })).toBe(true);
  });

  it("agotado, retirado o caducado por fecha no se anuncia en stock", () => {
    expect(isInStock({ status: "expired", offer_end_reason: "out_of_stock" })).toBe(false);
    expect(isInStock({ status: "expired", offer_end_reason: "not_found" })).toBe(false);
    expect(isInStock({ status: "expired", offer_end_reason: "expired_date" })).toBe(false);
    expect(isInStock({ status: "expired" })).toBe(false);
  });
});
