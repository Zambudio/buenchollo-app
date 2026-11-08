/**
 * Estado y transformaciones puras del formulario de chollos del admin.
 * Extraído de routes/admin.chollos.tsx (TD-03) para poder testearlo
 * unitariamente sin montar la ruta.
 */
import { calculateDiscount, slugify, toDatetimeLocal } from "@/lib/format";
import type { Category } from "@/services/api/categories";
import type { DealCreatePayload, DealDetailData } from "@/services/api/deals";
import type { ImportResponse } from "@/services/api/affiliates";

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
  coupon_code: string;
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
  /** Redes de afiliación (Awin / Tradedoubler). Vacíos en Amazon/manual. */
  affiliate_program_id: string;
  data_source: string;
  data_provider_updated_at: string; // ISO
  data_imported_at: string; // ISO
  price_verified_at: string; // ISO; comprobación manual en tienda
  price_reference_type: string;
  price_reference_evidence: string;
  import_snapshot: Record<string, string> | null;
}

/** Clase compartida de inputs del panel admin (estética terminal). */
export const adminInputCls =
  "w-full bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-sm outline-none focus:border-cyan-glow";

/** Filtro de UX; la allowlist de seguridad definitiva vive en el backend. */
export function isAmazonProductReference(value: string): boolean {
  return /amazon\./i.test(value) || /amzn\./i.test(value) || /\.amazon(?:[/?#:]|$)/i.test(value);
}

const EMPTY_NETWORK_FIELDS = {
  affiliate_program_id: "",
  data_source: "",
  data_provider_updated_at: "",
  data_imported_at: "",
  price_verified_at: "",
  price_reference_type: "",
  price_reference_evidence: "",
  import_snapshot: null,
};

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
    coupon_code: "",
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
    ...EMPTY_NETWORK_FIELDS,
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
    coupon_code: d.coupon_code ?? "",
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
    affiliate_program_id: d.affiliate_program_id ?? "",
    data_source: d.data_source ?? "",
    data_provider_updated_at: d.data_provider_updated_at ?? "",
    data_imported_at: d.data_imported_at ?? "",
    price_verified_at: d.price_verified_at ?? "",
    price_reference_type: d.price_reference_type ?? "",
    price_reference_evidence: d.price_reference_evidence ?? "",
    import_snapshot: (d.import_snapshot as Record<string, string> | null) ?? null,
  };
}

export const FALLBACK_VARIOS_CATEGORY_ID = "99b72435-42f6-4628-a1af-3f66af5e4a88";
export const FALLBACK_VARIOS_SUBCATEGORY_ID = "970d38ab-20e8-43e8-97a1-5c84dfd391c5";

