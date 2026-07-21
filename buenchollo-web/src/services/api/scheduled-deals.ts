import { apiClient } from "./client";

export type ScheduledDealStatus =
  | "programado"
  | "publicado"
  | "cancelado_precio"
  | "cancelado_stock"
  | "error";

export interface ScheduledDealData {
  id: string;
  deal_id: string;
  asin: string;
  title: string;
  description_web: string;
  telegram_text: string;
  telegram_channel_id: string | null;
  offer_price: number;
  regular_price: number | null;
  discount_percentage: number;
  image_url: string | null;
  affiliate_url: string;
  store_name: string;
  category_id: string;
  scheduled_at: string;
  expires_at: string | null;
  status: ScheduledDealStatus;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScheduledDealCreatePayload {
  asin: string;
  title: string;
  slug?: string | null;
  description_web: string;
  short_description?: string | null;
  telegram_text?: string;
  telegram_channel_id?: string | null;
  offer_price: number;
  regular_price?: number | null;
  discount_percentage: number;
  image_url?: string | null;
  images?: string[];
  affiliate_url: string;
  store_name: string;
  store_id?: string | null;
  category_id: string;
  subcategory_id?: string | null;
  brand?: string | null;
  shipping_info?: string | null;
  expires_at?: string | null;
  scheduled_at: string;
  source?: string;
  show_keepa_chart?: boolean;
}

export type ScheduledDealUpdatePayload = Partial<
  Omit<ScheduledDealCreatePayload, "slug" | "source">
>;

export const scheduledDealsService = {
  list: (start: string, end: string): Promise<ScheduledDealData[]> => {
    const query = new URLSearchParams({ start, end });
    return apiClient.get<ScheduledDealData[]>(`/scheduled-deals/admin?${query.toString()}`);
  },

  create: (data: ScheduledDealCreatePayload): Promise<ScheduledDealData> =>
    apiClient.post<ScheduledDealData>("/scheduled-deals/admin", data),

  getNextSlot: (): Promise<{ scheduled_at: string }> =>
    apiClient.get<{ scheduled_at: string }>("/scheduled-deals/admin/next-slot"),

  getByDealId: (dealId: string): Promise<ScheduledDealData> =>
    apiClient.get<ScheduledDealData>(`/scheduled-deals/admin/by-deal/${dealId}`),

  update: (id: string, data: ScheduledDealUpdatePayload): Promise<ScheduledDealData> =>
    apiClient.put<ScheduledDealData>(`/scheduled-deals/admin/${id}`, data),

  reschedule: (id: string, scheduledAt: string): Promise<ScheduledDealData> =>
    apiClient.patch<ScheduledDealData>(`/scheduled-deals/admin/${id}/schedule`, {
      scheduled_at: scheduledAt,
    }),

  delete: (id: string): Promise<void> => apiClient.delete(`/scheduled-deals/admin/${id}`),
};
