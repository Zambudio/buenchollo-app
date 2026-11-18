import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { categoriesService } from "@/services/api/categories";
import { dealsService } from "@/services/api/deals";
import { blogService } from "@/services/api/blog";
import {
  blogSitemapEntry,
  categorySitemapEntries,
  dealSitemapEntry,
  renderSitemapXml,
  STATIC_SITEMAP_ENTRIES,
} from "@/lib/sitemap";

/** Best-effort: si una fuente falla, el sitemap sale con las demás. */
async function safe<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try {
    return await promise;
  } catch {
    return fallback;
  }
}

export const Route = createFileRoute("/sitemap.xml")({
  server: {
    handlers: {
      GET: async () => {
        // Datos vía el backend (ADR-002): catálogo permanente (activos y sin
        // oferta), categorías con chollos y artículos publicados.
        const [deals, categories, posts] = await Promise.all([
          safe(dealsService.getSitemap(), []),
          safe(categoriesService.getAll(), []),
          safe(blogService.getSitemap(), []),
        ]);
        const xml = renderSitemapXml([
          ...STATIC_SITEMAP_ENTRIES,
          ...categorySitemapEntries(categories, deals),
          ...deals.map(dealSitemapEntry),
          ...posts.map(blogSitemapEntry),
        ]);
        return new Response(xml, {
          headers: {
            "Content-Type": "application/xml; charset=utf-8",
            "Cache-Control": "public, max-age=3600",
          },
        });
      },
    },
  },
});
