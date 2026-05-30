/** Tests del type guard `isDuplicateDealError`.
 *
 *  Este guard decide si el catch del Save del admin abre el diálogo de
 *  "Chollo duplicado" o muestra el toast genérico. Un falso positivo
 *  abriría el diálogo con datos undefined; un falso negativo perdería el
 *  flujo de sobrescribir/editar.
 */
import { describe, expect, it } from "vitest";
import { ApiError } from "@/services/api/client";
import { isDuplicateDealError } from "@/services/api/deals";

const existing = { id: "abc-123", slug: "producto-x", title: "Producto X" };

describe("isDuplicateDealError", () => {
  it("acepta un ApiError 409 con code DUPLICATE_DEAL y deal existente", () => {
    const err = new ApiError(409, "ya existe", {
      code: "DUPLICATE_DEAL",
      detail: "ya existe",
      existing_deal: existing,
    });
    expect(isDuplicateDealError(err)).toBe(true);
  });

  it("rechaza un ApiError con status 400 aunque el body coincida", () => {
    const err = new ApiError(400, "bad", {
      code: "DUPLICATE_DEAL",
      existing_deal: existing,
    });
    expect(isDuplicateDealError(err)).toBe(false);
  });

  it("rechaza un ApiError 409 sin code DUPLICATE_DEAL", () => {
    const err = new ApiError(409, "otro conflict", { code: "OTHER" });
    expect(isDuplicateDealError(err)).toBe(false);
  });

  it("rechaza un Error nativo (no ApiError)", () => {
    expect(isDuplicateDealError(new Error("boom"))).toBe(false);
  });

  it("rechaza valores que no son Error", () => {
    expect(isDuplicateDealError("string")).toBe(false);
    expect(isDuplicateDealError(null)).toBe(false);
    expect(isDuplicateDealError(undefined)).toBe(false);
    expect(isDuplicateDealError({ status: 409, code: "DUPLICATE_DEAL" })).toBe(false);
  });

  it("rechaza ApiError 409 con data null", () => {
    const err = new ApiError(409, "no body", null);
    expect(isDuplicateDealError(err)).toBe(false);
  });
});
