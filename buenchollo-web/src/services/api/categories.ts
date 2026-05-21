import { apiClient } from "./client";

export interface Category {
  id: string;
  name: string;
  slug: string;
  icon: string | null;
  display_order: number;
  parent_id?: string | null;
}

export const categoriesService = {
  /** Obtiene todas las categorías principales activas */
  getAll: (): Promise<Category[]> => apiClient.get<Category[]>("/categories"),

  /** Obtiene una categoría por su slug */
  getBySlug: (slug: string): Promise<Category> => apiClient.get<Category>(`/categories/${slug}`),

  // --- ADMIN ENDPOINTS ---

  /** Obtiene todas las categorías para el panel de admin */
  getAdminAll: (): Promise<Category[]> => 
    apiClient.get<Category[]>("/categories/admin/all"),

  /** Crea una nueva categoría */
  create: (data: any): Promise<Category> => 
    apiClient.post<Category>("/categories/admin", data),

  /** Elimina una categoría */
  delete: (id: string): Promise<void> => 
    apiClient.delete(`/categories/admin/${id}`),
};
