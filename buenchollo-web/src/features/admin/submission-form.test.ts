import { describe, expect, it } from "vitest";
import { toDatetimeLocal } from "@/lib/format";
import type { AdminSubmission } from "@/services/api/submissions";
import {
  buildRejectReason,
  extractAsin,
  submissionToDealForm,
  submissionWarningLabels,
} from "./submission-form";

const NOW = new Date("2026-11-04T10:00:00Z");

function submission(over: Partial<AdminSubmission> = {}): AdminSubmission {
  return {
    id: "sub-1",
    status: "pending",
    title: "Monitor 27 pulgadas",
    description: "Panel IPS 144 Hz",
    original_url: "https://www.amazon.es/dp/B0ABCDEF12?tag=otro-21",
    affiliate_url: "https://www.amazon.es/dp/B0ABCDEF12?tag=buenchollo-21",
    asin: null,
    current_price: 149.9,
    previous_price: 199,
    coupon_code: "MONI10",
    shipping_info: "Envío gratis",
    store_id: "store-amazon",
    store_name: "Amazon",
    category_id: "cat-1",
    subcategory_id: "sub-cat-1",
    starts_at: null,
    expires_at: "2026-11-20T22:59:00Z",
    image_url: "https://img.test/b.webp",
    images: ["https://img.test/a.webp", "https://img.test/b.webp"],
    warnings: [],
    rejection_reason: null,
    deal_slug: null,
    created_at: "2026-11-03T08:00:00Z",
    author: { username: "pepe", display_name: "Pepe", avatar_url: null },
    previously_published: false,
    ...over,
  };
}

describe("extractAsin", () => {
  it("extrae el ASIN de /dp/ y /gp/product/", () => {
    expect(extractAsin("https://www.amazon.es/dp/B0ABCDEF12?tag=x")).toBe("B0ABCDEF12");
    expect(extractAsin("https://www.amazon.es/Monitor/dp/b0abcdef12/ref=sr")).toBe("B0ABCDEF12");
    expect(extractAsin("https://www.amazon.es/gp/product/B0ABCDEF12")).toBe("B0ABCDEF12");
  });

  it("devuelve cadena vacía si no es un enlace de producto de Amazon", () => {
    expect(extractAsin("https://www.pccomponentes.com/dp/B0ABCDEF12")).toBe("");
    expect(extractAsin("https://www.amazon.es/s?k=monitor")).toBe("");
    expect(extractAsin("no es url")).toBe("");
  });
});

