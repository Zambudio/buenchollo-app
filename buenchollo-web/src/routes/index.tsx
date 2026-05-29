import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Layout } from "@/components/Layout";
import { DealCard, type DealCardData } from "@/components/DealCard";
import { useAuth } from "@/hooks/useAuth";
import { ArrowRight, Send, Zap } from "lucide-react";
import { dealsService, favoritesApi } from "@/services/api/deals";

const TELEGRAM_URL = "https://t.me/buenchollotech";
const SITE = "https://buenchollotech.lovable.app";
const LIVE_LIMIT = 8;

export const Route = createFileRoute("/")({
  component: HomePage,
  head: () => ({
    meta: [
      { title: "BuencholloTech — Chollos y ofertas de tecnología en España" },
      { name: "description", content: "Chollos curados de tecnología: móviles, portátiles, audio, TV, gaming y más. Alertas personalizadas y comunidad. Las mejores ofertas en un solo lugar." },
      { property: "og:title", content: "BuencholloTech — Chollos y ofertas de tecnología en España" },
      { property: "og:description", content: "Chollos curados de tecnología: móviles, portátiles, audio, TV, gaming y más. Alertas personalizadas y comunidad." },
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
    dealsService.getPopular(4).then(setPopular).catch(console.error);
    loadLive();
  }, [loadLive]);

  // IntersectionObserver para scroll infinito
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => { if (entries[0]?.isIntersecting) loadLive(); },
      { rootMargin: "300px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [loadLive]);

  // Favoritos del usuario
  useEffect(() => {
    if (!user) { setFavIds(new Set()); return; }
    favoritesApi.getFavorites()
      .then((deals) => setFavIds(new Set(deals.map((d) => d.id))))
      .catch(() => setFavIds(new Set()));
  }, [user]);

  return (
    <Layout>
      {/* HERO */}
      <section className="border-b border-surface-700 bg-surface-900 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-glow/5 blur-[120px] pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 sm:py-20 relative">
          <div className="font-mono text-cyan-glow text-xs mb-4 animate-pulse">&gt; CONEXIÓN ESTABLECIDA · MONITOREANDO NODOS</div>
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold text-foreground tracking-tighter leading-[1.05] mb-6">
            INTERCEPTANDO<br />
            <span className="text-cyan-glow text-glow">CAÍDAS DE PRECIO</span>
          </h1>
          <p className="text-muted-foreground text-base sm:text-lg max-w-2xl mb-8">
            Las mejores ofertas de tecnología, monitorizadas en tiempo real. Sin spam, sin ruido — solo chollos que merecen tu atención.
          </p>
          <div className="flex flex-wrap gap-3">
            {!user && (
              <Link to="/registro" className="inline-flex items-center gap-2 border border-surface-700 bg-surface-800 text-foreground font-mono text-xs font-bold px-5 py-3 hover:border-cyan-glow hover:text-cyan-glow transition-colors">
                [ CREAR CUENTA ]
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* TELEGRAM BANNER */}
      <section className="border-b border-surface-700 bg-surface-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="relative overflow-hidden border border-surface-700 hover:border-cyan-glow transition-colors bg-gradient-to-r from-surface-900 via-surface-800 to-surface-900 p-5 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5">
            <div className="absolute -left-8 -top-8 w-40 h-40 bg-cyan-glow/10 blur-[80px] pointer-events-none" />
            <div className="flex items-start sm:items-center gap-4 relative z-10">
              <div className="shrink-0 size-12 sm:size-14 bg-cyan-glow/10 border border-cyan-glow/40 flex items-center justify-center">
                <Send className="size-6 sm:size-7 text-cyan-glow" strokeWidth={2.2} />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Zap className="size-3.5 text-cyan-glow" />
                  <span className="font-mono text-[10px] sm:text-xs text-cyan-glow uppercase tracking-wider">Canal oficial · Notificaciones al instante</span>
                </div>
                <h2 className="text-foreground font-bold text-base sm:text-lg tracking-tight leading-snug">
                  También publicamos los chollos en <span className="text-cyan-glow">Telegram</span>
                </h2>
                <p className="text-muted-foreground text-xs sm:text-sm mt-0.5">
                  Únete al canal y no te pierdas ninguna oferta — directo a tu móvil.
                </p>
              </div>
            </div>
            <a
              href={TELEGRAM_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="relative z-10 inline-flex items-center gap-2 bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-5 py-3 hover:bg-foreground transition-colors whitespace-nowrap w-full sm:w-auto justify-center"
            >
              <Send className="size-4" />
              [ UNIRME AL CANAL ]
            </a>
          </div>
        </div>
      </section>

      {/* MÁS POPULARES */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between border-b border-surface-700 pb-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="size-2 bg-alert-red rounded-full animate-pulse" />
            <h2 className="text-foreground font-bold text-lg tracking-tight font-mono">MÁS_POPULARES</h2>
          </div>
          <Link to="/explorar" search={{ sort: "popular" }} className="font-mono text-xs text-cyan-glow hover:text-foreground">[ VER MÁS ]</Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {popular.map((d) => <DealCard key={d.id} deal={d} isFavorite={favIds.has(d.id)} />)}
        </div>
      </section>

      {/* TRANSMISIÓN EN VIVO — scroll infinito */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between border-b border-surface-700 pb-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="size-2 bg-cyan-glow rounded-full animate-pulse" />
            <h2 className="text-foreground font-bold text-lg tracking-tight font-mono">TRANSMISIÓN_EN_VIVO</h2>
          </div>
          <Link
            to="/explorar"
            className="inline-flex items-center gap-2 bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 hover:bg-foreground transition-colors"
          >
            [ EXPLORAR CHOLLOS ] <ArrowRight className="size-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {latest.map((d) => <DealCard key={d.id} deal={d} isFavorite={favIds.has(d.id)} />)}
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
