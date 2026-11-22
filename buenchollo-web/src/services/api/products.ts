import type { AiProvider } from "@/lib/ai-providers";
import { apiClient } from "./client";

/** Respuesta normalizada de POST /products/preview-from-url. Coincide con
 *  el schema ProductPreviewResponse del backend. */
export interface AmazonPreviewResponse {
  title: string;
  brand: string;
  asin: string;
  product_url: string;
  affiliate_url: string;
  image_url: string;
  current_price: number;
  original_price: number;
  discount_percentage: number;
  store: string;
  category: string;
  category_id: string | null;
  subcategory_id: string | null;
  description: string;
  short_description: string;
  long_description: string;
  telegram_text: string;
  images: string[];
  expires_at: string | null;
}

// Encadena Amazon PA-API + Supabase + llamadas al motor de IA (copywriting y
// categorización, en paralelo gracias a ProductAIEnricher). Aun paralelizado
// puede rondar los 15s del timeout por defecto del cliente; se amplía aquí
// en vez de subir el límite global.
const PREVIEW_FROM_URL_TIMEOUT_MS = 45_000;
// La IA del autocompletado de redes (sin Amazon) puede encadenar varios modelos
// gratuitos que caducan antes de llegar al de reserva: se le da algo más de margen.
// Si aun así no llega, el panel resume la descripción del catálogo.
const ENRICH_TIMEOUT_MS = 60_000;

export const productsApi = {
  /** Genera una preview de producto a partir de una URL de Amazon o ASIN con opción de elegir motor de IA. */
  previewFromUrl: (url: string, provider?: AiProvider): Promise<AmazonPreviewResponse> =>
    apiClient.post<AmazonPreviewResponse>(
      "/products/preview-from-url",
      { url, ...(provider ? { provider } : {}) },
      { signal: AbortSignal.timeout(PREVIEW_FROM_URL_TIMEOUT_MS) },
    ),
  /** Copywriting y categoría con IA de un producto importado de Awin / Tradedoubler. */
  enrich: (req: ProductEnrichRequest, provider?: AiProvider): Promise<ProductEnrichResponse> =>
    apiClient.post<ProductEnrichResponse>(
      "/products/enrich",
      { ...req, ...(provider ? { provider } : {}) },
      { signal: AbortSignal.timeout(ENRICH_TIMEOUT_MS) },
    ),
};

/** Cuerpo de POST /products/enrich (schema ProductEnrichRequest del backend). */
export interface ProductEnrichRequest {
  title: string;
  description?: string;
  brand?: string;
  category_hint?: string;
}

/** Respuesta de POST /products/enrich. */
export interface ProductEnrichResponse {
  short_description: string;
  long_description: string;
  telegram_text: string;
  category_id: string | null;
  subcategory_id: string | null;
  /** false: la IA no escribió los textos; solo trae el resumen de la descripción. */
  copy_ok: boolean;
}
