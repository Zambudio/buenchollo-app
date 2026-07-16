import { logError } from "@/lib/logger";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { DealCard, type DealCardData } from "@/features/deals/components/DealCard";
import { useAuth } from "@/hooks/useAuth";
import { ArrowRight } from "lucide-react";
import { dealsService, favoritesApi } from "@/services/api/deals";

const SITE = "https://buenchollotech.com";
const LIVE_LIMIT = 8;

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

function HomePage() {
  const { user } = useAuth();
  const [popular, setPopular] = useState<DealCardData[]>([]);
  const [latest, setLatest] = useState<DealCardData[]>([]);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveHasMore, setLiveHasMore] = useState(true);
  const [favIds, setFavIds] = useState<Set<string>>(new Set());

  // Refs para evitar stale closures en el IntersectionObserver
  const offsetRef = useRef(0);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);
  const sentinelRef = useRef<HTMLDivElement>(null);

  const loadLive = useCallback(async () => {
    if (loadingRef.current || !hasMoreRef.current) return;
    loadingRef.current = true;
    setLiveLoading(true);
    try {
      const data = await dealsService.search({ limit: LIVE_LIMIT, offset: offsetRef.current });
      setLatest((prev) => [...prev, ...data]);
      offsetRef.current += data.length;
      if (data.length < LIVE_LIMIT) {
        hasMoreRef.current = false;
        setLiveHasMore(false);
      }
    } catch {
      // silent — no bloqueamos la UI por un fallo de paginación
    } finally {
      loadingRef.current = false;
      setLiveLoading(false);
    }
  }, []);

  // Carga inicial: populares + primera página de live
  useEffect(() => {
    dealsService
      .getPopular(4)
      .then(setPopular)
      .catch((error) => logError("Error cargando chollos populares", error));
    loadLive();
  }, [loadLive]);

  // IntersectionObserver para scroll infinito
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadLive();
      },
      { rootMargin: "300px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [loadLive]);

  // Favoritos del usuario
  useEffect(() => {
    if (!user) {
      setFavIds(new Set());
      return;
    }
    favoritesApi
      .getFavorites()
      .then((deals) => setFavIds(new Set(deals.map((d) => d.id))))
      .catch(() => setFavIds(new Set()));
  }, [user]);

  return (
    <Layout>
      {/* HERO */}
      <section className="border-b border-surface-700 bg-surface-900 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-glow/5 blur-[120px] pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 sm:py-20 relative">
          <div className="font-mono text-cyan-glow text-xs tracking-[0.2em] mb-5">
            &gt; SELECCIÓN DIARIA DE OFERTAS
          </div>
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold text-foreground tracking-tighter leading-[1.02] mb-6">
            Chollos en <span className="text-cyan-glow text-glow">tecnología</span>
          </h1>
          <p className="text-muted-foreground text-base sm:text-xl max-w-2xl leading-relaxed">
            Seleccionamos y comparamos ofertas para que encuentres el mejor precio.
          </p>
        </div>
      </section>

      {/* MÁS POPULARES */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between border-b border-surface-700 pb-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="size-2 bg-alert-red rounded-full animate-pulse" />
            <h2 className="text-foreground font-bold text-lg tracking-tight font-mono">
              MÁS_POPULARES
            </h2>
          </div>
          <Link
            to="/explorar"
            search={{ sort: "popular" }}
            className="font-mono text-xs text-cyan-glow hover:text-foreground"
          >
            [ VER MÁS ]
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {popular.map((d) => (
            <DealCard key={d.id} deal={d} isFavorite={favIds.has(d.id)} />
          ))}
        </div>
      </section>

      {/* TRANSMISIÓN EN VIVO — scroll infinito */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between border-b border-surface-700 pb-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="size-2 bg-cyan-glow rounded-full animate-pulse" />
            <h2 className="text-foreground font-bold text-lg tracking-tight font-mono">
              TRANSMISIÓN_EN_VIVO
            </h2>
          </div>
          <Link
            to="/explorar"
            className="inline-flex items-center gap-2 bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 hover:bg-foreground transition-colors"
          >
            [ EXPLORAR CHOLLOS ] <ArrowRight className="size-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {latest.map((d) => (
            <DealCard key={d.id} deal={d} isFavorite={favIds.has(d.id)} />
          ))}
        </div>

        {/* Sentinel — dispara la carga del siguiente lote */}
        <div ref={sentinelRef} className="h-1" />

        {liveLoading && (
          <div className="py-8 text-center font-mono text-xs text-muted-foreground animate-pulse">
            CARGANDO...
          </div>
        )}

        {!liveHasMore && latest.length > 0 && (
          <div className="py-8 text-center font-mono text-xs text-muted-foreground border-t border-surface-700 mt-6">
            — FIN DE LA TRANSMISIÓN —
          </div>
        )}
      </section>
    </Layout>
  );
}
