import { apiClient } from "./client";

/** Redes de afiliación (Awin / Tradedoubler). Todo va al backend: las
 *  credenciales nunca llegan al navegador (solo booleanos de "configurado"). */

export type ImportStatus =
  | "unsupported_store"
  | "use_amazon_flow"
  | "program_choice_required"
  | "program_disabled"
  | "not_configured"
  | "pending_approval"
  | "catalog_unavailable"
  | "no_match"
  | "ambiguous"
  | "rate_limited"
  | "provider_error"
  | "link_only"
  | "imported"
  | "stale_data";

export interface ProgramSummary {
  id: string;
  name: string;
  network: "awin" | "tradedoubler";
  advertiser_id: string;
  membership_status: string;
  membership_checked_at: string | null;
  enabled: boolean;
  disclosure_text: string | null;
  image_channels: string[];
  max_data_age_hours: number;
  store_id: string | null;
}

export interface ImportedOfferData {
  title?: string | null;
  brand?: string | null;
  model?: string | null;
  description?: string | null;
  short_description?: string | null;
  specs?: Record<string, string>;
  ean?: string | null;
  mpn?: string | null;
  sku?: string | null;
  product_key?: string | null;
  colour?: string | null;
  condition?: string | null;
  image_url?: string | null;
  category_hint?: string | null;
  current_price?: string | null;
  currency?: string | null;
  reference_price?: string | null;
  reference_type?: string | null;
  reference_evidence?: string | null;
  rrp_price?: string | null;
  shipping_info?: string | null;
  in_stock?: boolean | null;
  store_id?: string | null;
  store_name?: string | null;
  external_id?: string | null;
  original_url?: string;
  destination_url?: string;
  affiliate_url?: string | null;
  link_source?: string | null;
  affiliate_program_id: string;
  data_source: string;
}

export interface ImportCandidate {
  product_key: string;
  title: string;
  price: string | null;
  colour: string | null;
  condition: string | null;
  ean: string | null;
  sku: string | null;
  url: string | null;
  image_url: string | null;
}

export interface ImportResponse {
  status: ImportStatus;
  message: string;
  stage: "none" | "link_generated" | "product_imported";
  program: ProgramSummary | null;
  program_options: ProgramSummary[];
  link: { status: string; affiliate_url?: string; source?: string; message?: string };
  offer: ImportedOfferData | null;
  provenance: {
    data_source: string;
    feed_id?: string | null;
    provider_updated_at?: string | null;
    imported_at: string;
    freshness?: "fresh" | "stale" | "unknown";
    max_data_age_hours?: number;
  } | null;
  missing: string[];
  candidates: ImportCandidate[];
  existing_deal: { id: string; slug: string; title: string; status: string } | null;
  warnings: string[];
}

export interface ImportRequest {
  url: string;
  program_id?: string | null;
  product_key?: string | null;
  ean?: string | null;
  sku?: string | null;
  link_only?: boolean;
}

export interface ReadinessRequest {
  affiliate_program_id?: string | null;
  data_source?: string | null;
  affiliate_url?: string | null;
  title?: string | null;
  current_price?: number | null;
  previous_price?: number | null;
  price_reference_type?: string | null;
  price_reference_evidence?: string | null;
  shipping_info?: string | null;
  short_description?: string | null;
  category_id?: string | null;
  image_url?: string | null;
  data_provider_updated_at?: string | null;
  price_verified_at?: string | null;
}

export interface ReadinessResponse {
  applies: boolean;
  ready: boolean;
  blockers: { code: string; message: string }[];
  savings_amount: string | null;
  discount_percentage: number | null;
}

export interface AffiliateFeed {
  feed_id: string;
  name?: string | null;
  language?: string | null;
  selected?: boolean;
  available?: boolean;
  products?: string | number | null;
  last_imported?: string | null;
  last_synced_at?: string | null;
  last_status?: string | null;
  last_error?: string | null;
  rows?: number | null;
}

export interface AffiliateProgram {
  id: string;
  network: "awin" | "tradedoubler";
  advertiser_id: string;
  name: string;
  store_id: string | null;
  domains: string[];
  country: string;
  currency: string;
  membership_status: string;
  membership_checked_at: string | null;
  membership_source: string | null;
  promo_spaces: string[];
  feeds: AffiliateFeed[];
  supports_import: boolean;
  supports_links: boolean;
  deeplink_verified_at: string | null;
  restrictions: {
    marketplace?: boolean | null;
    third_party_sellers?: string | null;
    image_channels?: string[];
    channels?: string[];
    notes?: string | null;
  };
  disclosure_text: string | null;
  max_data_age_hours: number;
  enabled: boolean;
  notes: string | null;
  updated_at: string | null;
}

export type AffiliateProgramUpdate = Partial<{
  store_id: string | null;
  domains: string[];
  promo_spaces: string[];
  membership_status: string;
  selected_feed_ids: string[];
  supports_import: boolean;
  supports_links: boolean;
  deeplink_verified: boolean;
  restrictions: AffiliateProgram["restrictions"];
  disclosure_text: string | null;
  max_data_age_hours: number;
  enabled: boolean;
  notes: string | null;
}>;

export interface IntegrationStatus {
  awin_publisher_api: boolean;
  awin_feeds: boolean;
  tradedoubler_products: boolean;
  tradedoubler_site_id: boolean;
}

export const affiliatesApi = {
  status: () => apiClient.get<IntegrationStatus>("/affiliates/status"),
  programs: () => apiClient.get<AffiliateProgram[]>("/affiliates/programs"),
  updateProgram: (id: string, data: AffiliateProgramUpdate) =>
    apiClient.put<AffiliateProgram>(`/affiliates/programs/${encodeURIComponent(id)}`, data),
  refreshMembership: () =>
    apiClient.post<{ results: Record<string, unknown>[] }>(
      "/affiliates/programs/refresh-membership",
      {},
    ),
  syncFeeds: (programId?: string, force = false) =>
    apiClient.post<{ accepted: boolean }>("/affiliates/feeds/sync", {
      program_id: programId ?? null,
      force,
    }),
  importOffer: (req: ImportRequest) =>
    apiClient.post<ImportResponse>("/affiliates/import", req, {
      signal: AbortSignal.timeout(45_000),
    }),
  readiness: (req: ReadinessRequest) =>
    apiClient.post<ReadinessResponse>("/affiliates/readiness", req),
};
