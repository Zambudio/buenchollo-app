import { describe, expect, it } from "vitest";
import {
  blogSitemapEntry,
  categorySitemapEntries,
  dealSitemapEntry,
  isoDate,
  renderSitemapXml,
  STATIC_SITEMAP_ENTRIES,
} from "./sitemap";

describe("dealSitemapEntry", () => {
  it("un chollo activo se rastrea a diario con prioridad alta e imagen", () => {
    expect(
      dealSitemapEntry({
        slug: "monitor-lg",
        status: "active",
        updated_at: "2026-11-05T04:00:00Z",
        published_at: "2026-11-01T10:00:00Z",
        title: "Monitor LG",
        image_url: "https://img/m.webp",
      }),
    ).toEqual({
      path: "/chollo/monitor-lg",
      lastmod: "2026-11-05T04:00:00.000Z",
      changefreq: "daily",
      priority: "0.8",
      images: [{ loc: "https://img/m.webp", title: "Monitor LG" }],
    });
  });

  it("un chollo sin oferta sigue en el sitemap con menos prioridad y sin imagen", () => {
    expect(
      dealSitemapEntry({
        slug: "ssd",
        status: "expired",
        updated_at: null,
        published_at: "2026-10-01T00:00:00Z",
      }),
    ).toEqual({
      path: "/chollo/ssd",
      lastmod: "2026-10-01T00:00:00.000Z",
      changefreq: "weekly",
      priority: "0.4",
      images: undefined,
    });
  });

  it("sin fechas no inventa lastmod", () => {
    expect(
      dealSitemapEntry({ slug: "x", status: "active", updated_at: null, published_at: null })
        .lastmod,
    ).toBeUndefined();
  });
});

describe("isoDate", () => {
  it("devuelve la primera fecha válida e ignora vacías o inválidas", () => {
    expect(isoDate("", "no-es-fecha", "2026-11-01T00:00:00Z")).toBe("2026-11-01T00:00:00.000Z");
    expect(isoDate(null, undefined, "")).toBeUndefined();
  });
});

describe("categorySitemapEntries", () => {
  const categories = [
    { id: "audio", slug: "audio" },
    { id: "auris", slug: "auriculares" },
    { id: "vacia", slug: "energia" },
  ];

  it("solo publica categorías con chollos, con la fecha del más reciente", () => {
    const entries = categorySitemapEntries(categories, [
      {
        slug: "a",
        status: "active",
        updated_at: "2026-11-02T00:00:00Z",
        published_at: null,
        category_id: "audio",
        subcategory_id: "auris",
      },
      {
        slug: "b",
        status: "expired",
        updated_at: "2026-11-10T00:00:00Z",
        published_at: null,
        category_id: "audio",
        subcategory_id: null,
      },
    ]);
    expect(entries.map((entry) => [entry.path, entry.lastmod])).toEqual([
      ["/categoria/audio", "2026-11-10T00:00:00.000Z"],
      ["/categoria/auriculares", "2026-11-02T00:00:00.000Z"],
    ]);
  });

  it("una categoría con chollos sin fecha se publica sin lastmod", () => {
    const [entry] = categorySitemapEntries(categories, [
      { slug: "c", status: "active", updated_at: null, published_at: null, category_id: "audio" },
    ]);
    expect(entry).toMatchObject({ path: "/categoria/audio", lastmod: undefined });
  });
});

describe("blogSitemapEntry", () => {
  it("no rompe si al artículo le faltan las fechas", () => {
    expect(blogSitemapEntry({ slug: "guia", updated_at: null, published_at: null })).toEqual({
      path: "/blog/guia",
      lastmod: undefined,
      changefreq: "weekly",
      priority: "0.6",
    });
  });
});

describe("renderSitemapXml", () => {
  it("publica URLs absolutas, imágenes y escapa caracteres XML", () => {
    const xml = renderSitemapXml([
      {
        path: "/chollo/a",
        lastmod: "2026-11-01T00:00:00.000Z",
        changefreq: "daily",
        priority: "0.8",
        images: [{ loc: "https://img/a.webp?x=1&y=2", title: "Auriculares <Pro> & más" }],
      },
      { path: "/blog" },
    ]);
    expect(xml).toContain('xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"');
    expect(xml).toContain("<loc>https://buenchollotech.com/chollo/a</loc>");
    expect(xml).toContain("<image:loc>https://img/a.webp?x=1&amp;y=2</image:loc>");
    expect(xml).toContain("<image:title>Auriculares &lt;Pro&gt; &amp; más</image:title>");
    expect(xml).toContain("<loc>https://buenchollotech.com/blog</loc>");
  });

  it("las páginas fijas no incluyen el buscador con noindex", () => {
    expect(STATIC_SITEMAP_ENTRIES.map((entry) => entry.path)).not.toContain("/explorar");
  });
});
