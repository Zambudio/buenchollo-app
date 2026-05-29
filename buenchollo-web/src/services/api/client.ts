import { supabase } from "@/integrations/supabase/client";

// Toda la API de negocio cuelga de /v1/. Los servicios de este directorio
// declaran rutas sin prefijo (ej. "/deals/latest") y el cliente añade /v1
// aquí. El único endpoint que NO va versionado es /health (infraestructura),
// pero el frontend no lo llama.
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_URL = `${API_BASE}/v1`;

interface ApiErrorDetail {
  loc: (string | number)[];
  msg: string;
}

function isValidationError(detail: unknown): detail is ApiErrorDetail[] {
  return Array.isArray(detail) && detail.every(
    (d) => d !== null && typeof d === "object" && "loc" in d && "msg" in d,
  );
}

async function extractErrorMessage(response: Response): Promise<string> {
  const fallback = `API Error: ${response.status} ${response.statusText}`;
  try {
    const data = (await response.json()) as { detail?: unknown };
    const detail = data?.detail;
    if (typeof detail === "string") return detail;
    if (isValidationError(detail)) {
      return detail.map((d) => `${d.loc.join(".")}: ${d.msg}`).join(", ");
    }
    if (detail != null) return JSON.stringify(detail);
    return fallback;
  } catch {
    return fallback;
  }
}

async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  const { data: { session } } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    throw new Error(await extractErrorMessage(response));
  }

  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestInit): Promise<T> =>
    fetchWithAuth<T>(endpoint, options),

  post: <T, B = unknown>(endpoint: string, data: B, options?: RequestInit): Promise<T> =>
    fetchWithAuth<T>(endpoint, {
      ...options,
      method: "POST",
      body: JSON.stringify(data),
    }),

  put: <T, B = unknown>(endpoint: string, data: B, options?: RequestInit): Promise<T> =>
    fetchWithAuth<T>(endpoint, {
      ...options,
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: <T = void>(endpoint: string, options?: RequestInit): Promise<T> =>
    fetchWithAuth<T>(endpoint, { ...options, method: "DELETE" }),
};