describe("submissionToDealForm", () => {
  it("mapea textos, precios, enlace, tienda, cupón y envío", () => {
    const f = submissionToDealForm(submission(), NOW);
    expect(f.title).toBe("Monitor 27 pulgadas");
    expect(f.description).toBe("Panel IPS 144 Hz");
    expect(f.short_description).toBe("");
    expect(f.brand).toBe("");
    expect(f.current_price).toBe("149.9");
    expect(f.previous_price).toBe("199");
    expect(f.affiliate_url).toBe("https://www.amazon.es/dp/B0ABCDEF12?tag=buenchollo-21");
    expect(f.store_id).toBe("store-amazon");
    expect(f.coupon_code).toBe("MONI10");
    expect(f.shipping_info).toBe("Envío gratis");
  });

  it("usa el ASIN del enlace como external_id y activa Keepa", () => {
    const f = submissionToDealForm(submission(), NOW);
    expect(f.external_id).toBe("B0ABCDEF12");
    expect(f.show_keepa_chart).toBe(true);
  });

  it("prefiere el campo asin si la API lo envía", () => {
    const f = submissionToDealForm(
      { ...submission({ affiliate_url: "https://amzn.eu/d/xyz" }), asin: "B0ZZZZZZZZ" },
      NOW,
    );
    expect(f.external_id).toBe("B0ZZZZZZZZ");
  });

  it("sin ASIN deja external_id vacío y Keepa desactivado", () => {
    const f = submissionToDealForm(
      submission({
        original_url: "https://www.pccomponentes.com/monitor",
        affiliate_url: "https://www.pccomponentes.com/monitor",
      }),
      NOW,
    );
    expect(f.external_id).toBe("");
    expect(f.show_keepa_chart).toBe(false);
  });

  it("pone la imagen principal primero y la conserva en image_url", () => {
    const f = submissionToDealForm(submission(), NOW);
    expect(f.images).toEqual(["https://img.test/b.webp", "https://img.test/a.webp"]);
    expect(f.image_url).toBe("https://img.test/b.webp");
  });

  it("añade la imagen principal si no estaba en la lista", () => {
    const f = submissionToDealForm(
      submission({ image_url: "https://img.test/c.webp", images: ["https://img.test/a.webp"] }),
      NOW,
    );
    expect(f.images).toEqual(["https://img.test/c.webp", "https://img.test/a.webp"]);
  });

  it("sin imágenes deja la lista y la principal vacías", () => {
    const f = submissionToDealForm(submission({ image_url: null, images: [] }), NOW);
    expect(f.images).toEqual([]);
    expect(f.image_url).toBe("");
  });

  it("mapea categoría y subcategoría", () => {
    const f = submissionToDealForm(submission(), NOW);
    expect(f.category_id).toBe("cat-1");
    expect(f.subcategory_id).toBe("sub-cat-1");
  });

  it("convierte valores nulos en cadenas vacías", () => {
    const f = submissionToDealForm(
      submission({
        description: null,
        previous_price: null,
        coupon_code: null,
        shipping_info: null,
        store_id: null,
        category_id: null,
        subcategory_id: null,
        expires_at: null,
      }),
      NOW,
    );
    expect(f.description).toBe("");
    expect(f.previous_price).toBe("");
    expect(f.coupon_code).toBe("");
    expect(f.shipping_info).toBe("");
    expect(f.store_id).toBe("");
    expect(f.category_id).toBe("");
    expect(f.subcategory_id).toBe("");
    expect(f.expires_at).toBe("");
  });

  it("convierte expires_at a datetime-local", () => {
    const f = submissionToDealForm(submission(), NOW);
    expect(f.expires_at).toBe(toDatetimeLocal("2026-11-20T22:59:00Z"));
  });

  it("sin starts_at queda activo y sin programar", () => {
    const f = submissionToDealForm(submission(), NOW);
    expect(f.status).toBe("active");
    expect(f.scheduled_for).toBe("");
  });

  it("starts_at futura → programado con scheduled_for", () => {
    const f = submissionToDealForm(submission({ starts_at: "2026-11-10T08:00:00Z" }), NOW);
    expect(f.status).toBe("scheduled");
    expect(f.scheduled_for).toBe(toDatetimeLocal("2026-11-10T08:00:00Z"));
  });

  it("starts_at pasada → activo (se publica ya)", () => {
    const f = submissionToDealForm(submission({ starts_at: "2026-11-01T08:00:00Z" }), NOW);
    expect(f.status).toBe("active");
    expect(f.scheduled_for).toBe(toDatetimeLocal("2026-11-01T08:00:00Z"));
  });
});

describe("submissionWarningLabels", () => {
  it("traduce los avisos conocidos", () => {
    expect(
      submissionWarningLabels(
        submission({
          warnings: [
            "amazon_foreign_marketplace",
            "third_party_affiliate_removed",
            "not_affiliable",
          ],
        }),
      ),
    ).toEqual([
      "Amazon de otro país (sin nuestro tag)",
      "Afiliado ajeno eliminado",
      "Sin afiliación",
    ]);
  });

  it("añade el aviso de chollo previo una sola vez", () => {
    expect(
      submissionWarningLabels(
        submission({ previously_published: true, warnings: ["previously_published"] }),
      ),
    ).toEqual(["Se borrará el chollo caducado anterior al aprobar"]);
  });

  it("muestra los códigos desconocidos tal cual", () => {
    expect(submissionWarningLabels(submission({ warnings: ["algo_nuevo"] }))).toEqual([
      "algo_nuevo",
    ]);
  });
});

describe("buildRejectReason", () => {
  it("usa el motivo predefinido", () => {
    expect(buildRejectReason("Ya publicado", "")).toBe("Ya publicado");
  });

  it("añade el texto libre tras dos puntos", () => {
    expect(buildRejectReason("Precio no es una oferta", "  estaba más barato ayer ")).toBe(
      "Precio no es una oferta: estaba más barato ayer",
    );
  });

  it("solo texto libre", () => {
    expect(buildRejectReason("", "  Fuera de stock ")).toBe("Fuera de stock");
  });

  it("vacío si no hay nada", () => {
    expect(buildRejectReason("", "   ")).toBe("");
  });
});
