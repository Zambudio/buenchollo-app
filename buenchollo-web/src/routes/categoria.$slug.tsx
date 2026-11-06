import { createFileRoute, Link } from "@tanstack/react-router";
import { Layout } from "@/components/layout/Layout";
import { DealCard } from "@/features/deals/components/DealCard";
import { useMyVotes } from "@/features/deals/hooks/useMyVotes";
import { categoriesService, type Category } from "@/services/api/categories";
import { dealsService } from "@/services/api/deals";
import { serializeJsonLd } from "@/lib/json-ld";
import { catalogService } from "@/services/api/catalog";
import { TopProducts } from "@/features/catalog/TopProducts";

const SITE = "https://buenchollotech.com";

export const Route = createFileRoute("/categoria/$slug")({
  component: CategoryPage,
  loader: async ({ params }) => {
    try {
      const cat = await categoriesService.getBySlug(params.slug);
      const [tops, categories, deals] = await Promise.all([
        catalogService.top(params.slug).catch(() => []),
        categoriesService.getAll().catch(() => []),
        dealsService
          .search({
            ...(cat.parent_id ? { subcategory_id: cat.id } : { category_id: cat.id }),
            limit: 48,
          })
          .catch(() => []),
      ]);
      return { cat, tops, categories, deals };
    } catch {
      return { cat: null, tops: [], categories: [], deals: [] };
    }
  },
  head: ({ params, loaderData }) => {
    const c = loaderData?.cat as (Category & { description?: string }) | null | undefined;
    const name = c?.name ?? params.slug;
    const url = `${SITE}/categoria/${params.slug}`;
    const desc =
      c?.description ?? `Chollos y ofertas de ${name} curados a diario en BuenChollo Tech.`;
    return {
      meta: [
        { title: `Chollos de ${name} · BuenChollo Tech` },
        { name: "description", content: String(desc).slice(0, 200) },
        { property: "og:title", content: `Chollos de ${name}` },
        { property: "og:description", content: String(desc).slice(0, 200) },
        { property: "og:url", content: url },
        { property: "og:type", content: "website" },
      ],
      links: [{ rel: "canonical", href: url }],
      scripts: [
        {
          type: "application/ld+json",
          children: serializeJsonLd({
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            name: `Chollos de ${name}`,
            url,
          }),
        },
      ],
    };
  },
});

function CategoryPage() {
  const { slug } = Route.useParams();
  const { cat, tops, categories, deals } = Route.useLoaderData();
  const myVotes = useMyVotes(deals.map((d) => d.id));

  const subcategories = categories.filter((category) => category.parent_id === cat?.id);

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <Link to="/categorias" className="font-mono text-xs text-cyan-glow hover:text-foreground">
          ← TODAS LAS CATEGORÍAS
        </Link>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mt-3 mb-2">
          {cat?.name ?? "Categoría"}
        </h1>
        <p className="text-muted-foreground font-mono text-sm mb-8">
          {deals.length} chollos activos
        </p>
        {subcategories.length > 0 && (
          <nav aria-label={`Subcategorías de ${cat?.name}`} className="category-subnav">
            {subcategories.map((subcategory) => (
              <Link key={subcategory.id} to="/categoria/$slug" params={{ slug: subcategory.slug }}>
                {subcategory.name}
              </Link>
            ))}
          </nav>
        )}
        <TopProducts slug={slug} initialProducts={tops} />
        <h2 className="feed-section-title">Chollos activos de {cat?.name ?? "esta categoría"}</h2>
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
