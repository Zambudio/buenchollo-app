import { logError } from "@/lib/logger";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { DealCard, type DealCardData } from "@/features/deals/components/DealCard";
import { HomeFilterTabs, type HomeFilterKey } from "@/features/deals/components/HomeFilterTabs";
import { useMyVotes } from "@/features/deals/hooks/useMyVotes";
import { useAuth } from "@/hooks/useAuth";
import { dealsService, favoritesApi } from "@/services/api/deals";

const SITE = "https://buenchollotech.com";
const PAGE_SIZE = 12;
// Tope de seguridad: el backend rechaza limit > 100 (422). Sin este tope, un
// fetch fallido deja hasMore=true con el sentinel aún visible, y el
// IntersectionObserver reintenta sin parar incrementando limit sin fin.
const MAX_LIMIT = 96;

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
      { name: "robots", content: "index, follow, max-image-preview:large" },
      { name: "theme-color", content: "#0b1120" },
    ],
    links: [{ rel: "canonical", href: `${SITE}/` }],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "Organization",
              "@id": `${SITE}/#organization`,
              name: "BuenChollo Tech",
              url: `${SITE}/`,
              logo: {
                "@type": "ImageObject",
                url: `${SITE}/logo-512.png`,
                width: 512,
                height: 512,
              },
              sameAs: ["https://t.me/buenchollotech"],
            },
            {
              "@type": "WebSite",
              "@id": `${SITE}/#website`,
              url: `${SITE}/`,
              name: "BuenChollo Tech",
              publisher: { "@id": `${SITE}/#organization` },
              inLanguage: "es-ES",
              potentialAction: {
                "@type": "SearchAction",
                target: `${SITE}/explorar?q={search_term_string}`,
                "query-input": "required name=search_term_string",
              },
            },
          ],
        }),
      },
    ],
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
  const sentinelRef = useRef<HTMLDivElement>(null);
  const myVotes = useMyVotes(deals.map((d) => d.id));

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
        setHasMore(data.length >= limit && limit < MAX_LIMIT);
      })
      .catch((error) => {
        logError("Error cargando chollos de portada", error);
        setHasMore(false);
      })
      .finally(() => setLoading(false));
  }, [filter, limit]);

  // Scroll infinito: al llegar cerca del final, pide un lote mayor
  // (se refetch y reordena el conjunto completo, ver sortDeals)
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !loading && hasMore) {
          setLimit((l) => Math.min(l + PAGE_SIZE, MAX_LIMIT));
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [loading, hasMore]);

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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground mb-6">
          Chollos y Ofertas de Tecnología Verificadas
        </h1>
        <details className="seo-accordion group mb-6 border-b border-surface-700 pb-3 text-sm text-muted-foreground">
          <summary className="cursor-pointer list-none font-mono text-xs text-cyan-glow hover:text-foreground transition-colors marker:content-none">
            <span className="group-open:hidden">
              + Más información sobre los chollos de tecnología...
            </span>
            <span className="hidden group-open:inline">− Menos información</span>
          </summary>
          <p className="mt-3 max-w-3xl leading-relaxed">
            En BuenChollo Tech somos especialistas en rastrear, verificar y seleccionar diariamente
            las mejores ofertas y descuentos en tecnología. Monitorizamos los precios de Amazon y
            principales tiendas para traerte chollos en informática, telefonía, consolas, gaming, TV,
            audio, domótica y cualquier dispositivo electrónico al precio mínimo histórico. Compara
            ofertas verificadas y ahorra tiempo y dinero en tus compras tech.
          </p>
        </details>
        <HomeFilterTabs value={filter} onChange={handleFilterChange} />

        <section aria-labelledby="home-deals-heading" className="mt-6">
          <h2 id="home-deals-heading" className="sr-only">
            {filter === "popular"
              ? "Chollos más populares"
              : filter === "recent"
                ? "Nuevos chollos"
                : "Chollos con mayor descuento"}
          </h2>
          <div className="deal-feed-grid">
            {deals.map((d, index) => (
              <DealCard
                key={d.id}
                deal={d}
                isFavorite={favIds.has(d.id)}
                myVote={myVotes[d.id]}
                imageLoading={index < 3 ? "eager" : "lazy"}
              />
            ))}
          </div>
        </section>

        <div ref={sentinelRef} className="h-1" />

        {loading && (
          <div className="py-8 text-center font-mono text-xs text-muted-foreground animate-pulse">
            CARGANDO...
          </div>
        )}

        {!loading && !hasMore && deals.length > 0 && (
          <div className="py-8 text-center font-mono text-xs text-muted-foreground border-t border-surface-700 mt-6">
            — FIN —
          </div>
        )}
      </div>
    </Layout>
  );
}
