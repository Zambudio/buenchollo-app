import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { categoriesService } from "@/services/api/categories";
import { dealsService } from "@/services/api/deals";
import { blogService } from "@/services/api/blog";
import { dealSitemapEntry, type SitemapEntry } from "@/lib/sitemap";

const BASE_URL = "https://buenchollotech.com";

export const Route = createFileRoute("/sitemap.xml")({
  server: {
    handlers: {
      GET: async () => {
        const entries: SitemapEntry[] = [
          { path: "/", changefreq: "hourly", priority: "1.0" },
          { path: "/explorar", changefreq: "hourly", priority: "0.9" },
          { path: "/categorias", changefreq: "weekly", priority: "0.7" },
          { path: "/blog", changefreq: "daily", priority: "0.7" },
          { path: "/politica-de-privacidad", changefreq: "yearly", priority: "0.5" },
          { path: "/terminos-y-condiciones", changefreq: "yearly", priority: "0.5" },
          { path: "/politica-de-cookies", changefreq: "yearly", priority: "0.5" },
        ];

        // Categorías y chollos vía el backend (ADR-002), como el blog. Antes se
        // leían con supabaseAdmin desde el Worker; fallaba en silencio y el
        // sitemap de producción no publicaba ninguna categoría ni chollo.
        try {
          for (const c of await categoriesService.getAll()) {
            entries.push({ path: `/categoria/${c.slug}`, changefreq: "daily", priority: "0.7" });
          }
        } catch {
          // sitemap es best-effort: si una fuente falla seguimos con las demás
        }

        try {
          // Catálogo permanente: activos y sin oferta (URL estable).
          for (const d of await dealsService.getSitemap()) {
            entries.push(dealSitemapEntry(d));
          }
        } catch {
          // sitemap es best-effort: si una fuente falla seguimos con las demás
        }

        try {
          // Los artículos del blog se obtienen vía el backend (no Supabase
          // directo): endpoint público dedicado `GET /blog/sitemap`.
          const posts = await blogService.getSitemap();
          for (const p of posts) {
            entries.push({
              path: `/blog/${p.slug}`,
              lastmod: new Date(p.updated_at ?? p.published_at ?? "").toISOString(),
              changefreq: "weekly",
              priority: "0.7",
            });
          }
        } catch {
          // sitemap es best-effort: si una fuente falla seguimos con las demás
        }

        const urls = entries.map((e) =>
          [
            `  <url>`,
            `    <loc>${BASE_URL}${e.path}</loc>`,
            e.lastmod ? `    <lastmod>${e.lastmod}</lastmod>` : null,
            e.changefreq ? `    <changefreq>${e.changefreq}</changefreq>` : null,
            e.priority ? `    <priority>${e.priority}</priority>` : null,
            `  </url>`,
          ]
            .filter(Boolean)
            .join("\n"),
        );

        const xml = [
          `<?xml version="1.0" encoding="UTF-8"?>`,
          `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">`,
          ...urls,
          `</urlset>`,
        ].join("\n");

        return new Response(xml, {
          headers: {
            "Content-Type": "application/xml",
            "Cache-Control": "public, max-age=3600",
          },
        });
      },
    },
  },
});
