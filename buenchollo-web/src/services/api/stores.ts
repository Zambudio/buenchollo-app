import { apiClient } from "./client";

export interface Store {
  id: string;
  name: string;
  slug: string;
  domain: string | null;
  logo_url: string | null;
}

export const storesService = {
  /** Obtiene todas las tiendas activas */
  getAll: (): Promise<Store[]> => apiClient.get<Store[]>("/stores"),
};
