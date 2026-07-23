import { describe, expect, it } from "vitest";
import { blogPostFormSchema, blogCategoryFormSchema, scheduleFormSchema } from "./blogPostSchema";

describe("blogPostFormSchema", () => {
  it("acepta un formulario mínimo válido", () => {
    const result = blogPostFormSchema.safeParse({ title: "Un título válido" });
    expect(result.success).toBe(true);
  });

  it("rechaza título demasiado corto", () => {
    const result = blogPostFormSchema.safeParse({ title: "ab" });
    expect(result.success).toBe(false);
  });

  it("rechaza cover_image_url que no sea http(s)", () => {
    const result = blogPostFormSchema.safeParse({
      title: "Título válido",
      cover_image_url: "javascript:alert(1)",
    });
    expect(result.success).toBe(false);
  });

  it("acepta cover_image_url http(s) válida", () => {
    const result = blogPostFormSchema.safeParse({
      title: "Título válido",
      cover_image_url: "https://cdn.example.com/a.png",
    });
    expect(result.success).toBe(true);
  });

  it("limita tags a 20", () => {
    const result = blogPostFormSchema.safeParse({
      title: "Título válido",
      tags: Array.from({ length: 21 }, (_, i) => `tag-${i}`),
    });
    expect(result.success).toBe(false);
  });
});

describe("blogCategoryFormSchema", () => {
  it("exige nombre y slug mínimos", () => {
    expect(blogCategoryFormSchema.safeParse({ name: "a", slug: "a" }).success).toBe(false);
    expect(blogCategoryFormSchema.safeParse({ name: "Ofertas", slug: "ofertas" }).success).toBe(
      true,
    );
  });
});

describe("scheduleFormSchema", () => {
  it("rechaza fechas pasadas", () => {
    const past = new Date(Date.now() - 60_000).toISOString();
    expect(scheduleFormSchema.safeParse({ scheduled_for: past }).success).toBe(false);
  });

  it("acepta fechas futuras", () => {
    const future = new Date(Date.now() + 60_000).toISOString();
    expect(scheduleFormSchema.safeParse({ scheduled_for: future }).success).toBe(true);
  });
});
