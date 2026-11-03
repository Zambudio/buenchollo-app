import { describe, expect, it } from "vitest";
import {
  submissionFormSchema,
  toSubmissionPayload,
  type SubmissionFormValues,
} from "@/lib/validation/submissions";
import { ApiError } from "@/services/api/client";
import { isProfileIncompleteError, isSubmissionDuplicateError } from "@/services/api/submissions";

const future = (days: number) => new Date(Date.now() + days * 86400000).toISOString().slice(0, 16);
const past = () => new Date(Date.now() - 86400000).toISOString().slice(0, 16);

const valido: SubmissionFormValues = {
  title: "Auriculares X",
  description: "",
  current_price: "49,99",
  previous_price: "79.99",
  coupon_code: "",
  shipping_info: "",
  store_name: "",
  category_id: "cat-1",
  subcategory_id: "",
  starts_at: "",
  expires_at: "",
  images: ["https://a/1.webp", "https://a/2.webp"],
  image_url: "",
};

function message(values: Partial<SubmissionFormValues>, path: string) {
  const r = submissionFormSchema.safeParse({ ...valido, ...values });
  if (r.success) return null;
  return r.error.issues.find((i) => i.path[0] === path)?.message ?? null;
}

describe("submissionFormSchema", () => {
  it("acepta un payload válido", () => {
    expect(submissionFormSchema.safeParse(valido).success).toBe(true);
  });
  it("rechaza título vacío y > 200", () => {
    expect(message({ title: "  " }, "title")).toBe("El título no puede estar vacío");
    expect(message({ title: "a".repeat(201) }, "title")).toBe("Máximo 200 caracteres");
  });
  it("rechaza precio <= 0, > 100000, con más de 2 decimales, vacío o no numérico", () => {
    expect(message({ current_price: "0" }, "current_price")).toBeTruthy();
    expect(message({ current_price: "100000.01" }, "current_price")).toBeTruthy();
    expect(message({ current_price: "10.999" }, "current_price")).toBeTruthy();
    expect(message({ current_price: "" }, "current_price")).toBeTruthy();
    expect(message({ current_price: "abc" }, "current_price")).toBeTruthy();
  });
  it("rechaza previous_price <= current_price", () => {
    expect(message({ previous_price: "49.99" }, "previous_price")).toBe(
      "El precio anterior debe ser mayor que el actual",
    );
    expect(message({ previous_price: "10" }, "previous_price")).toBeTruthy();
  });
  it("rechaza 9 imágenes y acepta 8", () => {
    const imgs = (n: number) => Array.from({ length: n }, (_, i) => `https://a/${i}.webp`);
    expect(message({ images: imgs(9) }, "images")).toBe("Máximo 8 imágenes");
    expect(submissionFormSchema.safeParse({ ...valido, images: imgs(8) }).success).toBe(true);
  });
  it("image_url debe estar entre las imágenes", () => {
    expect(message({ image_url: "https://otra/x.webp" }, "image_url")).toBeTruthy();
    expect(
      submissionFormSchema.safeParse({ ...valido, image_url: "https://a/2.webp" }).success,
    ).toBe(true);
  });
  it("categoría obligatoria", () => {
    expect(message({ category_id: "" }, "category_id")).toBe("Elige una categoría");
  });
  it("límites de cupón, envío y tienda", () => {
    expect(message({ coupon_code: "a".repeat(65) }, "coupon_code")).toBeTruthy();
    expect(message({ shipping_info: "a".repeat(121) }, "shipping_info")).toBeTruthy();
    expect(message({ store_name: "a".repeat(81) }, "store_name")).toBeTruthy();
  });
  it("expires_at pasada se rechaza; futura se acepta", () => {
    expect(message({ expires_at: past() }, "expires_at")).toBe(
      "La fecha de caducidad debe ser futura",
    );
    expect(submissionFormSchema.safeParse({ ...valido, expires_at: future(2) }).success).toBe(true);
  });
  it("expires_at debe ser posterior a starts_at", () => {
    expect(message({ starts_at: future(3), expires_at: future(2) }, "expires_at")).toBe(
      "La caducidad debe ser posterior al inicio",
    );
  });
});

describe("toSubmissionPayload", () => {
  it("normaliza: números, vacíos fuera, image_url = primera imagen", () => {
    const expires = future(2);
    const p = toSubmissionPayload(
      { ...valido, title: "  Hola ", coupon_code: " CUP ", expires_at: expires },
      "https://www.amazon.es/dp/B0",
    );
    expect(p.url).toBe("https://www.amazon.es/dp/B0");
    expect(p.title).toBe("Hola");
    expect(p.current_price).toBe(49.99);
    expect(p.previous_price).toBe(79.99);
    expect(p.coupon_code).toBe("CUP");
    expect(p.description).toBeUndefined();
    expect(p.shipping_info).toBeUndefined();
    expect(p.subcategory_id).toBeUndefined();
    expect(p.starts_at).toBeUndefined();
    expect(p.image_url).toBe("https://a/1.webp");
    expect(p.expires_at).toBe(new Date(expires).toISOString());
  });
  it("sin imágenes no envía image_url y respeta el seleccionado", () => {
    expect(toSubmissionPayload({ ...valido, images: [] }, "u").image_url).toBeUndefined();
    expect(toSubmissionPayload({ ...valido, image_url: "https://a/2.webp" }, "u").image_url).toBe(
      "https://a/2.webp",
    );
  });
});

describe("guards de error", () => {
  it("isSubmissionDuplicateError", () => {
    const dup = new ApiError(409, "x", { code: "SUBMISSION_DUPLICATE" });
    expect(isSubmissionDuplicateError(dup)).toBe(true);
    expect(isSubmissionDuplicateError(new ApiError(409, "x", { code: "DUPLICATE_DEAL" }))).toBe(
      false,
    );
    expect(
      isSubmissionDuplicateError(new ApiError(400, "x", { code: "SUBMISSION_DUPLICATE" })),
    ).toBe(false);
    expect(isSubmissionDuplicateError(new Error("x"))).toBe(false);
  });
  it("isProfileIncompleteError", () => {
    expect(isProfileIncompleteError(new ApiError(403, "x", { code: "PROFILE_INCOMPLETE" }))).toBe(
      true,
    );
    expect(isProfileIncompleteError(new ApiError(403, "x", null))).toBe(false);
  });
});
