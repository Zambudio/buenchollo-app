import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { dealsService } from "@/services/api/deals";
import { SITE_URL } from "@/lib/site";
import { renderRss, RSS_HEADERS, type RssItem } from "@/lib/seo/rss";
import { priceText } from "@/lib/seo/text";

/** Feed de los últimos chollos publicados. */
export const Route = createFileRoute("/rss.xml")({
  server: {
    handlers: {
      GET: async () => {
        let items: RssItem[] = [];
        try {
          const deals = await dealsService.getLatest(50);
          items = deals.map((deal) => {
            const discount = deal.discount_percentage ? ` (-${deal.discount_percentage} %)` : "";
            const store = deal.store?.name ? ` en ${deal.store.name}` : "";
            const summary = deal.short_description
              ? `${deal.short_description.trim().replace(/[.\s]*$/, ".")} `
              : "";
            return {
              title: `${deal.title}: ${priceText(deal.current_price)}${discount}`,
              url: `${SITE_URL}/chollo/${deal.slug}`,
              description: `${summary}Precio: ${priceText(deal.current_price)}${store}.`,
              publishedAt: deal.published_at,
              category: deal.category?.name,
            };
          });
        } catch {
          // RSS es best-effort: si el backend falla, devolvemos un feed vacío.
        }
        const xml = renderRss({
          title: "BuenChollo Tech · Chollos de tecnología",
          link: `${SITE_URL}/`,
          selfUrl: `${SITE_URL}/rss.xml`,
          description: "Los últimos chollos y ofertas de tecnología publicados en BuenChollo Tech.",
          items,
        });
        return new Response(xml, { headers: RSS_HEADERS });
      },
    },
  },
});
