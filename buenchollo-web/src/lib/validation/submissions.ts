/**
 * Validación del formulario "Publicar chollo". Espeja las reglas de
 * `SubmissionCreate` del backend (el backend sigue siendo la autoridad).
 *
 * Convención: el schema valida los VALORES DEL FORMULARIO, que son strings
 * (inputs de texto, number y datetime-local) más la lista de imágenes. No
 * transforma: `SubmissionFormValues` es input y output a la vez, y
 * `toSubmissionPayload` convierte a `SubmissionCreatePayload` (números,
 * ISO, vacíos fuera). Los precios aceptan coma o punto decimal.
 *
 * `computeDiscount` no se duplica: es `calculateDiscount` de `@/lib/format`
 * (mismo redondeo y misma semántica de null).
 */
import { z } from "zod";
import { calculateDiscount } from "@/lib/format";
import type { SubmissionCreatePayload } from "@/services/api/submissions";

export const computeDiscount = calculateDiscount;

const MAX_IMAGES = 8;
const MAX_PRICE = 100_000;

export function parsePrice(raw: string): number {
  const normalized = raw.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(normalized)) return Number.NaN;
  return Number(normalized);
}

function hasMoreThanTwoDecimals(raw: string): boolean {
  const decimals = raw.trim().replace(",", ".").split(".")[1];
  return decimals !== undefined && decimals.length > 2;
}

function checkPrice(
  raw: string,
  ctx: z.RefinementCtx,
  path: "current_price" | "previous_price",
  required: boolean,
): number | null {
  if (!raw.trim()) {
    if (required) ctx.addIssue({ code: "custom", path: [path], message: "Obligatorio" });
    return null;
  }
  const n = parsePrice(raw);
  let message: string | null = null;
  if (!Number.isFinite(n)) message = "Introduce un número válido";
  else if (n <= 0) message = "Debe ser mayor que 0";
  else if (n > MAX_PRICE) message = "Máximo 100.000 €";
  else if (hasMoreThanTwoDecimals(raw)) message = "Máximo 2 decimales";
  if (message) {
    ctx.addIssue({ code: "custom", path: [path], message });
    return null;
  }
  return n;
}

const timestamp = (value: string): number => (value.trim() ? Date.parse(value) : Number.NaN);

export const submissionFormSchema = z
  .object({
    title: z
      .string()
      .trim()
      .min(1, "El título no puede estar vacío")
      .max(200, "Máximo 200 caracteres"),
    description: z.string().max(10_000, "Máximo 10.000 caracteres"),
    current_price: z.string(),
    previous_price: z.string(),
    coupon_code: z.string().trim().max(64, "Máximo 64 caracteres"),
    shipping_info: z.string().trim().max(120, "Máximo 120 caracteres"),
    store_name: z.string().trim().max(80, "Máximo 80 caracteres"),
    category_id: z.string().trim().min(1, "Elige una categoría"),
    subcategory_id: z.string(),
    starts_at: z.string(),
    expires_at: z.string(),
    images: z.array(z.string()).max(MAX_IMAGES, `Máximo ${MAX_IMAGES} imágenes`),
    image_url: z.string(),
  })
  .superRefine((data, ctx) => {
    const current = checkPrice(data.current_price, ctx, "current_price", true);
    const previous = checkPrice(data.previous_price, ctx, "previous_price", false);
    if (current != null && previous != null && previous <= current) {
      ctx.addIssue({
        code: "custom",
        path: ["previous_price"],
        message: "El precio anterior debe ser mayor que el actual",
      });
    }

    const starts = timestamp(data.starts_at);
    const expires = timestamp(data.expires_at);
    if (data.starts_at.trim() && Number.isNaN(starts)) {
      ctx.addIssue({ code: "custom", path: ["starts_at"], message: "Fecha de inicio no válida" });
    }
    if (data.expires_at.trim()) {
      if (Number.isNaN(expires)) {
        ctx.addIssue({
          code: "custom",
          path: ["expires_at"],
          message: "Fecha de caducidad no válida",
        });
      } else if (expires <= Date.now()) {
        ctx.addIssue({
          code: "custom",
          path: ["expires_at"],
          message: "La fecha de caducidad debe ser futura",
        });
      } else if (!Number.isNaN(starts) && expires <= starts) {
        ctx.addIssue({
          code: "custom",
          path: ["expires_at"],
          message: "La caducidad debe ser posterior al inicio",
        });
      }
    }

    if (data.image_url.trim() && !data.images.includes(data.image_url.trim())) {
      ctx.addIssue({
        code: "custom",
        path: ["image_url"],
        message: "La imagen principal debe estar entre las imágenes",
      });
    }
  });

export type SubmissionFormValues = z.infer<typeof submissionFormSchema>;

const orUndefined = (value: string): string | undefined => value.trim() || undefined;
const toIso = (value: string): string | undefined =>
  value.trim() ? new Date(value).toISOString() : undefined;

/** Convierte valores YA validados del formulario en el body de POST /submissions. */
export function toSubmissionPayload(
  values: SubmissionFormValues,
  url: string,
): SubmissionCreatePayload {
  const imageUrl = orUndefined(values.image_url) ?? values.images[0];
  const previous = orUndefined(values.previous_price);
  return {
    url,
    title: values.title.trim(),
    description: orUndefined(values.description),
    current_price: parsePrice(values.current_price),
    previous_price: previous ? parsePrice(previous) : undefined,
    coupon_code: orUndefined(values.coupon_code),
    shipping_info: orUndefined(values.shipping_info),
    store_name: orUndefined(values.store_name),
    category_id: values.category_id,
    subcategory_id: orUndefined(values.subcategory_id),
    starts_at: toIso(values.starts_at),
    expires_at: toIso(values.expires_at),
    images: values.images,
    image_url: imageUrl,
  };
}
