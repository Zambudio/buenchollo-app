/** Catálogos del panel admin (tiendas, categorías y subcategorías). */
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { categoriesService, type Category } from "@/services/api/categories";
import { storesService, type Store } from "@/services/api/stores";
import { errorMessage } from "@/lib/errors";

export function useAdminCatalogs() {
  const [stores, setStores] = useState<Store[]>([]);
  const [cats, setCats] = useState<Category[]>([]);
  const [subcats, setSubcats] = useState<Category[]>([]);

  useEffect(() => {
    Promise.all([storesService.getAll(), categoriesService.getAll()])
      .then(([s, c]) => {
        setStores(s);
        setCats(c.filter((x) => !x.parent_id));
        setSubcats(c.filter((x) => !!x.parent_id));
      })
      .catch((err: unknown) => toast.error(errorMessage(err)));
  }, []);

  return { stores, cats, subcats };
}
