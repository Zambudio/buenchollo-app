import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { blogService } from "@/services/api/blog";
import { SITE_URL } from "@/lib/site";
import { renderRss, RSS_HEADERS, type RssItem } from "@/lib/seo/rss";

export const Route = createFileRoute("/blog/rss.xml")({
  server: {
    handlers: {
      GET: async () => {
        let items: RssItem[] = [];
        try {
          const page = await blogService.getPosts({ page: 1, page_size: 30 });
          items = page.items.map((post) => ({
            title: post.title,
            url: `${SITE_URL}/blog/${post.slug}`,
            description: post.excerpt,
            publishedAt: post.published_at,
            category: post.category?.name,
          }));
        } catch {
          // RSS es best-effort: si el backend falla, devolvemos un feed vacío.
        }
        const xml = renderRss({
          title: "BuenChollo Tech · Blog",
          link: `${SITE_URL}/blog`,
          selfUrl: `${SITE_URL}/blog/rss.xml`,
          description: "Guías de compra, comparativas y recomendaciones tecnológicas.",
          items,
        });
        return new Response(xml, { headers: RSS_HEADERS });
      },
    },
  },
});
