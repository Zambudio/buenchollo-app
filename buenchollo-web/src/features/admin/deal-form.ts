/**
 * Estado y transformaciones puras del formulario de chollos del admin.
 * Extraído de routes/admin.chollos.tsx (TD-03) para poder testearlo
 * unitariamente sin montar la ruta.
 */
import { calculateDiscount, slugify, toDatetimeLocal } from "@/lib/format";
import type { DealCreatePayload, DealDetailData } from "@/services/api/deals";

export type DealStatus = "active" | "expired" | "scheduled" | "draft";

/** Estado del formulario de admin. Los precios viven como string mientras el
 *  usuario edita (los <input type="number"> trabajan con string). */
export interface DealForm {
  title: string;
  short_description: string;
  description: string;
  image_url: string;
  images: string[];
  current_price: string;
  previous_price: string;
  shipping_info: string;
  affiliate_url: string;
  store_id: string;
  category_id: string;
  subcategory_id: string;
  brand: string;
  status: DealStatus;
  expires_at: string; // datetime-local sin zona
  scheduled_for: string; // datetime-local sin zona
  external_id: string;
  show_keepa_chart: boolean;
  telegram_text?: string;
}

/** Clase compartida de inputs del panel admin (estética terminal). */
export const adminInputCls =
  "w-full bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-sm outline-none focus:border-cyan-glow";

export function emptyForm(): DealForm {
  return {
    title: "",
    short_description: "",
    description: "",
    image_url: "",
    images: [],
    current_price: "",
    previous_price: "",
    shipping_info: "",
    affiliate_url: "",
    store_id: "",
    category_id: "",
    subcategory_id: "",
    brand: "",
    status: "active",
    expires_at: "",
    scheduled_for: "",
    external_id: "",
    show_keepa_chart: false,
  };
}

export function dealToForm(d: DealDetailData): DealForm {
  return {
    title: d.title,
    short_description: d.short_description ?? "",
    description: d.description ?? "",
    image_url: d.image_url ?? "",
    images: d.images ?? [],
    current_price: String(d.current_price),
    previous_price: d.previous_price != null ? String(d.previous_price) : "",
    shipping_info: d.shipping_info ?? "",
    affiliate_url: d.affiliate_url ?? "",
    store_id: d.store_id ?? "",
    category_id: d.category_id ?? "",
    subcategory_id: d.subcategory_id ?? "",
    brand: d.brand ?? "",
    status: (d.status as DealStatus) || "active",
    expires_at: toDatetimeLocal(d.expires_at),
    scheduled_for: toDatetimeLocal(d.scheduled_for),
    external_id: d.external_id ?? "",
    show_keepa_chart: d.show_keepa_chart ?? false,
  };
}

/** Construye el payload de creación/actualización desde el formulario.
 *  `editing` conserva el slug original al editar; al crear se genera uno
 *  único con sufijo temporal. */
export function buildDealPayload(
  form: DealForm,
  editing: DealDetailData | null,
): DealCreatePayload {
  const allImages = form.images.filter(Boolean);
  if (form.image_url && !allImages.includes(form.image_url)) allImages.unshift(form.image_url);
  const mainImage = allImages[0] ?? null;
  const current = +form.current_price;
  const previous = form.previous_price ? +form.previous_price : null;

  const payload: DealCreatePayload = {
    title: form.title.slice(0, 200),
    slug: editing?.slug ?? slugify(form.title) + "-" + Date.now().toString(36),
    short_description: form.short_description?.slice(0, 300) || null,
    description: form.description || null,
    image_url: mainImage,
    images: allImages,
    current_price: current,
    previous_price: previous,
    discount_percentage: calculateDiscount(current, previous),
    shipping_info: form.shipping_info || null,
    affiliate_url: form.affiliate_url,
    store_id: form.store_id || null,
    category_id: form.category_id || null,
    subcategory_id: form.subcategory_id || null,
    brand: form.brand || null,
    status: form.status,
    expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
    scheduled_for:
      form.status === "scheduled" && form.scheduled_for
        ? new Date(form.scheduled_for).toISOString()
        : null,
    external_id: form.external_id || null,
    show_keepa_chart: form.show_keepa_chart,
  };
  if (form.status === "active" && !editing) {
    payload.published_at = new Date().toISOString();
  }
  return payload;
}
