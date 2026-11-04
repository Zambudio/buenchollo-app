/** Transformaciones puras para moderar propuestas de la comunidad. */
import { toDatetimeLocal } from "@/lib/format";
import type { AdminSubmission, SubmissionStatus } from "@/services/api/submissions";
import { emptyForm, type DealForm } from "./deal-form";

export const SUBMISSION_WARNING_LABELS: Record<string, string> = {
  amazon_foreign_marketplace: "Amazon de otro país (sin nuestro tag)",
  third_party_affiliate_removed: "Afiliado ajeno eliminado",
  not_affiliable: "Sin afiliación",
  previously_published: "Se borrará el chollo caducado anterior al aprobar",
};

export const SUBMISSION_STATUS_LABEL: Record<SubmissionStatus, string> = {
  pending: "Pendiente",
  approved: "Aprobada",
  rejected: "Rechazada",
  withdrawn: "Retirada",
};

export const QUEUE_TABS: { value: SubmissionStatus; label: string }[] = [
  { value: "pending", label: "Pendientes" },
  { value: "approved", label: "Aprobadas" },
  { value: "rejected", label: "Rechazadas" },
  { value: "withdrawn", label: "Retiradas" },
];

export const REJECT_REASONS = [
  "Ya publicado",
  "Precio no es una oferta",
  "Enlace no válido o sin stock",
  "Información incompleta",
  "No es tecnología",
] as const;

export const REJECT_REASON_MIN = 3;
export const REJECT_REASON_MAX = 500;

const AMAZON_HOST = /(^|\.)amazon\.[a-z.]+$/i;
const ASIN_PATH = /\/(?:dp|gp\/product|gp\/aw\/d|exec\/obidos\/asin)\/([A-Z0-9]{10})(?:[/?#]|$)/i;

/** ASIN de un enlace de producto de Amazon, o "" si no se reconoce. */
export function extractAsin(url: string): string {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return "";
  }
  if (!AMAZON_HOST.test(parsed.hostname)) return "";
  const match = ASIN_PATH.exec(parsed.pathname);
  return match?.[1] ? match[1].toUpperCase() : "";
}

export function submissionToDealForm(
  s: AdminSubmission,
  now: Date = new Date(),
): DealForm {
  const images = s.images.filter(Boolean);
  if (s.image_url) {
    const index = images.indexOf(s.image_url);
    if (index >= 0) images.splice(index, 1);
    images.unshift(s.image_url);
  }
  const asin = (
    s.asin ||
    extractAsin(s.affiliate_url) ||
    extractAsin(s.original_url)
  ).toUpperCase();
  const startsAt = s.starts_at ? new Date(s.starts_at) : null;
  const scheduled = !!startsAt && startsAt.getTime() > now.getTime();

  return {
    ...emptyForm(),
    title: s.title,
    description: s.description ?? "",
    image_url: s.image_url ?? "",
    images,
    current_price: String(s.current_price),
    previous_price: s.previous_price != null ? String(s.previous_price) : "",
    shipping_info: s.shipping_info ?? "",
    coupon_code: s.coupon_code ?? "",
    affiliate_url: s.affiliate_url,
    store_id: s.store_id ?? "",
    category_id: s.category_id ?? "",
    subcategory_id: s.subcategory_id ?? "",
    status: scheduled ? "scheduled" : "active",
    expires_at: toDatetimeLocal(s.expires_at),
    scheduled_for: toDatetimeLocal(s.starts_at),
    external_id: asin,
    show_keepa_chart: !!asin,
  };
}

/** Etiquetas legibles de los avisos de una propuesta (sin duplicados). */
export function submissionWarningLabels(s: AdminSubmission): string[] {
  const codes = [...s.warnings];
  if (s.previously_published) codes.push("previously_published");
  return [...new Set(codes)].map((code) => SUBMISSION_WARNING_LABELS[code] ?? code);
}

/** Motivo final de rechazo: etiqueta predefinida + ": " + texto libre. */
export function buildRejectReason(label: string, text: string): string {
  const extra = text.trim();
  if (!label) return extra;
  return extra ? `${label}: ${extra}` : label;
}
