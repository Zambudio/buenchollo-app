/**
 * Listado admin de chollos + catálogos (tiendas/categorías).
 * Extraído de routes/admin.chollos.tsx (TD-03).
 */
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { dealsService, type DealDetailData } from "@/services/api/deals";
import { errorMessage } from "@/lib/errors";
import { useAdminCatalogs } from "./useAdminCatalogs";

export function useAdminDeals() {
  const [deals, setDeals] = useState<DealDetailData[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const { stores, cats, subcats } = useAdminCatalogs();

  const load = useCallback(() => {
    dealsService
      .getAdminAll(statusFilter)
      .then(setDeals)
      .catch((err: unknown) => toast.error(errorMessage(err)));
  }, [statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

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
