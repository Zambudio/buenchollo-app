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

export const authApi = {
  /** Devuelve el usuario autenticado, sus roles y datos básicos de perfil. */
  me: (): Promise<MeResponse> => apiClient.get<MeResponse>("/auth/me"),
};

export const adminUsersApi = {
  /** Lista todos los perfiles + roles. Sólo admin. */
  list: (): Promise<AdminUserItem[]> => apiClient.get<AdminUserItem[]>("/admin/users"),
};