export function resolveCategorySelection(
  categoryId: string,
  subcategoryId: string,
  categories: Category[],
  subcategories: Category[],
): { category_id: string; subcategory_id: string } {
  // 1. Si tenemos una categoría válida en el catálogo
  const matchedCategory = categories.find((c) => c.id === categoryId);
  if (matchedCategory) {
    const matchedSubcategory = subcategories.find(
      (s) => s.id === subcategoryId && s.parent_id === matchedCategory.id,
    );
    if (matchedSubcategory) {
      return { category_id: matchedCategory.id, subcategory_id: matchedSubcategory.id };
    }
    // Si la categoría existe pero la subcategoría falta o no coincide con el padre,
    // buscamos la primera subcategoría válida de esta categoría para no perder la clasificación
    const firstSubcategory = subcategories.find((s) => s.parent_id === matchedCategory.id);
    if (firstSubcategory) {
      return { category_id: matchedCategory.id, subcategory_id: firstSubcategory.id };
    }
  }

  // 2. Si no hay categoría válida, buscamos "Varios" en las categorías activas
  const fallbackCategory = categories.find(
    (category) =>
      category.slug === "varios-xly2" || category.name.trim().toLocaleLowerCase("es") === "varios",
  );
  const fallbackSubcategory = fallbackCategory
    ? subcategories.find(
        (subcategory) =>
          subcategory.parent_id === fallbackCategory.id &&
          (subcategory.slug === "varios-y175" ||
            subcategory.name.trim().toLocaleLowerCase("es") === "varios"),
      ) || subcategories.find((s) => s.parent_id === fallbackCategory.id)
    : undefined;

  // 3. Devolvemos la pareja Varios encontrada o los IDs canónicos de producción (si el catálogo aún está cargando)
  return {
    category_id: fallbackCategory?.id ?? FALLBACK_VARIOS_CATEGORY_ID,
    subcategory_id: fallbackSubcategory?.id ?? FALLBACK_VARIOS_SUBCATEGORY_ID,
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
  const titleSlug = slugify(form.title).slice(0, 180) || "chollo";

  const payload: DealCreatePayload = {
    title: form.title.slice(0, 200),
    slug: editing?.slug ?? titleSlug + "-" + Date.now().toString(36),
    short_description: form.short_description?.slice(0, 300) || null,
    description: form.description || null,
    image_url: mainImage,
    images: allImages,
    current_price: current,
    previous_price: previous,
    discount_percentage: calculateDiscount(current, previous),
    shipping_info: form.shipping_info || null,
    coupon_code: form.coupon_code.trim().slice(0, 64) || null,
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
  if (isNetworkForm(form)) {
    payload.affiliate_program_id = form.affiliate_program_id || null;
    payload.data_source = form.data_source || null;
    payload.data_provider_updated_at = form.data_provider_updated_at || null;
    payload.data_imported_at = form.data_imported_at || null;
    payload.price_verified_at = form.price_verified_at || null;
    payload.price_reference_type = form.price_reference_type || null;
    payload.price_reference_evidence = form.price_reference_evidence.trim().slice(0, 500) || null;
    payload.import_snapshot = form.import_snapshot;
  }
  if (form.status === "active" && !editing) {
    payload.published_at = new Date().toISOString();
  }
  return payload;
}

// ── Redes de afiliación ──────────────────────────────────────────────────────

/** Chollo importado de Awin/Tradedoubler: aplica sus reglas de publicación. */
export function isNetworkForm(
  form: Pick<DealForm, "affiliate_program_id" | "data_source">,
): boolean {
  return (
    !!form.affiliate_program_id ||
    ["awin_feed", "tradedoubler_api", "link_only"].includes(form.data_source)
  );
}

/** Tipos de "precio anterior" que SÍ lo justifican (el backend usa la misma lista). */
export const PROOF_REFERENCE_TYPES = [
  "provider_price_history_30d",
  "store_strikethrough_verified",
  "manual_verified",
];

export const REFERENCE_TYPE_LABELS: Record<string, string> = {
  none: "Sin precio anterior",
  rrp: "PVP recomendado (no justifica el «antes»)",
  feed_original_price: "Precio original del feed sin fecha (no justifica)",
  provider_price_history_30d: "Mínimo de 30 días según el historial de la red",
  store_strikethrough_verified: "Precio tachado comprobado en la tienda",
  manual_verified: "Otra evidencia comprobada a mano",
};

type ImportableField =
  | "title"
  | "short_description"
  | "description"
  | "brand"
  | "current_price"
  | "previous_price"
  | "shipping_info"
  | "image_url"
  | "affiliate_url"
  | "store_id"
  | "external_id"
  | "price_reference_type"
  | "price_reference_evidence";

export const IMPORT_FIELD_LABELS: Record<ImportableField, string> = {
  title: "Título",
  short_description: "Descripción corta",
  description: "Descripción larga",
  brand: "Marca",
  current_price: "Precio actual",
  previous_price: "Precio anterior",
  shipping_info: "Envío",
  image_url: "Imagen principal",
  affiliate_url: "Enlace afiliado",
  store_id: "Tienda",
  external_id: "ID de producto",
  price_reference_type: "Tipo de precio anterior",
  price_reference_evidence: "Evidencia del precio anterior",
};

export interface ImportConflict {
  field: ImportableField;
  current: string;
  imported: string;
}

/** Valores que aporta la importación (solo los que trae la fuente). */
export function importedValues(result: ImportResponse): Partial<Record<ImportableField, string>> {
  const o = result.offer;
  if (!o) return {};
  const out: Partial<Record<ImportableField, string>> = {};
  const put = (field: ImportableField, value: string | null | undefined) => {
    if (value != null && String(value).trim() !== "") out[field] = String(value);
  };
  put("title", o.title);
  put("short_description", o.short_description);
  put("description", o.description);
  put("brand", o.brand);
  put("current_price", o.current_price);
  // Solo una referencia con significado y evidencia se propone como "antes".
  if (o.reference_price && o.reference_type && PROOF_REFERENCE_TYPES.includes(o.reference_type)) {
    put("previous_price", o.reference_price);
    put("price_reference_type", o.reference_type);
    put("price_reference_evidence", o.reference_evidence);
  }
  put("shipping_info", o.shipping_info);
  put("image_url", o.image_url);
  put("affiliate_url", o.affiliate_url);
  put("store_id", o.store_id);
  put("external_id", o.external_id);
  return out;
}

/** Aplica una importación al formulario sin pisar en silencio lo editado a
 *  mano: un campo con valor propio distinto del importado (y distinto de la
 *  importación anterior) se deja como está y se devuelve como conflicto. */
export function applyImport(
  form: DealForm,
  result: ImportResponse,
): { form: DealForm; conflicts: ImportConflict[] } {
  const values = importedValues(result);
  const previous = form.import_snapshot ?? {};
  const next: DealForm = { ...form };
  const conflicts: ImportConflict[] = [];
  for (const [field, imported] of Object.entries(values) as [ImportableField, string][]) {
    const current = String(next[field] ?? "");
    if (!current.trim() || current === imported || current === previous[field]) {
      (next as unknown as Record<string, unknown>)[field] = imported;
    } else {
      conflicts.push({ field, current, imported });
    }
  }
  const image = next.image_url;
  if (image && values.image_url === image && !next.images.includes(image)) {
    next.images = [image, ...next.images];
  }
  if (result.offer) {
    next.affiliate_program_id = result.offer.affiliate_program_id;
    next.data_source = result.offer.data_source;
    next.show_keepa_chart = false;
  }
  next.data_imported_at = result.provenance?.imported_at ?? new Date().toISOString();
  next.data_provider_updated_at = result.provenance?.provider_updated_at ?? "";
  next.import_snapshot = { ...previous, ...values } as Record<string, string>;
  return { form: next, conflicts };
}

/** Aplica el valor importado de un conflicto (decisión explícita del editor). */
export function resolveConflict(form: DealForm, conflict: ImportConflict): DealForm {
  const next = { ...form, [conflict.field]: conflict.imported } as DealForm;
  if (conflict.field === "image_url") {
    next.images = [conflict.imported, ...form.images.filter((img) => img !== conflict.imported)];
  }
  return next;
}
