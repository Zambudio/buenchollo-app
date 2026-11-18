/**
 * Construcción del sitemap (`/sitemap.xml`): funciones puras para poder
 * probarlas sin red. La ruta solo obtiene los datos y devuelve el XML.
 */
import { SITE_URL } from "@/lib/site";
import { escapeXml } from "@/lib/xml";

export interface SitemapImage {
  loc: string;
  title?: string;
}

export interface SitemapEntry {
  path: string;
  lastmod?: string;
  changefreq?: "always" | "hourly" | "daily" | "weekly" | "monthly" | "yearly" | "never";
  priority?: string;
  images?: SitemapImage[];
}

export interface SitemapDeal {
  slug: string;
  status: string;
  updated_at: string | null;
  published_at: string | null;
  title?: string | null;
  image_url?: string | null;
  category_id?: string | null;
  subcategory_id?: string | null;
}

export interface SitemapCategory {
  id: string;
  slug: string;
}

export interface SitemapPost {
  slug: string;
  updated_at?: string | null;
  published_at?: string | null;
}

/** Páginas fijas indexables. `/explorar` (buscador con filtros) es `noindex`. */
export const STATIC_SITEMAP_ENTRIES: SitemapEntry[] = [
  { path: "/", changefreq: "hourly", priority: "1.0" },
  { path: "/categorias", changefreq: "daily", priority: "0.8" },
  { path: "/blog", changefreq: "daily", priority: "0.7" },
  { path: "/sobre-nosotros", changefreq: "monthly", priority: "0.5" },
  { path: "/contacto", changefreq: "yearly", priority: "0.3" },
  { path: "/politica-de-privacidad", changefreq: "yearly", priority: "0.2" },
  { path: "/terminos-y-condiciones", changefreq: "yearly", priority: "0.2" },
  { path: "/politica-de-cookies", changefreq: "yearly", priority: "0.2" },
];

/** ISO 8601 o `undefined` si la fecha falta o no es válida (antes una fecha
 *  vacía lanzaba excepción y dejaba el blog entero fuera del sitemap). */
export function isoDate(...candidates: Array<string | null | undefined>): string | undefined {
  for (const value of candidates) {
    if (!value) continue;
    const date = new Date(value);
    if (!Number.isNaN(date.getTime())) return date.toISOString();
  }
  return undefined;
}

/**
 * Catálogo permanente: los chollos sin oferta (`expired`) conservan su URL y
 * siguen en el sitemap, con menos prioridad que las ofertas activas.
 */
export function dealSitemapEntry(deal: SitemapDeal): SitemapEntry {
  const active = deal.status === "active";
  return {
    path: `/chollo/${deal.slug}`,
    lastmod: isoDate(deal.updated_at, deal.published_at),
    changefreq: active ? "daily" : "weekly",
    priority: active ? "0.8" : "0.4",
    images: deal.image_url ? [{ loc: deal.image_url, title: deal.title ?? undefined }] : undefined,
  };
}

/** Solo categorías con algún chollo: una categoría vacía es contenido escaso. */
export function categorySitemapEntries(
  categories: SitemapCategory[],
  deals: SitemapDeal[],
): SitemapEntry[] {
  const latest = new Map<string, string>();
  for (const deal of deals) {
    const date = isoDate(deal.updated_at, deal.published_at) ?? "";
    for (const id of [deal.category_id, deal.subcategory_id]) {
      if (!id) continue;
      const current = latest.get(id);
      if (current === undefined || date > current) latest.set(id, date);
    }
  }
  return categories
    .filter((category) => latest.has(category.id))
    .map((category) => ({
      path: `/categoria/${category.slug}`,
      lastmod: latest.get(category.id) || undefined,
      changefreq: "daily" as const,
      priority: "0.7",
    }));
}

export function blogSitemapEntry(post: SitemapPost): SitemapEntry {
  return {
    path: `/blog/${post.slug}`,
    lastmod: isoDate(post.updated_at, post.published_at),
    changefreq: "weekly",
    priority: "0.6",
  };
}

export function renderSitemapXml(entries: SitemapEntry[]): string {
  const urls = entries.map((entry) =>
    [
      `  <url>`,
      `    <loc>${escapeXml(`${SITE_URL}${entry.path}`)}</loc>`,
      entry.lastmod ? `    <lastmod>${entry.lastmod}</lastmod>` : null,
      entry.changefreq ? `    <changefreq>${entry.changefreq}</changefreq>` : null,
      entry.priority ? `    <priority>${entry.priority}</priority>` : null,
      ...(entry.images ?? []).map((image) =>
        [
          `    <image:image>`,
          `      <image:loc>${escapeXml(image.loc)}</image:loc>`,
          image.title ? `      <image:title>${escapeXml(image.title)}</image:title>` : null,
          `    </image:image>`,
        ]
          .filter(Boolean)
          .join("\n"),
      ),
      `  </url>`,
    ]
      .filter(Boolean)
      .join("\n"),
  );
  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">`,
    ...urls,
    `</urlset>`,
  ].join("\n");
}
