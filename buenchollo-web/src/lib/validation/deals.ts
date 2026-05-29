/**
 * Schema de validación para el formulario de chollos del panel de admin.
 *
 * El backend ya valida con Pydantic (`DealCreate` / `DealUpdate`), pero aquí
 * añadimos validación en frontera para feedback inmediato sin viaje al servidor.
 *
 * Convención: los inputs de tipo number en HTML viven como strings en el form
 * state; este schema los convierte a number / null.
 */
import { z } from "zod";

const trimmedString = z.string().trim();
const optionalTrimmedString = trimmedString.optional().transform((v) => v || "");

const requiredPositiveNumberFromString = z
  .string()
  .trim()
  .min(1, "Obligatorio")
  .transform((v, ctx) => {
    const n = Number(v);
    if (!Number.isFinite(n) || n <= 0) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Debe ser un número positivo" });
      return z.NEVER;
    }
    return n;
  });

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

export const dealFormSchema = z
  .object({
    title: trimmedString.min(3, "Mínimo 3 caracteres").max(200, "Máximo 200"),
    affiliate_url: trimmedString.url("URL de afiliado inválida"),
    current_price: requiredPositiveNumberFromString,
    previous_price: optionalPositiveNumberFromString,
    short_description: optionalTrimmedString,
    description: optionalTrimmedString,
  })
  .refine((data) => data.previous_price == null || data.previous_price > data.current_price, {
    path: ["previous_price"],
    message: "El precio anterior debe ser mayor que el actual",
  });

export type DealFormInput = z.input<typeof dealFormSchema>;
