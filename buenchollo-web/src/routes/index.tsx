import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { DealCard } from "@/features/deals/components/DealCard";
import { DealPagination } from "@/features/deals/components/DealPagination";
import { HomeFilterTabs, type HomeFilterKey } from "@/features/deals/components/HomeFilterTabs";
import { useAuth } from "@/hooks/useAuth";
import { dealsService, favoritesApi } from "@/services/api/deals";
import { pageHead } from "@/lib/seo/head";
import { HOME_H1, homeSeo } from "@/lib/seo/home";
import { SiteFaq } from "@/features/home/SiteFaq";
import { withFallback } from "@/lib/fallback";
import { HomeSidebar } from "@/features/home/HomeSidebar";
import { blogService } from "@/services/api/blog";
import { TopBanner } from "@/features/home/TopBanner";
import { loadBannerTops } from "@/features/home/bannerTops";
import { CampaignHero } from "@/features/campaigns/CampaignHero";
import { BLACK_FRIDAY, campaignStatus } from "@/lib/campaigns";

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

/** URL rastreable de una página del feed (misma forma que `toHomeSearch`). */
function homeHref(filter: HomeFilterKey, page: number): string {
  const { sort, page: pageParam } = toHomeSearch(filter, page);
  const params = new URLSearchParams();
  if (sort) params.set("sort", sort);
  if (pageParam) params.set("page", String(pageParam));
  const query = params.toString();
  return query ? `/?${query}` : "/";
}

export const Route = createFileRoute("/")({
  component: HomePage,
  validateSearch: parseHomeSearch,
  loaderDeps: ({ search }) => ({ sort: search.sort ?? "popular", page: search.page ?? 1 }),
  loader: async ({ deps }) => {
    const [page, tops, popular, posts] = await Promise.all([
      withFallback(
        dealsService.getPage({ sort: deps.sort, page: deps.page, page_size: PAGE_SIZE }),
        { items: [], total_pages: 1, page: 1, page_size: PAGE_SIZE, total: 0 },
        "Error cargando chollos de portada",
      ),
      withFallback(loadBannerTops(), [], "Error cargando tops de portada"),
      withFallback(dealsService.getPopular(3), [], "Error cargando chollos populares"),
      withFallback(
        blogService.getPosts({ page_size: 3 }).then((result) => result.items),
        [],
        "Error cargando artículos del blog",
      ),
    ]);
    return { ...page, popular, posts, tops };
  },
  head: ({ loaderData }) =>
    pageHead(homeSeo({ page: loaderData?.page ?? 1, deals: loaderData?.items ?? [] })),
});

function HomePage() {
  const { user } = useAuth();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const filter = search.sort ?? "popular";
  const page = search.page ?? 1;
  const data = Route.useLoaderData();
  const deals = data.items;
  const totalPages = data.total_pages;
  const currentPage = data.page;
  const [favIds, setFavIds] = useState<Set<string>>(new Set());
  const dealsHeadingRef = useRef<HTMLHeadingElement>(null);
  const campaign = campaignStatus(BLACK_FRIDAY);

  const handleFilterChange = (next: HomeFilterKey) => {
    void navigate({ search: toHomeSearch(next, 1) });
  };

  useEffect(() => {
    if (currentPage !== page) {
      void navigate({ search: toHomeSearch(filter, currentPage), replace: true });
    }
  }, [currentPage, filter, navigate, page]);

  const changePage = (nextPage: number) => {
    if (nextPage < 1 || nextPage > totalPages || nextPage === currentPage) return;
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
        {/* Sin texto visible de cabecera (decisión de diseño); el H1 se mantiene para SEO y lectores de pantalla. */}
        <h1 className="sr-only">{HOME_H1}</h1>
        {/* Durante una campaña estacional el hero la anuncia; fuera de ella, los tops. */}
        {campaign.promoted ? (
          <CampaignHero campaign={BLACK_FRIDAY} status={campaign} />
        ) : (
          <TopBanner tops={data.tops} />
        )}
        {/* Filtros fuera de la rejilla: el primer chollo y la columna lateral arrancan a la misma altura. */}
        <HomeFilterTabs value={filter} onChange={handleFilterChange} />
        <div className="home-content-layout mt-6">
          <div className="home-feed-column">
            <section aria-labelledby="home-deals-heading">
              <h2 ref={dealsHeadingRef} id="home-deals-heading" className="sr-only">
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
                    imageLoading={index < 3 ? "eager" : "lazy"}
                  />
                ))}
              </div>
            </section>

            {deals.length === 0 && (
              <p className="py-10 text-center font-mono text-sm text-muted-foreground">
                No hay chollos disponibles en este momento.
              </p>
            )}

            {deals.length > 0 && (
              <div className="mt-8 border-t border-surface-700 pt-6">
                <DealPagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  loading={false}
                  onPageChange={changePage}
                  hrefForPage={(target) => homeHref(filter, target)}
                />
              </div>
            )}
          </div>
          <HomeSidebar popular={data.popular} posts={data.posts} />
        </div>
        {currentPage === 1 && <SiteFaq />}
      </div>
    </Layout>
  );
}
