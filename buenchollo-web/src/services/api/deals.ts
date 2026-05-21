import { apiClient } from "./client";
import type { DealCardData } from "@/components/DealCard";

export interface DealDetailData extends DealCardData {
  description: string | null;
  short_description: string | null;
  affiliate_url: string | null;
  status: string;
  expires_at: string | null;
  shipping_info: string | null;
  comment_count: number;
  favorite_count: number;
  votes_up: number;
  votes_down: number;
  click_count: number;
  subcategory?: { name: string; slug: string } | null;
}

export const dealsService = {
  /** Obtiene los chollos más recientes */
  getLatest: (limit = 8): Promise<DealCardData[]> => 
    apiClient.get<DealCardData[]>(`/deals/latest?limit=${limit}`),

  /** Obtiene los chollos más populares/calientes */
  getPopular: (limit = 4): Promise<DealCardData[]> => 
    apiClient.get<DealCardData[]>(`/deals/popular?limit=${limit}`),

  /** Obtiene un chollo por su slug */
  getBySlug: (slug: string): Promise<DealDetailData> => 
    apiClient.get<DealDetailData>(`/deals/${slug}`),

  /** Busca chollos (opcional: por categoría) */
  search: (params?: { category_id?: string; store_id?: string; search?: string; limit?: number }): Promise<DealCardData[]> => {
    const queryParams = new URLSearchParams();
    if (params?.category_id) queryParams.append("category_id", params.category_id);
    if (params?.store_id) queryParams.append("store_id", params.store_id);
    if (params?.search) queryParams.append("search", params.search);
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    
    const qs = queryParams.toString();
    return apiClient.get<DealCardData[]>(`/deals${qs ? `?${qs}` : ''}`);
  },

  // --- ADMIN ENDPOINTS ---

  /** Obtiene todos los chollos para el panel de admin */
  getAdminAll: (status?: string, limit = 200): Promise<DealDetailData[]> => {
    const qs = new URLSearchParams();
    if (status && status !== "all") qs.append("status", status);
    qs.append("limit", limit.toString());
    return apiClient.get<DealDetailData[]>(`/deals/admin/all?${qs.toString()}`);
  },

  /** Crea un nuevo chollo */
  create: (data: any): Promise<DealDetailData> => 
    apiClient.post<DealDetailData>(`/deals/admin`, data),

  /** Actualiza un chollo existente */
  update: (id: string, data: any): Promise<DealDetailData> => 
    apiClient.put<DealDetailData>(`/deals/admin/${id}`, data),

  /** Elimina un chollo */
  delete: (id: string): Promise<void> => 
    apiClient.delete(`/deals/admin/${id}`),
};
