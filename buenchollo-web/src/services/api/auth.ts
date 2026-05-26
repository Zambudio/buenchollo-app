import { apiClient } from "./client";

export interface MeResponse {
  user_id: string;
  email: string | null;
  roles: string[];
  is_admin: boolean;
  has_profile: boolean;
  username: string | null;
}

export interface AdminUserItem {
  user_id: string;
  display_name: string | null;
  username: string | null;
  avatar_url: string | null;
  created_at: string | null;
  roles: string[];
}

export interface MyProfile {
  user_id: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  username: string | null;
}

export interface MyStats {
  comments_made: number;
  comments_received: number;
  likes_given: number;
  likes_received: number;
  dislikes_received: number;
  deal_votes_cast: number;
  favorites_count: number;
}

export const authApi = {
  /** Devuelve el usuario autenticado, sus roles y datos básicos de perfil. */
  me: (): Promise<MeResponse> => apiClient.get<MeResponse>("/auth/me"),

  /** Perfil completo del usuario autenticado. */
  getMyProfile: (): Promise<MyProfile> => apiClient.get<MyProfile>("/users/me/profile"),

  /** Actualiza display_name y bio del usuario autenticado. */
  updateMyProfile: (data: { display_name: string; bio: string }): Promise<MyProfile> =>
    apiClient.put<MyProfile>("/users/me/profile", data),

  /** Estadísticas agregadas del usuario (comentarios, votos, favoritos…). */
  getMyStats: (): Promise<MyStats> => apiClient.get<MyStats>("/users/me/stats"),
};

export interface AdminStats {
  deals: number;
  active: number;
  favs: number;
  alerts: number;
  comments: number;
  users: number;
}

export const adminUsersApi = {
  /** Lista todos los perfiles + roles. Sólo admin. */
  list: (): Promise<AdminUserItem[]> => apiClient.get<AdminUserItem[]>("/admin/users"),
};

export const adminApi = {
  /** Contadores agregados para el dashboard. Sólo admin. */
  getStats: (): Promise<AdminStats> => apiClient.get<AdminStats>("/admin/stats"),
};
