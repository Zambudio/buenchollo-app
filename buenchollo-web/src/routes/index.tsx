import { logError } from "@/lib/logger";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { DealCard, type DealCardData } from "@/features/deals/components/DealCard";
import { DealPagination } from "@/features/deals/components/DealPagination";
import { HomeFilterTabs, type HomeFilterKey } from "@/features/deals/components/HomeFilterTabs";
import { useMyVotes } from "@/features/deals/hooks/useMyVotes";
import { useAuth } from "@/hooks/useAuth";
import { dealsService, favoritesApi } from "@/services/api/deals";

const SITE = "https://buenchollotech.com";
const PAGE_SIZE = 30;

interface HomeSearch {
  sort?: HomeFilterKey;
  page?: number;
}

function parseHomeSearch(search: Record<string, unknown>): HomeSearch {
  const sort = ["popular", "recent", "discount"].includes(String(search.sort))
    ? (search.sort as HomeFilterKey)
    : undefined;
  const parsedPage = Number(search.page);
  const page = Number.isSafeInteger(parsedPage) && parsedPage >= 2 ? parsedPage : undefined;
  return { sort, page };
}

function toHomeSearch(filter: HomeFilterKey, page: number): HomeSearch {
  return {
    sort: filter === "popular" ? undefined : filter,
    page: page === 1 ? undefined : page,
  };
}

export const Route = createFileRoute("/")({
  component: HomePage,
  validateSearch: parseHomeSearch,
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

function HomePage() {
  const { user } = useAuth();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const filter = search.sort ?? "popular";
  const page = search.page ?? 1;
  const [deals, setDeals] = useState<DealCardData[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalPages, setTotalPages] = useState(1);
  const currentPage = Math.min(page, totalPages);
  const [favIds, setFavIds] = useState<Set<string>>(new Set());
  const dealsHeadingRef = useRef<HTMLHeadingElement>(null);
  const myVotes = useMyVotes(deals.map((d) => d.id));

  const handleFilterChange = (next: HomeFilterKey) => {
    void navigate({ search: toHomeSearch(next, 1) });
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    dealsService
      .getPage({ sort: filter, page, page_size: PAGE_SIZE })
      .then((data) => {
        if (cancelled) return;
        setDeals(data.items);
        setTotalPages(data.total_pages);
        if (data.page !== page) {
          void navigate({ search: toHomeSearch(filter, data.page), replace: true });
        }
      })
      .catch((error) => {
        if (cancelled) return;
        logError("Error cargando chollos de portada", error);
        setDeals([]);
        setTotalPages(1);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filter, navigate, page]);

  const changePage = (nextPage: number) => {
    if (loading || nextPage < 1 || nextPage > totalPages || nextPage === currentPage) return;
    void navigate({ search: toHomeSearch(filter, nextPage) });
    const headingTop = dealsHeadingRef.current?.getBoundingClientRect().top;
    if (headingTop != null) {
      window.scrollTo({ top: Math.max(0, window.scrollY + headingTop - 96), behavior: "smooth" });
    }
  };

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
            principales tiendas para traerte chollos en informática, telefonía, consolas, gaming,
            TV, audio, domótica y cualquier dispositivo electrónico al precio mínimo histórico.
            Compara ofertas verificadas y ahorra tiempo y dinero en tus compras tech.
          </p>
        </details>
        <HomeFilterTabs value={filter} onChange={handleFilterChange} />

        <section aria-labelledby="home-deals-heading" className="mt-6" aria-busy={loading}>
          <h2 ref={dealsHeadingRef} id="home-deals-heading" className="sr-only">
            {filter === "popular"
              ? "Chollos más populares"
              : filter === "recent"
                ? "Nuevos chollos"
                : "Chollos con mayor descuento"}
          </h2>
          <div className={`deal-feed-grid transition-opacity ${loading ? "opacity-60" : ""}`}>
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

        {loading && (
          <div className="py-8 text-center font-mono text-xs text-muted-foreground animate-pulse">
            CARGANDO...
          </div>
        )}

        {!loading && deals.length === 0 && (
          <p className="py-10 text-center font-mono text-sm text-muted-foreground">
            No hay chollos disponibles en este momento.
          </p>
        )}

        {deals.length > 0 && (
          <div className="mt-8 border-t border-surface-700 pt-6">
            <DealPagination
              currentPage={currentPage}
              totalPages={totalPages}
              loading={loading}
              onPageChange={changePage}
            />
          </div>
        )}
      </div>
    </Layout>
  );
}
