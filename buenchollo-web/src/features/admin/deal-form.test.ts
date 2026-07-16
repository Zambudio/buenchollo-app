import { describe, expect, it } from "vitest";
import { buildDealPayload, dealToForm, emptyForm } from "./deal-form";
import type { DealDetailData } from "@/services/api/deals";

function formWith(overrides: Partial<ReturnType<typeof emptyForm>>) {
  return { ...emptyForm(), ...overrides };
}

const baseDeal = {
  id: "d1",
  slug: "mi-chollo",
  title: "Mi chollo",
  current_price: 99.99,
  previous_price: 149.99,
  status: "active",
} as DealDetailData;

describe("emptyForm", () => {
  it("arranca activo, sin imágenes y sin keepa", () => {
    const f = emptyForm();
    expect(f.status).toBe("active");
    expect(f.images).toEqual([]);
    expect(f.show_keepa_chart).toBe(false);
  });
});

describe("dealToForm", () => {
  it("convierte precios a string y nulls a cadena vacía", () => {
    const f = dealToForm(baseDeal);
    expect(f.current_price).toBe("99.99");
    expect(f.previous_price).toBe("149.99");
    expect(f.brand).toBe("");
    expect(f.store_id).toBe("");
  });
});

describe("buildDealPayload", () => {
  it("genera slug único al crear y conserva el slug al editar", () => {
    const form = formWith({ title: "Ratón Gaming Pro", current_price: "10" });
    const created = buildDealPayload(form, null);
    expect(created.slug).toMatch(/^raton-gaming-pro-/);
    const edited = buildDealPayload(form, baseDeal);
    expect(edited.slug).toBe("mi-chollo");
  });

  it("calcula el descuento y promociona image_url a principal", () => {
    const form = formWith({
      title: "X",
      current_price: "50",
      previous_price: "100",
      image_url: "https://img/main.jpg",
      images: ["https://img/otra.jpg"],
    });
    const p = buildDealPayload(form, null);
    expect(p.discount_percentage).toBe(50);
    expect(p.image_url).toBe("https://img/main.jpg");
    expect(p.images).toEqual(["https://img/main.jpg", "https://img/otra.jpg"]);
  });

  it("solo fija published_at al CREAR en estado active", () => {
    const form = formWith({ title: "X", current_price: "10", status: "active" });
    expect(buildDealPayload(form, null).published_at).toBeDefined();
    expect(buildDealPayload(form, baseDeal).published_at).toBeUndefined();
    const draft = formWith({ title: "X", current_price: "10", status: "draft" });
    expect(buildDealPayload(draft, null).published_at).toBeUndefined();
  });

  it("solo envía scheduled_for cuando el estado es scheduled", () => {
    const scheduled = formWith({
      title: "X",
      current_price: "10",
      status: "scheduled",
      scheduled_for: "2026-08-01T10:00",
    });
    expect(buildDealPayload(scheduled, null).scheduled_for).toBe(
      new Date("2026-08-01T10:00").toISOString(),
    );
    const active = formWith({
      title: "X",
      current_price: "10",
      status: "active",
      scheduled_for: "2026-08-01T10:00",
    });
    expect(buildDealPayload(active, null).scheduled_for).toBeNull();
  });

  it("trunca título a 200 y descripción corta a 300", () => {
    const form = formWith({
      title: "t".repeat(250),
      short_description: "s".repeat(400),
      current_price: "10",
    });
    const p = buildDealPayload(form, null);
    expect(p.title).toHaveLength(200);
    expect(p.short_description).toHaveLength(300);
  });
});
