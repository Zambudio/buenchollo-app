import { apiClient } from "./client";

export interface TelegramChannel {
  id: string;
  name: string;
}

export interface TelegramGenerateRequest {
  title: string;
  current_price: number;
  previous_price?: number | null;
  discount_percentage?: number | null;
  description?: string | null;
  affiliate_url?: string;
  expires_at?: string | null;
  /** Redes de afiliación: línea de envío y aviso adicional del programa. */
  shipping_info?: string | null;
  notice?: string | null;
}

export interface TelegramGenerateResponse {
  text: string;
  suggested_categories: string[];
}

export interface TelegramNotifyRequest {
  // Flujo panel (texto ya editado)
  text?: string;
  entities?: object[];
  image_url?: string | null;
  channel_id?: string;
  /** Chollo al que pertenece, para registrar la publicación. */
  deal_id?: string | null;
  // Flujo rápido (checkbox al guardar)
  title?: string;
  current_price?: number;
  previous_price?: number | null;
  discount_percentage?: number | null;
  short_description?: string | null;
  affiliate_url?: string;
  public_url?: string | null;
}

/** Publicación enviada a Telegram (registro). */
export interface TelegramPublication {
  id: string;
  deal_id: string | null;
  channel_kind: "main" | "admin" | "other";
  source: "panel" | "scheduled";
  text: string;
  image_url: string | null;
  price: number | null;
  previous_price: number | null;
  discount_percentage: number | null;
  sent_at: string;
  /** El mismo texto con el precio actual del chollo (null si no se puede corregir). */
  repriced_text?: string | null;
}

export const telegramApi = {
  listPublications(dealId: string): Promise<TelegramPublication[]> {
    return apiClient.get<TelegramPublication[]>(
      `/telegram/publications?deal_id=${encodeURIComponent(dealId)}`,
    );
  },

  getChannels(): Promise<TelegramChannel[]> {
    return apiClient.get<TelegramChannel[]>("/telegram/channels");
  },

  getCategories(): Promise<string[]> {
    return apiClient
      .get<{ categories: string[] }>("/telegram/categories")
      .then((r) => r.categories);
  },

  addCategory(category: string): Promise<string[]> {
    return apiClient
      .post<{ categories: string[] }>("/telegram/categories", { category })
      .then((r) => r.categories);
  },

  generate(data: TelegramGenerateRequest): Promise<TelegramGenerateResponse> {
    return apiClient.post<TelegramGenerateResponse>("/telegram/generate", data);
  },

  notify(data: TelegramNotifyRequest): Promise<{ ok: boolean }> {
    return apiClient.post<{ ok: boolean }>("/telegram/notify", data);
  },
};
