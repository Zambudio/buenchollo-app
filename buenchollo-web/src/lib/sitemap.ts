export interface SitemapEntry {
  path: string;
  lastmod?: string;
  changefreq?: "always" | "hourly" | "daily" | "weekly" | "monthly" | "yearly" | "never";
  priority?: string;
}

export interface SitemapDeal {
  slug: string;
  status: string;
  updated_at: string | null;
  published_at: string | null;
}

/**
 * Catálogo permanente: los chollos sin oferta (`expired`) conservan su URL y
 * siguen en el sitemap, con menos prioridad que las ofertas activas.
 */
export function dealSitemapEntry(deal: SitemapDeal): SitemapEntry {
  const date = deal.updated_at ?? deal.published_at;
  const active = deal.status === "active";
  return {
    path: `/chollo/${deal.slug}`,
    lastmod: date ? new Date(date).toISOString() : undefined,
    changefreq: active ? "daily" : "weekly",
    priority: active ? "0.8" : "0.5",
  };
}
