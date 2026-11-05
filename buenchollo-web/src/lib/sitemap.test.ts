import { describe, expect, it } from "vitest";
import { dealSitemapEntry } from "./sitemap";

describe("dealSitemapEntry", () => {
  it("un chollo activo se rastrea a diario con prioridad alta", () => {
    expect(
      dealSitemapEntry({
        slug: "monitor-lg",
        status: "active",
        updated_at: "2026-11-05T04:00:00Z",
        published_at: "2026-11-01T10:00:00Z",
      }),
    ).toEqual({
      path: "/chollo/monitor-lg",
      lastmod: "2026-11-05T04:00:00.000Z",
      changefreq: "daily",
      priority: "0.8",
    });
  });

  it("un chollo sin oferta sigue en el sitemap con menos prioridad", () => {
    expect(
      dealSitemapEntry({ slug: "ssd", status: "expired", updated_at: null, published_at: "2026-10-01T00:00:00Z" }),
    ).toEqual({
      path: "/chollo/ssd",
      lastmod: "2026-10-01T00:00:00.000Z",
      changefreq: "weekly",
      priority: "0.5",
    });
  });

  it("sin fechas no inventa lastmod", () => {
    expect(dealSitemapEntry({ slug: "x", status: "active", updated_at: null, published_at: null }).lastmod).toBeUndefined();
  });
});
