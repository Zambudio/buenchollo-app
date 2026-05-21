import { supabase } from "@/integrations/supabase/client";

// Obtenemos la URL de la API desde las variables de entorno
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  
  // Obtenemos la sesión actual de Supabase para adjuntar el JWT
  const { data: { session } } = await supabase.auth.getSession();
  
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        if (typeof errorData.detail === "string") {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((err: any) => `${err.loc.join(".")}: ${err.msg}`).join(", ");
        } else {
          errorMessage = JSON.stringify(errorData.detail);
        }
      }
    } catch (e) {
      // Ignore if not JSON
    }
    throw new Error(errorMessage);
  }

  // Handle empty responses
  const text = await response.text();
  return text ? JSON.parse(text) : (null as any);
}

export const apiClient = {
  get: async <T>(endpoint: string, options?: RequestInit): Promise<T> => {
    return fetchWithAuth<T>(endpoint, options);
  },

  post: async <T>(endpoint: string, data: any, options?: RequestInit): Promise<T> => {
    return fetchWithAuth<T>(endpoint, {
      ...options,
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  put: async <T>(endpoint: string, data: any, options?: RequestInit): Promise<T> => {
    return fetchWithAuth<T>(endpoint, {
      ...options,
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete: async <T>(endpoint: string, options?: RequestInit): Promise<T> => {
    return fetchWithAuth<T>(endpoint, {
      ...options,
      method: "DELETE",
    });
  },
};
