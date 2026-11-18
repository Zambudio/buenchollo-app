import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { blogService } from "@/services/api/blog";
import { categoriesService } from "@/services/api/categories";
import { dealsService } from "@/services/api/deals";
import { buildLlmsTxt } from "@/lib/seo/llms";

/** Best-effort: si una fuente falla, el fichero sale igualmente con el resto. */
async function safe<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try {
    return await promise;
  } catch {
    return fallback;
  }
}

/** Resumen del sitio para asistentes de IA (formato llmstxt.org). */
export const Route = createFileRoute("/llms.txt")({
  server: {
    handlers: {
      GET: async () => {
        const [deals, categories, sitemap, posts] = await Promise.all([
          safe(dealsService.getLatest(40), []),
          safe(categoriesService.getAll(), []),
          safe(dealsService.getSitemap(), []),
          safe(
            blogService.getPosts({ page: 1, page_size: 10 }).then((page) => page.items),
            [],
          ),
        ]);
        // Solo categorías principales con algún chollo: las vacías no aportan.
        const withDeals = new Set(
          sitemap.flatMap((deal) => [deal.category_id, deal.subcategory_id]),
        );
        const text = buildLlmsTxt({
          deals,
          categories: categories.filter(
            (category) => !category.parent_id && withDeals.has(category.id),
          ),
          posts,
          generatedAt: new Date(),
        });
        return new Response(text, {
          headers: {
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "public, max-age=3600",
          },
        });
      },
    },
  },
});
