import { describe, expect, it } from "vitest";
import { describeChange, summarizeTransitions } from "./price-check";

describe("describeChange", () => {
  it("combina la transición y el motivo", () => {
    expect(describeChange("offer_ended", "price_increase")).toBe(
      "Oferta terminada · Subió de precio",
    );
    expect(describeChange("offer_ended", "not_found")).toBe(
      "Oferta terminada · Ya no está en la tienda",
    );
    expect(describeChange("reactivated", "deal_again")).toBe(
      "Reactivada · Vuelve a estar en oferta",
    );
    expect(describeChange("purged", "product_purged")).toBe("Eliminada · Producto sin tiendas");
    expect(describeChange("purged", "listing_purged")).toBe(
      "Eliminada · Tienda retirada del producto",
    );
  });

  it("tolera valores desconocidos", () => {
    expect(describeChange("otra", "rara")).toBe("otra · rara");
  });
});

describe("summarizeTransitions", () => {
  it("cuenta cada tipo de cambio y omite los que no hay", () => {
    expect(
      summarizeTransitions([
        { transition: "offer_ended" },
        { transition: "offer_ended" },
        { transition: "reactivated" },
      ]),
    ).toBe("2 ofertas terminadas · 1 reactivada");
    expect(summarizeTransitions([{ transition: "purged" }])).toBe("1 eliminada");
    expect(summarizeTransitions([])).toBe("Sin cambios");
  });
});
