/**
 * Schema de validación para crear una alerta.
 *
 * Reglas de negocio:
 * - Al menos un criterio debe estar presente (keyword, categoría, tienda, marca,
 *   precio máximo o descuento mínimo).
 * - max_price > 0 si se indica.
 * - min_discount entre 1 y 100 si se indica.
 *
 * Devuelve los datos ya normalizados (strings de inputs convertidos a number o
 * null), listos para `alertsApi.create`.
 */
import { z } from "zod";

const optionalNonEmpty = z
  .string()
  .trim()
  .optional()
  .transform((v) => (v && v.length > 0 ? v : null));

const optionalPositiveNumberFromString = z
  .string()
  .trim()
  .optional()
  .transform((v, ctx) => {
    if (!v) return null;
    const n = Number(v);
    if (!Number.isFinite(n) || n <= 0) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Debe ser un número positivo" });
      return z.NEVER;
    }
    return n;
  });

const optionalDiscountPercentage = z
  .string()
  .trim()
  .optional()
  .transform((v, ctx) => {
    if (!v) return null;
    const n = Number(v);
    if (!Number.isFinite(n) || n < 1 || n > 100) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Descuento entre 1 y 100" });
      return z.NEVER;
    }
    return n;
  });

export const alertFormSchema = z
  .object({
    keyword: optionalNonEmpty,
    category_id: optionalNonEmpty,
    store_id: optionalNonEmpty,
    brand: optionalNonEmpty,
    max_price: optionalPositiveNumberFromString,
    min_discount: optionalDiscountPercentage,
  })
  .refine(
    (data) =>
      Boolean(
        data.keyword ||
        data.category_id ||
        data.store_id ||
        data.brand ||
        data.max_price != null ||
        data.min_discount != null,
      ),
    { message: "Escribe un producto o elige al menos un criterio" },
  );

export type AlertFormInput = z.input<typeof alertFormSchema>;
export type AlertFormData = z.output<typeof alertFormSchema>;
