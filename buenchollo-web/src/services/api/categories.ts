import { apiClient } from "./client";

export interface Category {
  id: string;
  name: string;
  slug: string;
  icon: string | null;
  display_order: number;
  parent_id?: string | null;
}

export interface CategoryCreatePayload {
  name: string;
  slug: string;
  icon?: string | null;
  display_order?: number;
  parent_id?: string | null;
  is_active?: boolean;
}

export const categoriesService = {
  getAll: (): Promise<Category[]> => apiClient.get<Category[]>("/categories"),

  getWithDeals: (): Promise<Category[]> => apiClient.get<Category[]>("/categories?has_deals=true"),

  getBySlug: (slug: string): Promise<Category> => apiClient.get<Category>(`/categories/${slug}`),

  getAdminAll: (): Promise<Category[]> => apiClient.get<Category[]>("/categories/admin/all"),

  create: (data: CategoryCreatePayload): Promise<Category> =>
    apiClient.post<Category>("/categories/admin", data),

  delete: (id: string): Promise<void> => apiClient.delete(`/categories/admin/${id}`),
};
