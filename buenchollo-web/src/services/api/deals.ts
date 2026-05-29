import { apiClient } from "./client";
import type { DealCardData } from "@/features/deals/components/DealCard";

export interface VoteResponse {
  temperature: number;
  votes_up: number;
  votes_down: number;
  my_vote: number;
}

export interface DealDetailData extends DealCardData {
  description: string | null;
  short_description: string | null;
  affiliate_url: string | null;
  status: string;
  expires_at: string | null;
  scheduled_for?: string | null;
  shipping_info: string | null;
  comment_count: number;
  favorite_count: number;
  votes_up: number;
  votes_down: number;
  click_count: number;
  subcategory?: { name: string; slug: string } | null;
  store_id?: string | null;
  category_id?: string | null;
  subcategory_id?: string | null;
  brand?: string | null;
  external_id?: string | null;
  show_keepa_chart?: boolean;
}

/** Payload aceptado por POST /deals/admin. Coincide con el schema DealCreate del backend. */
export interface DealCreatePayload {
  title: string;
  slug?: string | null;
  short_description?: string | null;
  description?: string | null;
  image_url?: string | null;
  images?: string[];
  current_price: number;
  previous_price?: number | null;
  discount_percentage?: number | null;
  shipping_info?: string | null;
  affiliate_url: string;
  store_id?: string | null;
  category_id?: string | null;
  subcategory_id?: string | null;
  brand?: string | null;
  status?: string;
  expires_at?: string | null;
  scheduled_for?: string | null;
  published_at?: string | null;
  source?: string;
  external_id?: string | null;
  show_keepa_chart?: boolean;
}

/** Payload aceptado por PUT /deals/admin/{id}. Todos los campos opcionales (parcial). */
export type DealUpdatePayload = Partial<DealCreatePayload>;

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

  /** Busca chollos con paginación opcional */
  search: (params?: {
    category_id?: string;
    store_id?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<DealCardData[]> => {
    const queryParams = new URLSearchParams();
    if (params?.category_id) queryParams.append("category_id", params.category_id);
    if (params?.store_id) queryParams.append("store_id", params.store_id);
    if (params?.search) queryParams.append("search", params.search);
    if (params?.limit != null) queryParams.append("limit", params.limit.toString());
    if (params?.offset != null && params.offset > 0)
      queryParams.append("offset", params.offset.toString());
    const qs = queryParams.toString();
    const url = qs ? `/deals?${qs}` : "/deals";
    return apiClient.get<DealCardData[]>(url);
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
  create: (data: DealCreatePayload): Promise<DealDetailData> =>
    apiClient.post<DealDetailData>(`/deals/admin`, data),

  /** Actualiza un chollo existente */
  update: (id: string, data: DealUpdatePayload): Promise<DealDetailData> =>
    apiClient.put<DealDetailData>(`/deals/admin/${id}`, data),

  /** Elimina un chollo */
  delete: (id: string): Promise<void> => apiClient.delete(`/deals/admin/${id}`),

  // --- VOTOS ---

  /** Vota en un chollo (1 = arriba, -1 = abajo). Repetir el mismo voto lo anula. */
  vote: (dealId: string, vote: 1 | -1): Promise<VoteResponse> =>
    apiClient.post<VoteResponse>(`/deals/${dealId}/vote`, { vote }),

  /** Devuelve el voto actual del usuario para un chollo (-1, 0 o 1) */
  getMyVote: (dealId: string): Promise<number> =>
    apiClient.get<{ my_vote: number }>(`/deals/${dealId}/my-vote`).then((r) => r.my_vote),

  /** Incrementa el contador de clicks (público). Devuelve el nuevo total. */
  trackClick: (dealId: string): Promise<number> =>
    apiClient
      .post<{ click_count: number }>(`/deals/${dealId}/click`, {})
      .then((r) => r.click_count),
};

export const favoritesApi = {
  /** Lista de chollos favoritos del usuario autenticado */
  getFavorites: (): Promise<DealCardData[]> => apiClient.get<DealCardData[]>("/deals/favorites"),

  /** Toggle: añade o elimina el favorito. Devuelve el estado resultante. */
  toggle: (dealId: string): Promise<{ is_favorited: boolean }> =>
    apiClient.post<{ is_favorited: boolean }>(`/deals/${dealId}/favorite`, {}),

  /** Comprueba si un chollo está en favoritos del usuario */
  check: (dealId: string): Promise<boolean> =>
    apiClient
      .get<{ is_favorited: boolean }>(`/deals/${dealId}/favorite`)
      .then((r) => r.is_favorited),
};
