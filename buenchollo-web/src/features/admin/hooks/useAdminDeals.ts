/**
 * Listado admin de chollos + catálogos (tiendas/categorías).
 * Extraído de routes/admin.chollos.tsx (TD-03).
 */
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { dealsService, type DealDetailData } from "@/services/api/deals";
import { categoriesService, type Category } from "@/services/api/categories";
import { storesService, type Store } from "@/services/api/stores";
import { errorMessage } from "@/lib/errors";

export function useAdminDeals() {
  const [deals, setDeals] = useState<DealDetailData[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [stores, setStores] = useState<Store[]>([]);
  const [cats, setCats] = useState<Category[]>([]);
  const [subcats, setSubcats] = useState<Category[]>([]);

  const load = useCallback(() => {
    dealsService
      .getAdminAll(statusFilter)
      .then(setDeals)
      .catch((err: unknown) => toast.error(errorMessage(err)));
  }, [statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    Promise.all([storesService.getAll(), categoriesService.getAll()])
      .then(([s, c]) => {
        setStores(s);
        setCats(c.filter((x) => !x.parent_id));
        setSubcats(c.filter((x) => !!x.parent_id));
      })
      .catch((err: unknown) => toast.error(errorMessage(err)));
  }, []);

  const remove = async (id: string) => {
    if (!confirm("¿Eliminar este chollo?")) return;
    try {
      await dealsService.delete(id);
      load();
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    }
  };

  return { deals, statusFilter, setStatusFilter, stores, cats, subcats, load, remove };
}
