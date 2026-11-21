// FIXTURES sintéticas: ningún dato corresponde a un producto real.
import { describe, expect, it } from "vitest";
import {
  applyEnrichment,
  applyImport,
  buildDealPayload,
  emptyForm,
  isNetworkForm,
  resolveConflict,
} from "./deal-form";
import type { ImportResponse } from "@/services/api/affiliates";

function result(overrides: Partial<NonNullable<ImportResponse["offer"]>> = {}): ImportResponse {
  return {
    status: "imported",
    message: "",
    stage: "product_imported",
    program: null,
    program_options: [],
    link: {
      status: "generated",
      affiliate_url: "https://www.awin1.com/cread.php?x=1",
      source: "awin_linkbuilder",
    },
    offer: {
      title: "FIXTURE Monitor 27",
      short_description: "Panel IPS QHD.",
      description: "Panel IPS QHD 165 Hz.",
      current_price: "199.90",
      rrp_price: "279.00",
      reference_price: null,
      reference_type: "none",
      shipping_info: "Envío: 4,99 € (según la red)",
      image_url: "https://img.fixture.example.com/1.jpg",
      affiliate_url: "https://www.awin1.com/cread.php?x=1",
      store_id: "store-1",
      external_id: "aw:20982:F-1001",
      affiliate_program_id: "prog-1",
      data_source: "awin_feed",
      ...overrides,
    },
    provenance: {
      data_source: "awin_feed",
      imported_at: "2026-11-08T10:00:00+00:00",
      provider_updated_at: "2026-11-08T02:00:00+00:00",
    },
    missing: [],
    candidates: [],
    existing_deal: null,
    warnings: [],
  };
}

describe("applyImport", () => {
  it("rellena un formulario vacío y marca la procedencia", () => {
    const { form, conflicts } = applyImport(emptyForm(), result());
    expect(conflicts).toEqual([]);
    expect(form.title).toBe("FIXTURE Monitor 27");
    expect(form.current_price).toBe("199.90");
    expect(form.images).toEqual(["https://img.fixture.example.com/1.jpg"]);
    expect(form.affiliate_program_id).toBe("prog-1");
    expect(form.data_provider_updated_at).toBe("2026-11-08T02:00:00+00:00");
    expect(form.show_keepa_chart).toBe(false);
    expect(isNetworkForm(form)).toBe(true);
  });

  it("no usa el PVP recomendado como precio anterior", () => {
    const { form } = applyImport(emptyForm(), result());
    expect(form.previous_price).toBe("");
    expect(form.price_reference_type).toBe("");
  });

  it("propone el mínimo de 30 días con su evidencia", () => {
    const { form } = applyImport(
      emptyForm(),
      result({
        reference_price: "849.00",
        reference_type: "provider_price_history_30d",
        reference_evidence: "historial Tradedoubler",
      }),
    );
    expect(form.previous_price).toBe("849.00");
    expect(form.price_reference_evidence).toBe("historial Tradedoubler");
  });

  it("no inventa lo ausente", () => {
    const { form } = applyImport(emptyForm(), result({ shipping_info: null, title: null }));
    expect(form.shipping_info).toBe("");
    expect(form.title).toBe("");
  });

  it("reimportar no pisa lo editado a mano y actualiza lo no tocado", () => {
    const first = applyImport(emptyForm(), result()).form;
    const edited = { ...first, title: "Mi título editorial", status: "draft" as const };
    const again = applyImport(
      edited,
      result({ title: "FIXTURE Monitor 27 (nuevo)", current_price: "189.90" }),
    );
    expect(again.form.title).toBe("Mi título editorial");
    expect(again.form.current_price).toBe("189.90"); // no se editó: se actualiza
    expect(again.conflicts).toEqual([
      { field: "title", current: "Mi título editorial", imported: "FIXTURE Monitor 27 (nuevo)" },
    ]);
    const resolved = resolveConflict(again.form, again.conflicts[0]!);
    expect(resolved.title).toBe("FIXTURE Monitor 27 (nuevo)");
  });

  it("envía la procedencia solo en chollos de redes", () => {
    const network = applyImport(emptyForm(), result()).form;
    const payload = buildDealPayload({ ...network, title: "x", current_price: "10" }, null);
    expect(payload.data_source).toBe("awin_feed");
    expect(payload.affiliate_program_id).toBe("prog-1");
    const amazon = buildDealPayload({ ...emptyForm(), title: "x", current_price: "10" }, null);
    expect("data_source" in amazon).toBe(false);
  });
});

describe("applyEnrichment (IA tras importar de una red)", () => {
  const ai = {
    short_description: "Monitor QHD rápido para jugar",
    long_description: "**QHD** a 165 Hz",
    telegram_text: "Monitor QHD 165 Hz a precio de chollo",
    category_id: "cat-1",
    subcategory_id: "sub-1",
  };

  it("rellena descripción corta, larga, post y categoría que vienen del catálogo o vacíos", () => {
    const imported = applyImport(emptyForm(), result()).form;
    const out = applyEnrichment(imported, ai, { category_id: "cat-1", subcategory_id: "sub-1" });
    expect(out.short_description).toBe(ai.short_description);
    expect(out.description).toBe(ai.long_description);
    expect(out.telegram_text).toBe(ai.telegram_text);
    expect(out.category_id).toBe("cat-1");
    expect(out.subcategory_id).toBe("sub-1");
  });

  it("no pisa lo que el editor ya ha escrito a mano", () => {
    const imported = applyImport(emptyForm(), result()).form;
    const edited = {
      ...imported,
      short_description: "Mi frase",
      description: "Mi texto",
      telegram_text: "Mi post",
      category_id: "cat-9",
      subcategory_id: "sub-9",
    };
    const out = applyEnrichment(edited, ai, { category_id: "cat-1", subcategory_id: "sub-1" });
    expect(out.short_description).toBe("Mi frase");
    expect(out.description).toBe("Mi texto");
    expect(out.telegram_text).toBe("Mi post");
    expect(out.category_id).toBe("cat-9");
    expect(out.subcategory_id).toBe("sub-9");
  });

  it("una respuesta sin la forma esperada no rompe el formulario", () => {
    const imported = applyImport(emptyForm(), result()).form;
    const out = applyEnrichment(imported, [] as unknown as typeof ai, {
      category_id: "",
      subcategory_id: "",
    });
    expect(out).toEqual(imported);
  });

  it("ignora textos vacíos de la IA", () => {
    const imported = applyImport(emptyForm(), result()).form;
    const out = applyEnrichment(
      imported,
      { ...ai, short_description: "", long_description: "  " },
      { category_id: "", subcategory_id: "" },
    );
    expect(out.short_description).toBe("Panel IPS QHD.");
    expect(out.description).toBe("Panel IPS QHD 165 Hz.");
    expect(out.category_id).toBe("");
  });
});
