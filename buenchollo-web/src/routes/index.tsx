import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Layout } from "@/components/Layout";
import { DealCard, type DealCardData } from "@/components/DealCard";
import { useAuth } from "@/hooks/useAuth";
import { ArrowRight, Bell, Sparkles, Smartphone, Laptop, Headphones, Tv, Gamepad2, Cpu, Home as HomeIcon, Watch, HardDrive, Keyboard, Camera, Router, BatteryCharging, Send, Zap } from "lucide-react";

const TELEGRAM_URL = "https://t.me/buenchollotech";

const SITE = "https://buenchollotech.lovable.app";

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

const ICONS: Record<string, any> = {
  smartphone: Smartphone, laptop: Laptop, headphones: Headphones, tv: Tv,
  "gamepad-2": Gamepad2, cpu: Cpu, home: HomeIcon, watch: Watch,
  "hard-drive": HardDrive, keyboard: Keyboard, camera: Camera, router: Router,
  "battery-charging": BatteryCharging,
};

function HomePage() {
  const { user } = useAuth();
  const [latest, setLatest] = useState<DealCardData[]>([]);
  const [popular, setPopular] = useState<DealCardData[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [favIds, setFavIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const load = async () => {
      const sel = "id,title,slug,image_url,images,current_price,previous_price,discount_percentage,temperature,published_at,store:stores(name,slug),category:categories!deals_category_id_fkey(name,slug)";
      const [{ data: latestData }, { data: popularData }, { data: catData }] = await Promise.all([
        supabase.from("deals").select(sel).eq("status", "active").order("published_at", { ascending: false }).limit(8),
        supabase.from("deals").select(sel).eq("status", "active").order("temperature", { ascending: false }).limit(4),
        supabase.from("categories").select("id,name,slug,icon").is("parent_id", null).eq("is_active", true).order("display_order"),
      ]);
      setLatest((latestData ?? []) as any);
      setPopular((popularData ?? []) as any);
      setCategories(catData ?? []);
    };
    load();
  }, []);

  useEffect(() => {
    if (!user) { setFavIds(new Set()); return; }
    supabase.from("favorites").select("deal_id").eq("user_id", user.id)
      .then(({ data }) => setFavIds(new Set((data ?? []).map(f => f.deal_id))));
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
            <Link to="/explorar" className="inline-flex items-center gap-2 bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-5 py-3 hover:bg-foreground transition-colors">
              [ EXPLORAR CHOLLOS ] <ArrowRight className="size-4" />
            </Link>
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

      {/* CATEGORÍAS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="flex items-center justify-between border-b border-surface-700 pb-3 mb-6">
          <h2 className="text-foreground font-bold text-lg tracking-tight font-mono">CATEGORÍAS_DESTACADAS</h2>
          <Link to="/categorias" className="font-mono text-xs text-cyan-glow hover:text-foreground">[ VER TODAS ]</Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {categories.map(c => {
            const Icon = ICONS[c.icon] ?? Sparkles;
            return (
              <Link key={c.id} to="/categoria/$slug" params={{ slug: c.slug }}
                className="group bg-surface-800 border border-surface-700 hover:border-cyan-glow p-4 flex flex-col items-center gap-2 transition-all hover:glow-cyan">
                <Icon className="size-6 text-cyan-glow group-hover:scale-110 transition-transform" />
                <span className="text-xs font-mono uppercase text-center text-muted-foreground group-hover:text-foreground transition-colors">{c.name}</span>
              </Link>
            );
          })}
        </div>
      </section>

      {/* MÁS POPULARES */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between border-b border-surface-700 pb-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="size-2 bg-alert-red rounded-full animate-pulse" />
            <h2 className="text-foreground font-bold text-lg tracking-tight font-mono">MÁS_POPULARES</h2>
          </div>
          <Link to="/explorar" search={{ sort: "popular" } as any} className="font-mono text-xs text-cyan-glow hover:text-foreground">[ VER MÁS ]</Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {popular.map(d => <DealCard key={d.id} deal={d} isFavorite={favIds.has(d.id)} />)}
        </div>
      </section>

      {/* ÚLTIMAS OFERTAS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between border-b border-surface-700 pb-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="size-2 bg-cyan-glow rounded-full animate-pulse" />
            <h2 className="text-foreground font-bold text-lg tracking-tight font-mono">TRANSMISIÓN_EN_VIVO</h2>
          </div>
          <span className="font-mono text-xs text-muted-foreground hidden sm:block">ACTUALIZANDO...</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {latest.map(d => <DealCard key={d.id} deal={d} isFavorite={favIds.has(d.id)} />)}
        </div>
      </section>

      {/* CTA ALERTAS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="bg-surface-800 border-l-4 border-cyan-glow border-y border-r border-surface-700 p-8 sm:p-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-glow/10 blur-[100px] pointer-events-none" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <Bell className="size-5 text-cyan-glow" />
              <h3 className="text-2xl font-bold text-foreground tracking-tight">Configura tu radar de precios</h3>
            </div>
            <p className="text-muted-foreground max-w-xl">
              Define qué te interesa (marca, categoría, precio máximo) y te avisamos cuando aparezca un chollo que cumpla tus criterios.
            </p>
          </div>
          <Link
            to={user ? "/alertas/nueva" : "/registro"}
            className="relative z-10 inline-flex items-center gap-2 bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-6 py-3 hover:bg-foreground transition-colors whitespace-nowrap"
          >
            [ {user ? "CREAR ALERTA" : "EMPEZAR GRATIS"} ] <ArrowRight className="size-4" />
          </Link>
        </div>
      </section>
    </Layout>
  );
}
