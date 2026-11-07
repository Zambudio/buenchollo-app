import { categoriesService } from "@/services/api/categories";
import { catalogService, type TopProduct } from "@/services/api/catalog";

export interface BannerTop {
  slug: string;
  name: string;
  products: TopProduct[];
}

const MAX_CATEGORIES = 6;
// El loader de portada depende de `sort` y `page`: sin esta caché, cada cambio
// de filtro o de página repetía 7 peticiones (categorías + 6 tops) para el
// mismo banner. Solo en el navegador; el SSR siempre consulta datos frescos.
const CLIENT_CACHE_MS = 60_000;

let clientCache: { at: number; value: Promise<BannerTop[]> } | null = null;

// Fan-out acotado; cada podio es la clasificación real de una sola categoría.
async function fetchBannerTops(): Promise<BannerTop[]> {
  const categories = await categoriesService.getWithDeals();
  const roots = categories.filter((category) => !category.parent_id);
  const results = await Promise.allSettled(
    roots.slice(0, MAX_CATEGORIES).map(async ({ slug, name }) => ({
      slug,
      name,
      products: (await catalogService.top(slug)).filter((p) => p.position <= 3),
    })),
  );
  return results.flatMap((result) =>
    result.status === "fulfilled" && result.value.products.length ? [result.value] : [],
  );
}

export function loadBannerTops(now: number = Date.now()): Promise<BannerTop[]> {
  if (typeof window === "undefined") return fetchBannerTops();
  if (clientCache && now - clientCache.at < CLIENT_CACHE_MS) return clientCache.value;
  const value = fetchBannerTops();
  const entry = { at: now, value };
  clientCache = entry;
  // Un fallo no se cachea: la siguiente navegación lo reintenta.
  value.catch(() => {
    if (clientCache === entry) clientCache = null;
  });
  return value;
}

export function resetBannerTopsCache(): void {
  clientCache = null;
}
