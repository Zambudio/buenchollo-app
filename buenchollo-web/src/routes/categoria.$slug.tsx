import { logError } from "@/lib/logger";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { DealCard, type DealCardData } from "@/features/deals/components/DealCard";
import { useMyVotes } from "@/features/deals/hooks/useMyVotes";
import { categoriesService, type Category } from "@/services/api/categories";
import { dealsService } from "@/services/api/deals";

const SITE = "https://buenchollotech.com";

export const Route = createFileRoute("/categoria/$slug")({
  component: CategoryPage,
  loader: async ({ params }) => {
    try {
      const cat = await categoriesService.getBySlug(params.slug);
      return { cat };
    } catch {
      return { cat: null };
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
          children: JSON.stringify({
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
  const [cat, setCat] = useState<Category | null>(null);
  const [deals, setDeals] = useState<DealCardData[]>([]);
  const myVotes = useMyVotes(deals.map((d) => d.id));

  useEffect(() => {
    (async () => {
      try {
        const c = await categoriesService.getBySlug(slug);
        setCat(c);
        if (!c) return;
        const data = await dealsService.search({
          ...(c.parent_id ? { subcategory_id: c.id } : { category_id: c.id }),
          limit: 48,
        });
        setDeals(data);
      } catch (error) {
        logError("Error cargando la categoría o sus chollos", error);
      }
    })();
  }, [slug]);

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
        {deals.length === 0 ? (
          <p className="text-muted-foreground font-mono">
            No hay chollos por ahora en esta categoría.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {deals.map((d) => (
              <DealCard key={d.id} deal={d} myVote={myVotes[d.id]} />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
