import { apiClient } from "./client";

export interface TopProduct {
  id: string;
  title: string;
  image_url: string | null;
  deal_slug: string | null;
  deal_status: string | null;
  current_price: number | null;
  vote_count: number;
  position: number;
}

export const catalogService = {
  top: (slug: string): Promise<TopProduct[]> =>
    apiClient.get<TopProduct[]>(`/catalog/tops/${encodeURIComponent(slug)}`),
  myVotes: (ids: string[]): Promise<string[]> =>
    apiClient.get<string[]>(
      `/catalog/my-votes?${ids.map((id) => `product_ids=${encodeURIComponent(id)}`).join("&")}`,
    ),
  vote: (id: string): Promise<{ voted: boolean }> =>
    apiClient.post<{ voted: boolean }>(`/catalog/products/${encodeURIComponent(id)}/vote`, {}),
};
