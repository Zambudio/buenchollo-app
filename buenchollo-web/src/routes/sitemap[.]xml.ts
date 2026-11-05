import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { supabaseAdmin } from "@/integrations/supabase/client.server";
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

        try {
          const { data: cats } = await supabaseAdmin
            .from("categories")
            .select("slug,updated_at")
            .eq("is_active", true);
          for (const c of cats ?? []) {
            entries.push({
              path: `/categoria/${c.slug}`,
              lastmod: c.updated_at ? new Date(c.updated_at).toISOString() : undefined,
              changefreq: "daily",
              priority: "0.7",
            });
          }
        } catch {
          // sitemap es best-effort: si una fuente falla seguimos con las demás
        }

        try {
          const { data: deals } = await supabaseAdmin
            .from("deals")
            .select("slug,status,updated_at,published_at")
            // Catálogo permanente: también los chollos sin oferta (URL estable).
            .in("status", ["active", "expired"])
            .order("published_at", { ascending: false })
            .limit(5000);
          for (const d of deals ?? []) {
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
