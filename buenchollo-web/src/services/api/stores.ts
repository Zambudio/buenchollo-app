import { apiClient } from "./client";

export interface Store {
  id: string;
  name: string;
  slug: string;
  domain: string | null;
  logo_url: string | null;
  affiliate_id: string | null;
  affiliate_url_template: string | null;
  is_active: boolean;
}

export interface StoreCreate {
  name: string;
  slug: string;
  domain?: string | null;
  logo_url?: string | null;
  affiliate_id?: string | null;
  affiliate_url_template?: string | null;
  is_active?: boolean;
}

export interface StoreUpdate {
  name?: string;
  slug?: string;
  domain?: string | null;
  logo_url?: string | null;
  affiliate_id?: string | null;
  affiliate_url_template?: string | null;
  is_active?: boolean;
}

export const storesService = {
  getAll: (): Promise<Store[]> => apiClient.get<Store[]>("/stores"),

  /** Solo tiendas con al menos un deal activo (para el drawer) */
  getWithDeals: (): Promise<Store[]> => apiClient.get<Store[]>("/stores?has_deals=true"),

  // --- ADMIN ---
  getAdminAll: (): Promise<Store[]> => apiClient.get<Store[]>("/stores/admin/all"),
  create: (data: StoreCreate): Promise<Store> => apiClient.post<Store>("/stores/admin", data),
  update: (id: string, data: StoreUpdate): Promise<Store> =>
    apiClient.put<Store>(`/stores/admin/${id}`, data),
  delete: (id: string): Promise<void> => apiClient.delete(`/stores/admin/${id}`),
};
