import type { AiProvider } from "@/lib/ai-providers";
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
  /** Redes de afiliación: línea de envío y programa (el servidor lee su aviso adicional). */
  shipping_info?: string | null;
  affiliate_program_id?: string | null;
  /** Chollo ya guardado: la IA reescribe la línea ✏️ a partir de `copy_context`. */
  ai_copy?: boolean;
  provider?: AiProvider | null;
  copy_context?: string | null;
}

export interface TelegramGenerateResponse {
  text: string;
  suggested_categories: string[];
  /** Copy escrito por la IA; null si no se pidió o falló (se usó `description`). */
  ai_copy?: string | null;
  /** El mismo post adaptado a WhatsApp (emojis estándar), para compartirlo a mano. */
  whatsapp_text?: string;
}

export interface TelegramNotifyResponse {
  ok: boolean;
  whatsapp_sent?: boolean;
  whatsapp_queued?: boolean;
}

export interface TelegramNotifyRequest {
  // Flujo panel (texto ya editado)
  text?: string;
  entities?: object[];
  image_url?: string | null;
  channel_id?: string;
  /** Chollo al que pertenece, para registrar la publicación. */
  deal_id?: string | null;
  /** Versión WhatsApp editada: va al Canal de WhatsApp (automático) o al canal Admin. */
  whatsapp_text?: string | null;
  /** Tarjeta de oferta (imagen): tienda; con `current_price` y `previous_price`. */
  store_name?: string | null;
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

  /**
   * Último envío registrado del chollo, en cualquier canal: se publica en el
   * canal Admin y desde allí se reenvía al oficial. La lista llega ordenada
   * de más reciente a más antigua.
   */
  async latestPublication(dealId: string): Promise<TelegramPublication | null> {
    const items = await this.listPublications(dealId);
    return items[0] ?? null;
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

  /** Convierte el post de Telegram (ya editado) a su versión de WhatsApp. */
  whatsappText(text: string): Promise<string> {
    return apiClient
      .post<{ text: string }>("/telegram/whatsapp-text", { text })
      .then((r) => r.text);
  },

  /**
   * `whatsapp_queued`: sale sola en el Canal de WhatsApp (publicación automática).
   * `whatsapp_sent`: la copia «versión WhatsApp» llegó al canal Admin.
   */
  notify(data: TelegramNotifyRequest): Promise<TelegramNotifyResponse> {
    return apiClient.post<TelegramNotifyResponse>("/telegram/notify", data);
  },
};
