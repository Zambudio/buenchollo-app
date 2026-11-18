import { describe, expect, it } from "vitest";
import type { DealDetailData } from "@/services/api/deals";
import { dealPageSeo, dealPath, isOfferLive } from "./deal";

/** Nodo JSON-LD como objeto plano para inspeccionarlo en los asserts. */
const plain = (value: unknown) => JSON.parse(JSON.stringify(value));

const NOW = new Date("2026-11-18T12:00:00Z");

function deal(overrides: Partial<DealDetailData> = {}): DealDetailData {
  return {
    id: "d1",
    title: "Auriculares Sony WH-1000XM5 con cancelación de ruido y 30 horas de batería",
    slug: "sony-wh1000xm5",
    image_url: "https://img/sony.webp",
    images: [],
    current_price: 279.99,
    previous_price: 419,
    discount_percentage: 33,
    temperature: 10,
    published_at: "2026-11-10T10:00:00Z",
    status: "active",
    expires_at: "2026-12-01T00:00:00Z",
    description: "Descripción larga",
    short_description: "Cancelación de ruido líder",
    affiliate_url: null,
    shipping_info: null,
    comment_count: 0,
    favorite_count: 0,
    votes_up: 0,
    votes_down: 0,
    click_count: 0,
    store: { id: "s", name: "Amazon", slug: "amazon" },
    category: { name: "Audio", slug: "audio" },
    subcategory: { name: "Auriculares", slug: "auriculares" },
    brand: "Sony",
    external_id: "B09XS7JWHH",
    ...overrides,
  };
}

function graphTypes(seo: ReturnType<typeof dealPageSeo>) {
  return (seo.jsonLd ?? []).map((node) => (node as { "@type": string })["@type"]);
}

describe("dealPageSeo", () => {
  it("oferta activa: título con chollo, precio y descuento, y Product con Offer", () => {
    const seo = dealPageSeo(deal(), NOW);
    expect(seo.title).toMatch(
      /^Chollo Auriculares Sony .+ por 279,99 € \(-33 %\) \| BuenChollo Tech$/,
    );
    expect(seo.description).toContain("antes 419 €, -33 %");
    expect(seo.description).toContain("en Amazon");
    expect(seo.type).toBe("product");
    expect(seo.noindex).toBeUndefined();
    expect(graphTypes(seo)).toEqual(["Product", "BreadcrumbList"]);
    const product = plain(seo.jsonLd![0]);
    expect(product.brand).toEqual({ "@type": "Brand", name: "Sony" });
    expect(product.category).toBe("Auriculares");
    expect(product.offers.priceValidUntil).toBe("2026-12-01");
    expect(product.offers.availability).toBe("https://schema.org/InStock");
    expect(product.offers.seller).toEqual({ "@type": "Organization", name: "Amazon" });
    const crumbs = plain(seo.jsonLd![1]).itemListElement;
    expect(crumbs.map((c: { name: string }) => c.name)).toEqual([
      "Inicio",
      "Audio",
      "Auriculares",
      deal().title,
    ]);
  });

  it("sin descuento, tienda ni categoría y con fecha de fin pasada", () => {
    const seo = dealPageSeo(
      deal({
        discount_percentage: null,
        previous_price: null,
        store: null,
        category: null,
        subcategory: null,
        brand: null,
        short_description: null,
        external_id: null,
        images: ["https://img/1.webp", "https://img/2.webp"],
        expires_at: "2026-11-01T00:00:00Z",
        published_at: "",
      }),
      NOW,
    );
    expect(seo.title).not.toContain("%");
    expect(seo.description).not.toContain("antes");
    const product = plain(seo.jsonLd![0]);
    expect(product.offers.priceValidUntil).toBeUndefined();
    expect(product.offers.seller).toBeUndefined();
    expect(product.sku).toBe("d1");
    expect(product.image).toEqual(["https://img/1.webp", "https://img/2.webp"]);
    expect(
      seo.extraMeta?.some((tag) => "property" in tag && tag.property === "article:published_time"),
    ).toBe(false);
  });

  it("calcula el descuento si la API no lo trae", () => {
    expect(dealPageSeo(deal({ discount_percentage: null }), NOW).title).toContain("(-33 %)");
  });

  it("oferta terminada: sin precio en el título ni Product en el JSON-LD", () => {
    const seo = dealPageSeo(deal({ status: "expired", offer_end_reason: "out_of_stock" }), NOW);
    expect(seo.title).toMatch(/oferta terminada \| BuenChollo Tech$/);
    expect(seo.title).not.toContain("€");
    expect(seo.description).toContain("ha terminado");
    expect(graphTypes(seo)).toEqual(["BreadcrumbList"]);
  });

  it("borradores y programados quedan fuera del índice", () => {
    expect(dealPageSeo(deal({ status: "draft" }), NOW).noindex).toBe(true);
    expect(dealPageSeo(deal({ status: "scheduled", image_url: null }), NOW)).toMatchObject({
      noindex: true,
      image: undefined,
    });
  });

  it("usa la fecha actual si no se indica", () => {
    expect(dealPageSeo(deal()).title).toContain("Chollo");
  });

  it("helpers", () => {
    expect(dealPath("x")).toBe("/chollo/x");
    expect(isOfferLive({ status: "active" })).toBe(true);
    expect(isOfferLive({ status: "expired" })).toBe(false);
  });
});
