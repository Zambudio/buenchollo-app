import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/services/api/auth";

/** Métricas del panel de admin. Stale corto (15s) porque el admin entra
 *  y sale del dashboard y espera ver números frescos. */
export function useAdminStats() {
  return useQuery({
    queryKey: ["admin", "stats"] as const,
    queryFn: () => adminApi.getStats(),
    staleTime: 15 * 1000,
  });
}
