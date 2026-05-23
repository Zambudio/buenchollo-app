import { apiClient } from "./client";

export interface AlertCategory {
  id: string;
  name: string;
}

export interface AlertStore {
  id: string;
  name: string;
}

export interface Alert {
  id: string;
  name: string;
  keyword: string | null;
  brand: string | null;
  category_id: string | null;
  store_id: string | null;
  min_price: number | null;
  max_price: number | null;
  min_discount: number | null;
  is_active: boolean;
  created_at: string;
  category: AlertCategory | null;
  store: AlertStore | null;
}

export interface AlertCreate {
  name: string;
  keyword?: string | null;
  brand?: string | null;
  category_id?: string | null;
  store_id?: string | null;
  min_price?: number | null;
  max_price?: number | null;
  min_discount?: number | null;
}

export interface AlertUpdate {
  name?: string;
  keyword?: string | null;
  brand?: string | null;
  category_id?: string | null;
  store_id?: string | null;
  min_price?: number | null;
  max_price?: number | null;
  min_discount?: number | null;
  is_active?: boolean;
}

export const alertsApi = {
  list: (): Promise<Alert[]> =>
    apiClient.get<Alert[]>("/alerts"),

  create: (data: AlertCreate): Promise<Alert> =>
    apiClient.post<Alert>("/alerts", data),

  update: (id: string, data: AlertUpdate): Promise<Alert> =>
    apiClient.put<Alert>(`/alerts/${id}`, data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/alerts/${id}`),

  toggle: (id: string, isActive: boolean): Promise<Alert> =>
    apiClient.put<Alert>(`/alerts/${id}`, { is_active: isActive }),
};
