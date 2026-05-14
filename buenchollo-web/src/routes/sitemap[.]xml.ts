import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { supabaseAdmin } from "@/integrations/supabase/client.server";

const BASE_URL = "https://buenchollotech.lovable.app";

interface SitemapEntry {
  path: string;
  lastmod?: string;
  changefreq?: "always" | "hourly" | "daily" | "weekly" | "monthly" | "yearly" | "never";
  priority?: string;
}

export const Route = createFileRoute("/sitemap.xml")({
  server: {
    handlers: {
      GET: async () => {
        const entries: SitemapEntry[] = [
          { path: "/", changefreq: "hourly", priority: "1.0" },
          { path: "/explorar", changefreq: "hourly", priority: "0.9" },
          { path: "/categorias", changefreq: "weekly", priority: "0.7" },
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
        } catch {}

        try {
          const { data: deals } = await supabaseAdmin
            .from("deals")
            .select("slug,updated_at,published_at")
            .eq("status", "active")
            .order("published_at", { ascending: false })
            .limit(2000);
          for (const d of deals ?? []) {
            entries.push({
              path: `/chollo/${d.slug}`,
              lastmod: (d.updated_at ?? d.published_at)
                ? new Date(d.updated_at ?? d.published_at).toISOString()
                : undefined,
              changefreq: "daily",
              priority: "0.8",
            });
          }
        } catch {}

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
