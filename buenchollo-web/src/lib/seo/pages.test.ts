import { describe, expect, it } from "vitest";
import type { BlogPostDetail } from "@/services/api/blog";
import { blogListSeo, blogPostPath, blogPostSeo } from "./blog";
import { categoryIntro, categoryPageSeo, CATEGORY_INTROS } from "./category";
import { HOME_H1, homeSeo } from "./home";
import { faqSchema, organizationSchema, websiteSchema } from "./schema";
import { SITE_FAQ } from "./site-content";

/** Nodo JSON-LD como objeto plano para inspeccionarlo en los asserts. */
const plain = (value: unknown) => JSON.parse(JSON.stringify(value));

const types = (nodes: object[] | undefined) =>
  (nodes ?? []).map((node) => (node as { "@type": string })["@type"]);

describe("homeSeo", () => {
  const deals = [{ slug: "a", title: "A" }];

  it("primera página: canonical raíz, organización, web, lista y FAQ", () => {
    const seo = homeSeo({ page: 1, deals });
    expect(seo.path).toBe("/");
    expect(seo.title).toContain("Chollos de tecnología hoy");
    expect(types(seo.jsonLd)).toEqual(["Organization", "WebSite", "ItemList"]);
    expect(HOME_H1).toContain("Chollos de tecnología");
  });

  it("páginas siguientes: canonical propio y sin FAQ", () => {
    const seo = homeSeo({ page: 3, deals: [] });
    expect(seo.path).toBe("/?page=3");
    expect(seo.title).toContain("página 3");
    expect(types(seo.jsonLd)).toEqual(["Organization", "WebSite"]);
  });
});

describe("categoryPageSeo", () => {
  it("categoría con chollos: título orientado a búsqueda, lista y migas con padre", () => {
    const seo = categoryPageSeo({
      slug: "auriculares",
      name: "Auriculares",
      parent: { slug: "audio", name: "Audio" },
      deals: [{ slug: "a", title: "A" }],
      topCount: 0,
    });
    expect(seo.title).toBe("Chollos de Auriculares hoy: ofertas y descuentos | BuenChollo Tech");
    expect(seo.description).toMatch(/^1 chollos de Auriculares activos ahora\./);
    expect(seo.noindex).toBe(false);
    expect(types(seo.jsonLd)).toEqual(["CollectionPage", "BreadcrumbList", "ItemList"]);
    const crumbs = plain(seo.jsonLd![1]).itemListElement;
    expect(crumbs.map((c: { name: string }) => c.name)).toEqual([
      "Inicio",
      "Categorías",
      "Audio",
      "Auriculares",
    ]);
  });

  it("categoría vacía sin productos destacados: fuera del índice", () => {
    const seo = categoryPageSeo({ slug: "energia", name: "Energía", deals: [], topCount: 0 });
    expect(seo.noindex).toBe(true);
    expect(seo.description).toMatch(/^Ofertas de Energía:/);
    expect(types(seo.jsonLd)).toEqual(["CollectionPage", "BreadcrumbList"]);
  });

  it("categoría vacía con productos destacados sigue indexable", () => {
    expect(
      categoryPageSeo({ slug: "portatiles", name: "Portátiles", deals: [], topCount: 3 }).noindex,
    ).toBe(false);
  });

  it("textos propios para las principales y plantilla para el resto", () => {
    expect(categoryIntro("audio", "Audio")).toBe(CATEGORY_INTROS.audio);
    expect(categoryIntro("tablets", "Tablets", "smartphones-y-tablets")).toMatch(
      /^Chollos y ofertas de Tablets seleccionados/,
    );
    expect(categoryIntro("varios", "Varios")).toContain("de tecnología");
  });
});

