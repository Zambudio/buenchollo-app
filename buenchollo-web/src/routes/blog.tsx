import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { Search } from "lucide-react";
import { useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { Skeleton } from "@/components/ui/skeleton";
import { DealPagination } from "@/features/deals/components/DealPagination";
import { useBlogPosts, useBlogCategories } from "@/features/blog/hooks/useBlogPublic";
import { BlogPostCard } from "@/features/blog/components/public/BlogPostCard";
import { TelegramCta } from "@/features/blog/components/public/TelegramCta";

const SITE = "https://buenchollotech.com";
const PAGE_SIZE = 12;

const searchSchema = z.object({
  category: z.string().optional(),
  q: z.string().optional(),
  page: z.number().int().min(1).optional(),
});

export const Route = createFileRoute("/blog")({
  component: BlogPage,
  validateSearch: (s) => searchSchema.parse(s),
  head: () => ({
    meta: [
      { title: "Blog · BuenChollo Tech" },
      {
        name: "description",
        content:
          "Guías de compra, comparativas y recomendaciones tecnológicas para encontrar el mejor chollo con conocimiento.",
      },
      { property: "og:title", content: "Blog · BuenChollo Tech" },
      {
        property: "og:description",
        content: "Guías de compra, comparativas y recomendaciones tecnológicas.",
      },
      { property: "og:url", content: `${SITE}/blog` },
      { property: "og:type", content: "website" },
    ],
    links: [{ rel: "canonical", href: `${SITE}/blog` }],
  }),
});

function BlogPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const [queryInput, setQueryInput] = useState(search.q ?? "");
  const page = search.page ?? 1;

  const { data: categories } = useBlogCategories();
  const { data, isLoading } = useBlogPosts({
    category: search.category,
    search: search.q,
    page,
    page_size: PAGE_SIZE,
  });
  const { data: featuredPage } = useBlogPosts({ featured: true, page: 1, page_size: 1 });
  const featured = !search.category && !search.q && page === 1 ? featuredPage?.items[0] : undefined;

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    navigate({ search: { ...search, q: queryInput || undefined, page: undefined } });
  };

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="font-mono text-cyan-glow text-xs tracking-[0.2em] mb-3">&gt; BLOG</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-3">
          Guías, comparativas y recomendaciones
        </h1>
        <p className="text-muted-foreground max-w-2xl mb-8">
          Artículos para elegir mejor: guías de compra, comparativas y recomendaciones tecnológicas
          basadas en los chollos que publicamos.
        </p>

        {featured && (
          <a
            href={`/blog/${featured.slug}`}
            className="block mb-10 border border-cyan-glow/50 bg-surface-800/40 rounded-lg overflow-hidden hover:border-cyan-glow transition-colors"
          >
            <div className="grid md:grid-cols-2">
              {featured.cover_image_url && (
                <img
                  src={featured.cover_image_url}
                  alt={featured.cover_image_alt ?? ""}
                  className="w-full h-56 md:h-full object-cover"
                  loading="eager"
                />
              )}
              <div className="p-6 flex flex-col justify-center">
                <span className="font-mono text-[10px] uppercase text-cyan-glow mb-2">
                  Destacado{featured.category ? ` · ${featured.category.name}` : ""}
                </span>
                <h2 className="text-2xl font-bold mb-2">{featured.title}</h2>
                {featured.excerpt && (
                  <p className="text-muted-foreground line-clamp-3">{featured.excerpt}</p>
                )}
              </div>
            </div>
          </a>
        )}

        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <form onSubmit={submitSearch} className="flex-1 flex gap-2">
            <input
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="Buscar artículos..."
              aria-label="Buscar artículos"
              className="flex-1 bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
            />
            <button
              type="submit"
              aria-label="Buscar"
              className="border border-surface-700 px-3 py-2 hover:border-cyan-glow"
            >
              <Search className="size-4" />
            </button>
          </form>
          <select
            aria-label="Filtrar por categoría"
            value={search.category ?? ""}
            onChange={(e) =>
              navigate({
                search: { ...search, category: e.target.value || undefined, page: undefined },
              })
            }
            className="bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
          >
            <option value="">Todas las categorías</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-64 w-full" />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {data.items.map((post) => (
                <BlogPostCard key={post.id} post={post} />
              ))}
            </div>
            <div className="mt-8">
              <DealPagination
                currentPage={data.page}
                totalPages={data.total_pages}
                onPageChange={(p) => navigate({ search: { ...search, page: p } })}
              />
            </div>
          </>
        ) : (
          <div className="text-center py-16 border border-surface-700 bg-surface-800/30">
            <p className="text-muted-foreground">
              {search.q || search.category
                ? "No hay artículos que coincidan con tu búsqueda."
                : "Todavía no hay artículos publicados. Vuelve pronto."}
            </p>
          </div>
        )}

        <TelegramCta />
      </div>
    </Layout>
  );
}
