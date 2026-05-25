import { apiClient } from "./client";

export interface MeResponse {
  user_id: string;
  email: string | null;
  roles: string[];
  is_admin: boolean;
  has_profile: boolean;
  username: string | null;
}

export const authApi = {
  /** Devuelve el usuario autenticado, sus roles y datos básicos de perfil. */
  me: (): Promise<MeResponse> => apiClient.get<MeResponse>("/auth/me"),
};
