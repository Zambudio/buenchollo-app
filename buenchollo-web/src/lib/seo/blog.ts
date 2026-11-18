/** SEO del blog: artículos (`BlogPosting`) y listado. */
import type { BlogPostDetail } from "@/services/api/blog";
import { SITE_URL } from "@/lib/site";
import { absoluteUrl, withBrand, type PageSeo } from "./head";
import { breadcrumbSchema, ORGANIZATION_ID, type Crumb } from "./schema";

export function blogPostPath(slug: string): string {
  return `/blog/${slug}`;
}

export function blogPostSeo(post: BlogPostDetail): PageSeo {
  const path = blogPostPath(post.slug);
  const url = absoluteUrl(path);
  const title = post.seo_title || post.title;
  const description = post.seo_description || post.excerpt || post.title;
  const image = post.og_image_url || post.cover_image_url || null;
  const crumbs: Crumb[] = [
    { name: "Inicio", path: "/" },
    { name: "Blog", path: "/blog" },
    ...(post.category
      ? [{ name: post.category.name, path: `/blog?category=${post.category.slug}` }]
      : []),
    { name: post.title, path },
  ];
  return {
    title: withBrand(title),
    description,
    path: post.canonical_url || path,
    image,
    imageAlt: post.title,
    type: "article",
    jsonLd: [
      {
        "@type": "BlogPosting",
        "@id": `${url}#article`,
        headline: post.title,
        description: post.excerpt || undefined,
        image: image ? [image] : undefined,
        datePublished: post.published_at ?? undefined,
        dateModified: post.updated_at,
        inLanguage: "es-ES",
        wordCount: post.word_count || undefined,
        timeRequired: post.reading_time_minutes ? `PT${post.reading_time_minutes}M` : undefined,
        author: post.author?.display_name
          ? { "@type": "Person", name: post.author.display_name }
          : { "@id": ORGANIZATION_ID },
        publisher: { "@id": ORGANIZATION_ID },
        mainEntityOfPage: { "@type": "WebPage", "@id": url },
        isPartOf: { "@id": `${SITE_URL}/blog#blog` },
        articleSection: post.category?.name ?? undefined,
        keywords: post.tags.length > 0 ? post.tags.join(", ") : undefined,
      },
      breadcrumbSchema(crumbs),
    ],
    extraMeta: [
      ...(post.published_at
        ? [{ property: "article:published_time", content: post.published_at }]
        : []),
      { property: "article:modified_time", content: post.updated_at },
      ...(post.category ? [{ property: "article:section", content: post.category.name }] : []),
      ...post.tags.map((tag) => ({ property: "article:tag", content: tag })),
    ],
  };
}

export interface BlogListInput {
  page: number;
  hasFilters: boolean;
  posts: { slug: string; title: string }[];
}

export function blogListSeo({ page, hasFilters, posts }: BlogListInput): PageSeo {
  const path = page > 1 ? `/blog?page=${page}` : "/blog";
  const description =
    "Guías de compra, comparativas y consejos para comprar tecnología al mejor precio: qué mirar antes de comprar y cuándo una oferta es de verdad un chollo.";
  return {
    title: withBrand(
      page > 1
        ? `Blog de tecnología y guías de compra (página ${page})`
        : "Blog de tecnología y guías de compra",
    ),
    description,
    path,
    // Búsquedas y filtros del blog son variantes del listado: no se indexan.
    noindex: hasFilters,
    jsonLd: [
      {
        "@type": "Blog",
        "@id": `${SITE_URL}/blog#blog`,
        name: "Blog de BuenChollo Tech",
        url: absoluteUrl("/blog"),
        description,
        inLanguage: "es-ES",
        publisher: { "@id": ORGANIZATION_ID },
        blogPost: posts.map((post) => ({
          "@type": "BlogPosting",
          headline: post.title,
          url: absoluteUrl(blogPostPath(post.slug)),
        })),
      },
      breadcrumbSchema([
        { name: "Inicio", path: "/" },
        { name: "Blog", path: "/blog" },
      ]),
    ],
  };
}
