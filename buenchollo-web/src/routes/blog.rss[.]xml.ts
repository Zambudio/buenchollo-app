import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { blogService } from "@/services/api/blog";

const BASE_URL = "https://buenchollotech.com";

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export const Route = createFileRoute("/blog/rss.xml")({
  server: {
    handlers: {
      GET: async () => {
        let items: string[] = [];
        try {
          const page = await blogService.getPosts({ page: 1, page_size: 30 });
          items = page.items.map((post) => {
            const url = `${BASE_URL}/blog/${post.slug}`;
            return [
              "  <item>",
              `    <title>${escapeXml(post.title)}</title>`,
              `    <link>${url}</link>`,
              `    <guid>${url}</guid>`,
              post.excerpt ? `    <description>${escapeXml(post.excerpt)}</description>` : null,
              post.published_at
                ? `    <pubDate>${new Date(post.published_at).toUTCString()}</pubDate>`
                : null,
              post.category ? `    <category>${escapeXml(post.category.name)}</category>` : null,
              "  </item>",
            ]
              .filter(Boolean)
              .join("\n");
          });
        } catch {
          // RSS es best-effort: si el backend falla, devolvemos un feed vacío.
        }

        const xml = [
          `<?xml version="1.0" encoding="UTF-8"?>`,
          `<rss version="2.0">`,
          "<channel>",
          "  <title>BuenChollo Tech · Blog</title>",
          `  <link>${BASE_URL}/blog</link>`,
          "  <description>Guías de compra, comparativas y recomendaciones tecnológicas.</description>",
          "  <language>es-ES</language>",
          ...items,
          "</channel>",
          "</rss>",
        ].join("\n");

        return new Response(xml, {
          headers: {
            "Content-Type": "application/rss+xml; charset=utf-8",
            "Cache-Control": "public, max-age=1800",
          },
        });
      },
    },
  },
});
