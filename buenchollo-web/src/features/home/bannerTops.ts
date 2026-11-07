import { categoriesService } from "@/services/api/categories";
import { catalogService, type TopProduct } from "@/services/api/catalog";

export interface BannerTop {
  slug: string;
  name: string;
  products: TopProduct[];
}

// Bounded fan-out; each podium belongs to one real category ranking.
export async function loadBannerTops(): Promise<BannerTop[]> {
  const categories = await categoriesService.getWithDeals();
  const roots = categories.filter((category) => !category.parent_id);
  const results = await Promise.allSettled(
    roots.slice(0, 6).map(async ({ slug, name }) => ({
      slug,
      name,
      products: (await catalogService.top(slug)).filter((p) => p.position <= 3),
    })),
  );
  return results.flatMap((result) =>
    result.status === "fulfilled" && result.value.products.length ? [result.value] : [],
  );
}
