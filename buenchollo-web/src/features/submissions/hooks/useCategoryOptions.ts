/** Categorías y subcategorías activas para el formulario de propuesta.
 *  Mismo origen y mismo reparto padre/hijo que `useAdminDeals` (que además
 *  carga tiendas a la vez y no usa React Query, por eso no se comparte). */
import { useQuery } from "@tanstack/react-query";
import { categoriesService } from "@/services/api/categories";

export function useCategoryOptions() {
  const query = useQuery({
    queryKey: ["categories", "all"],
    queryFn: () => categoriesService.getAll(),
    staleTime: 10 * 60_000,
    select: (all) => ({
      cats: all.filter((c) => !c.parent_id),
      subcats: all.filter((c) => !!c.parent_id),
    }),
  });
  return {
    cats: query.data?.cats ?? [],
    subcats: query.data?.subcats ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}
