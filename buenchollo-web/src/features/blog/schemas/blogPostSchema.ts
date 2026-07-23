/**
 * Validación de frontera para los metadatos editoriales/SEO del formulario
 * de artículos. El contenido Tiptap se valida aparte (el backend es la
 * autoridad final, ver `buenchollo-api/app/modules/blog/domain/content.py`).
 */
import { z } from "zod";

const trimmedString = z.string().trim();
const optionalTrimmedString = trimmedString.optional().transform((v) => v || "");
const optionalUrl = trimmedString
  .optional()
  .transform((v) => v || "")
  .refine((v) => !v || /^https?:\/\//i.test(v), "Debe ser una URL http(s) válida");

export const blogPostFormSchema = z.object({
  title: trimmedString.min(3, "Mínimo 3 caracteres").max(180, "Máximo 180"),
  slug: optionalTrimmedString,
  excerpt: trimmedString
    .max(500, "Máximo 500 caracteres")
    .optional()
    .transform((v) => v || ""),
  cover_image_url: optionalUrl,
  cover_image_alt: trimmedString
    .max(300)
    .optional()
    .transform((v) => v || ""),
  category_id: optionalTrimmedString,
  tags: z.array(z.string().trim().min(1)).max(20).default([]),
  seo_title: trimmedString
    .max(200)
    .optional()
    .transform((v) => v || ""),
  seo_description: trimmedString
    .max(320)
    .optional()
    .transform((v) => v || ""),
  canonical_url: optionalUrl,
  og_image_url: optionalUrl,
  is_featured: z.boolean().default(false),
});

export type BlogPostFormInput = z.input<typeof blogPostFormSchema>;
export type BlogPostFormValues = z.output<typeof blogPostFormSchema>;

export const blogCategoryFormSchema = z.object({
  name: trimmedString.min(2, "Mínimo 2 caracteres").max(100, "Máximo 100"),
  slug: trimmedString.min(2, "Mínimo 2 caracteres").max(200, "Máximo 200"),
  description: optionalTrimmedString,
  is_active: z.boolean().default(true),
  sort_order: z.number().int().default(0),
});

export type BlogCategoryFormInput = z.input<typeof blogCategoryFormSchema>;

export const scheduleFormSchema = z.object({
  scheduled_for: trimmedString.min(1, "Indica fecha y hora").refine((v) => {
    const date = new Date(v);
    return !Number.isNaN(date.getTime()) && date.getTime() > Date.now();
  }, "La fecha debe ser futura"),
});
