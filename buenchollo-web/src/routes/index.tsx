import { createFileRoute } from "@tanstack/react-router";
import { Fragment, useEffect, useRef, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { DealCard } from "@/features/deals/components/DealCard";
import { DealPagination } from "@/features/deals/components/DealPagination";
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
import { visitBaseline } from "@/lib/lastVisit";

const PAGE_SIZE = 30;

interface HomeSearch {
  page?: number;
}

/** La portada lista siempre los chollos más nuevos: con la comunidad
 *  arrancando, «Más populares» (temperatura) no aportaba nada. Un `?sort=`
 *  antiguo se ignora y el canonical ya apuntaba a la URL sin orden. */
function parseHomeSearch(search: Record<string, unknown>): HomeSearch {
  const parsedPage = Number(search.page);
  const page = Number.isSafeInteger(parsedPage) && parsedPage >= 2 ? parsedPage : undefined;
  return { page };
}

function toHomeSearch(page: number): HomeSearch {
  return { page: page === 1 ? undefined : page };
}

/** URL rastreable de una página del feed. */
function homeHref(page: number): string {
  return page === 1 ? "/" : `/?page=${page}`;
}

export const Route = createFileRoute("/")({
  component: HomePage,
  validateSearch: parseHomeSearch,
  loaderDeps: ({ search }) => ({ page: search.page ?? 1 }),
  loader: async ({ deps }) => {
    const [page, tops, posts] = await Promise.all([
      withFallback(
        dealsService.getPage({ sort: "recent", page: deps.page, page_size: PAGE_SIZE }),
        { items: [], total_pages: 1, page: 1, page_size: PAGE_SIZE, total: 0 },
        "Error cargando chollos de portada",
      ),
      withFallback(loadBannerTops(), [], "Error cargando tops de portada"),
      withFallback(
        blogService.getPosts({ page_size: 3 }).then((result) => result.items),
        [],
        "Error cargando artículos del blog",
      ),
    ]);
    // La hora se fija en el loader para que servidor y cliente elijan el mismo hero.
    return { ...page, posts, tops, now: Date.now() };
  },
  head: ({ loaderData }) =>
    pageHead(homeSeo({ page: loaderData?.page ?? 1, deals: loaderData?.items ?? [] })),
});

function HomePage() {
  const { user } = useAuth();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const page = search.page ?? 1;
  const data = Route.useLoaderData();
  const deals = data.items;
  const totalPages = data.total_pages;
  const currentPage = data.page;
  const [favIds, setFavIds] = useState<Set<string>>(new Set());
  // Separador «lo nuevo desde tu última visita»: solo en el navegador (tras montar).
  const [baseline, setBaseline] = useState<Date | null>(null);
  useEffect(() => setBaseline(visitBaseline()), []);
  const firstSeenIndex =
    baseline && currentPage === 1
      ? deals.findIndex((d) => new Date(d.published_at).getTime() <= baseline.getTime())
      : -1;
  const dealsHeadingRef = useRef<HTMLHeadingElement>(null);
  const campaign = campaignStatus(BLACK_FRIDAY, new Date(data.now));

  useEffect(() => {
    if (currentPage !== page) {
      void navigate({ search: toHomeSearch(currentPage), replace: true });
    }
  }, [currentPage, navigate, page]);

  const changePage = (nextPage: number) => {
    if (nextPage < 1 || nextPage > totalPages || nextPage === currentPage) return;
    void navigate({ search: toHomeSearch(nextPage) });
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
        <div className="home-content-layout">
          <div className="home-feed-column">
            <section aria-labelledby="home-deals-heading">
              <h2 ref={dealsHeadingRef} id="home-deals-heading" className="sr-only">
                Últimos chollos
              </h2>
              <div className="deal-feed-grid">
                {deals.map((d, index) => (
                  <Fragment key={d.id}>
                    {index > 0 && index === firstSeenIndex && (
                      <div className="feed-new-divider" role="separator">
                        <span>Hasta aquí, lo nuevo desde tu última visita</span>
                      </div>
                    )}
                    <DealCard
                      deal={d}
                      isFavorite={favIds.has(d.id)}
                      imageLoading={index < 3 ? "eager" : "lazy"}
                    />
                  </Fragment>
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
                  hrefForPage={homeHref}
                />
              </div>
            )}
          </div>
          <HomeSidebar posts={data.posts} />
        </div>
        {currentPage === 1 && <SiteFaq />}
      </div>
    </Layout>
  );
}
