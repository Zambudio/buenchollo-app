import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";
import { DealCard } from "@/features/deals/components/DealCard";
import { useMyVotes } from "@/features/deals/hooks/useMyVotes";
import { categoriesService, type Category } from "@/services/api/categories";
import { dealsService } from "@/services/api/deals";
import { ApiError } from "@/services/api/client";
import { pageHead } from "@/lib/seo/head";
import { categoryIntro, categoryPageSeo } from "@/lib/seo/category";
import { withFallback } from "@/lib/fallback";
import { catalogService } from "@/services/api/catalog";
import { TopProducts } from "@/features/catalog/TopProducts";

export const Route = createFileRoute("/categoria/$slug")({
  component: CategoryPage,
  loader: async ({ params }) => {
    let cat: Category;
    try {
      cat = await categoriesService.getBySlug(params.slug);
    } catch (error) {
      // 404 real para buscadores; otros fallos se propagan como 5xx.
      if (error instanceof ApiError && error.status === 404) throw notFound();
      throw error;
    }
    const [tops, categories, deals] = await Promise.all([
      withFallback(catalogService.top(params.slug), [], "Error cargando el top de la categoría"),
      withFallback(categoriesService.getAll(), [], "Error cargando subcategorías"),
      withFallback(
        dealsService.search({
          ...(cat.parent_id ? { subcategory_id: cat.id } : { category_id: cat.id }),
          limit: 48,
        }),
        [],
        "Error cargando los chollos de la categoría",
      ),
    ]);
    return { cat, tops, categories, deals };
  },
  head: ({ loaderData }) => {
    if (!loaderData) return {};
    const { cat, categories, deals, tops } = loaderData;
    const parent = categories.find((category) => category.id === cat.parent_id) ?? null;
    return pageHead(
      categoryPageSeo({ slug: cat.slug, name: cat.name, parent, deals, topCount: tops.length }),
    );
  },
});

function CategoryPage() {
  const { slug } = Route.useParams();
  const { cat, tops, categories, deals } = Route.useLoaderData();
  const myVotes = useMyVotes(deals.map((d) => d.id));

  const subcategories = categories.filter((category) => category.parent_id === cat.id);
  const parentSlug = categories.find((category) => category.id === cat.parent_id)?.slug ?? null;

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <Link to="/categorias" className="font-mono text-xs text-cyan-glow hover:text-foreground">
          ← TODAS LAS CATEGORÍAS
        </Link>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mt-3 mb-2">
          Chollos de {cat.name}
        </h1>
        <p className="text-muted-foreground font-mono text-sm mb-3">
          {deals.length} chollos activos
        </p>
        <p className="text-muted-foreground text-sm max-w-3xl mb-8">
          {categoryIntro(cat.slug, cat.name, parentSlug)}
        </p>
        {subcategories.length > 0 && (
          <nav aria-label={`Subcategorías de ${cat.name}`} className="category-subnav">
            {subcategories.map((subcategory) => (
              <Link key={subcategory.id} to="/categoria/$slug" params={{ slug: subcategory.slug }}>
                {subcategory.name}
              </Link>
            ))}
          </nav>
        )}
        <TopProducts slug={slug} initialProducts={tops} />
        <h2 className="feed-section-title">Chollos activos de {cat.name ?? "esta categoría"}</h2>
        {deals.length === 0 ? (
          <p className="text-muted-foreground font-mono">
            No hay chollos por ahora en esta categoría.
          </p>
        ) : (
          <div className="deal-feed-grid">
            {deals.map((d) => (
              <DealCard key={d.id} deal={d} myVote={myVotes[d.id]} />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