function post(overrides: Partial<BlogPostDetail> = {}): BlogPostDetail {
  return {
    id: "p1",
    slug: "mejores-auriculares",
    title: "Los mejores auriculares",
    excerpt: "Guía de compra",
    cover_image_url: "https://img/cover.webp",
    published_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-02T00:00:00Z",
    tags: ["audio"],
    category: { id: "c", name: "Guías", slug: "guias" },
    author: { display_name: "Pedro" },
    seo_title: null,
    seo_description: null,
    canonical_url: null,
    og_image_url: null,
    reading_time_minutes: 5,
    word_count: 900,
    ...overrides,
  } as BlogPostDetail;
}

describe("blogPostSeo", () => {
  it("artículo completo: BlogPosting con autor y metas de artículo", () => {
    const seo = blogPostSeo(post());
    expect(seo.path).toBe("/blog/mejores-auriculares");
    expect(seo.type).toBe("article");
    expect(types(seo.jsonLd)).toEqual(["BlogPosting", "BreadcrumbList"]);
    const article = plain(seo.jsonLd![0]);
    expect(article.author).toEqual({ "@type": "Person", name: "Pedro" });
    expect(article.timeRequired).toBe("PT5M");
    expect(seo.extraMeta).toContainEqual({ property: "article:tag", content: "audio" });
    expect(seo.extraMeta).toContainEqual({ property: "article:section", content: "Guías" });
  });

  it("usa los campos SEO propios y la organización como autor por defecto", () => {
    const seo = blogPostSeo(
      post({
        seo_title: "Título SEO",
        seo_description: "Desc SEO",
        canonical_url: "https://otro.com/x",
        og_image_url: "https://img/og.webp",
        author: null,
        category: null,
        published_at: null,
        tags: [],
        reading_time_minutes: 0,
        word_count: 0,
        excerpt: null,
      }),
    );
    expect(seo.title).toBe("Título SEO | BuenChollo Tech");
    expect(seo.description).toBe("Desc SEO");
    expect(seo.path).toBe("https://otro.com/x");
    expect(seo.image).toBe("https://img/og.webp");
    const article = plain(seo.jsonLd![0]);
    expect(article.author).toEqual({ "@id": "https://buenchollotech.com/#organization" });
    expect(article.keywords).toBeUndefined();
    expect(blogPostPath("x")).toBe("/blog/x");
  });

  it("sin imágenes ni extracto usa el título", () => {
    const seo = blogPostSeo(post({ cover_image_url: null, excerpt: null }));
    expect(seo.image).toBeNull();
    expect(seo.description).toBe("Los mejores auriculares");
  });
});

describe("blogListSeo", () => {
  it("listado indexable con sus artículos", () => {
    const seo = blogListSeo({ page: 1, hasFilters: false, posts: [{ slug: "a", title: "A" }] });
    expect(seo.path).toBe("/blog");
    expect(seo.noindex).toBe(false);
    const blog = plain(seo.jsonLd![0]);
    expect(blog.blogPost[0].url).toBe("https://buenchollotech.com/blog/a");
  });

  it("páginas siguientes con canonical propio y filtros fuera del índice", () => {
    const seo = blogListSeo({ page: 2, hasFilters: true, posts: [] });
    expect(seo.path).toBe("/blog?page=2");
    expect(seo.title).toContain("página 2");
    expect(seo.noindex).toBe(true);
  });
});

describe("schema", () => {
  it("organización y web enlazadas por @id", () => {
    expect(websiteSchema().publisher).toEqual({ "@id": organizationSchema()["@id"] });
  });

  it("FAQPage refleja las preguntas visibles", () => {
    const faq = faqSchema(SITE_FAQ);
    expect(faq.mainEntity).toHaveLength(SITE_FAQ.length);
    expect(faq.mainEntity[0]!.acceptedAnswer.text).toBe(SITE_FAQ[0]!.answer);
  });
});

describe("faqPageSeo", () => {
  it("publica las preguntas visibles como FAQPage en su propia página", async () => {
    const { faqPageSeo, FAQ_PATH } = await import("./faq");
    const seo = faqPageSeo();
    expect(seo.path).toBe(FAQ_PATH);
    expect(types(seo.jsonLd)).toEqual(["BreadcrumbList", "FAQPage"]);
  });
});
