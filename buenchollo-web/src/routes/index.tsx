import { logError } from "@/lib/logger";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { DealCard, type DealCardData } from "@/features/deals/components/DealCard";
import { HomeFilterTabs, type HomeFilterKey } from "@/features/deals/components/HomeFilterTabs";
import { useAuth } from "@/hooks/useAuth";
import { dealsService, favoritesApi } from "@/services/api/deals";

const SITE = "https://buenchollotech.com";
const PAGE_SIZE = 12;

export const Route = createFileRoute("/")({
  component: HomePage,
  head: () => ({
    meta: [
      { title: "BuenChollo Tech — Chollos y ofertas de tecnología en España" },
      {
        name: "description",
        content:
          "Chollos curados de tecnología: móviles, portátiles, audio, TV, gaming y más. Alertas personalizadas y comunidad. Las mejores ofertas en un solo lugar.",
      },
      {
        property: "og:title",
        content: "BuenChollo Tech — Chollos y ofertas de tecnología en España",
      },
      {
        property: "og:description",
        content:
          "Chollos curados de tecnología: móviles, portátiles, audio, TV, gaming y más. Alertas personalizadas y comunidad.",
      },
      { property: "og:url", content: `${SITE}/` },
      { property: "og:type", content: "website" },
    ],
    links: [{ rel: "canonical", href: `${SITE}/` }],
  }),
});

function sortDeals(deals: DealCardData[], filter: HomeFilterKey): DealCardData[] {
  const sorted = [...deals];
  if (filter === "popular") sorted.sort((a, b) => b.temperature - a.temperature);
  if (filter === "recent")
    sorted.sort((a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime());
  if (filter === "discount")
    sorted.sort((a, b) => (b.discount_percentage ?? 0) - (a.discount_percentage ?? 0));
  return sorted;
}

function HomePage() {
  const { user } = useAuth();
  const [filter, setFilter] = useState<HomeFilterKey>("popular");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [deals, setDeals] = useState<DealCardData[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [favIds, setFavIds] = useState<Set<string>>(new Set());

  // Cambiar de pestaña resetea la paginación
  const handleFilterChange = (next: HomeFilterKey) => {
    setFilter(next);
    setLimit(PAGE_SIZE);
  };

  useEffect(() => {
    setLoading(true);
    dealsService
      .search({ limit })
      .then((data) => {
        setDeals(sortDeals(data, filter));
        setHasMore(data.length >= limit);
      })
      .catch((error) => logError("Error cargando chollos de portada", error))
      .finally(() => setLoading(false));
  }, [filter, limit]);

  // Favoritos del usuario
  useEffect(() => {
    if (!user) {
      setFavIds(new Set());
      return;
    }
    favoritesApi
      .getFavorites()
      .then((favs) => setFavIds(new Set(favs.map((d) => d.id))))
      .catch(() => setFavIds(new Set()));
  }, [user]);

  return (
    <Layout>
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <HomeFilterTabs value={filter} onChange={handleFilterChange} />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-6">
          {deals.map((d) => (
            <DealCard key={d.id} deal={d} isFavorite={favIds.has(d.id)} />
          ))}
        </div>

        {loading && (
          <div className="py-8 text-center font-mono text-xs text-muted-foreground animate-pulse">
            CARGANDO...
          </div>
        )}

        {!loading && hasMore && deals.length > 0 && (
          <div className="flex justify-center mt-8">
            <button
              type="button"
              onClick={() => setLimit((l) => l + PAGE_SIZE)}
              className="font-mono text-xs text-cyan-glow border border-surface-700 hover:border-cyan-glow px-4 py-2 transition-colors"
            >
              [ CARGAR MÁS ]
            </button>
          </div>
        )}

        {!loading && !hasMore && deals.length > 0 && (
          <div className="py-8 text-center font-mono text-xs text-muted-foreground border-t border-surface-700 mt-6">
            — FIN —
          </div>
        )}
      </section>
    </Layout>
  );
}
