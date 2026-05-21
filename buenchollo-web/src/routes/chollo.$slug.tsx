import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { dealsService, type DealDetailData } from "@/services/api/deals";
import { supabase } from "@/integrations/supabase/client";
import { Layout } from "@/components/Layout";
import { DealCard, type DealCardData } from "@/components/DealCard";
import { Comments } from "@/components/Comments";
import { ShareBox } from "@/components/ShareBox";
import { useAuth } from "@/hooks/useAuth";
import { formatPrice, formatRelativeTime } from "@/lib/format";
import { Heart, Flame, ExternalLink, ArrowUp, ArrowDown, MessageSquare, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";

const SITE = "https://buenchollotech.lovable.app";

export const Route = createFileRoute("/chollo/$slug")({
  component: DealDetail,
  loader: async ({ params }) => {
    try {
      const data = await dealsService.getBySlug(params.slug);
      return { meta: data };
    } catch {
      return { meta: null };
    }
  },
  head: ({ params, loaderData }) => {
    const m: any = loaderData?.meta;
    const url = `${SITE}/chollo/${params.slug}`;
    if (!m) {
      return {
        meta: [
          { title: `${params.slug} · BuencholloTech` },
          { property: "og:url", content: url },
        ],
        links: [{ rel: "canonical", href: url }],
      };
    }
    const desc =
      (m.short_description || (m.description ? String(m.description).slice(0, 200) : "")) +
      (m.current_price ? ` · ${m.current_price}€` : "");
    const img = (m.images && m.images[0]) || m.image_url || undefined;
    const title = `${m.title} — ${m.current_price ? `${m.current_price}€` : "Chollo"} · BuencholloTech`;
    return {
      meta: [
        { title },
        { name: "description", content: desc.slice(0, 200) },
        { property: "og:title", content: m.title },
        { property: "og:description", content: desc.slice(0, 200) },
        { property: "og:url", content: url },
        { property: "og:type", content: "product" },
        ...(img ? [{ property: "og:image", content: img }, { name: "twitter:image", content: img }] : []),
      ],
      links: [{ rel: "canonical", href: url }],
      scripts: [
        {
          type: "application/ld+json",
          children: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Product",
            name: m.title,
            description: m.short_description || m.description || undefined,
            image: img,
            offers: {
              "@type": "Offer",
              price: m.current_price,
              priceCurrency: "EUR",
              availability: "https://schema.org/InStock",
              url,
              seller: m.store?.name ? { "@type": "Organization", name: m.store.name } : undefined,
            },
          }),
        },
      ],
    };
  },
});

function DealDetail() {
  const { slug } = Route.useParams();
  const { user, isAdmin } = useAuth();
  const [deal, setDeal] = useState<DealDetailData | null>(null);
  const [related, setRelated] = useState<DealCardData[]>([]);
  const [commentCount, setCommentCount] = useState(0);
  const [myVote, setMyVote] = useState<number>(0);
  const [votingLoading, setVotingLoading] = useState(false);
  const [fav, setFav] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeImg, setActiveImg] = useState(0);

  const load = async () => {
    setLoading(true);
    try {
      const data = await dealsService.getBySlug(slug);
      setDeal(data);

      const rel = await dealsService.search({ category_id: data.category?.slug, limit: 5 });
      setRelated(rel.filter(d => d.id !== data.id).slice(0, 4));
      setCommentCount(data.comment_count ?? 0);

      if (user) {
        const [myVoteVal, { data: f }] = await Promise.all([
          dealsService.getMyVote(data.id).catch(() => 0),
          supabase.from("favorites").select("id").eq("deal_id", data.id).eq("user_id", user.id).maybeSingle(),
        ]);
        setMyVote(myVoteVal);
        setFav(!!f);
      }
      setLoading(false);
    } catch (error) {
      console.error(error);
      setLoading(false);
      return;
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [slug, user?.id]);

  const vote = async (v: number) => {
    if (!user) { toast.error("Inicia sesión para votar"); return; }
    if (!deal || votingLoading) return;
    setVotingLoading(true);
    try {
      const result = await dealsService.vote(deal.id, v as 1 | -1);
      setMyVote(result.my_vote);
      setDeal((d: any) => ({ ...d, temperature: result.temperature, votes_up: result.votes_up, votes_down: result.votes_down }));
    } catch (e: any) {
      toast.error(e?.message ?? "Error al votar");
    } finally {
      setVotingLoading(false);
    }
  };

  const toggleFav = async () => {
    if (!user) { toast.error("Inicia sesión para guardar"); return; }
    if (!deal) return;
    if (fav) { await supabase.from("favorites").delete().eq("user_id", user.id).eq("deal_id", deal.id); setFav(false); }
    else { await supabase.from("favorites").insert({ user_id: user.id, deal_id: deal.id }); setFav(true); }
  };

  const trackClick = async () => {
    if (!deal) return;
    await supabase.from("deals").update({ click_count: (deal.click_count ?? 0) + 1 }).eq("id", deal.id);
  };

  if (loading) return <Layout><div className="max-w-7xl mx-auto p-8 font-mono text-sm">CARGANDO...</div></Layout>;
  if (!deal) return <Layout><div className="max-w-7xl mx-auto p-8 text-center"><h1 className="text-2xl font-bold mb-2">Chollo no encontrado</h1><Link to="/explorar" className="text-cyan-glow font-mono text-xs">[ EXPLORAR CHOLLOS ]</Link></div></Layout>;

  // Estados ocultos al público
  const isExpired = deal.status === "expired";
  const isDraft = deal.status === "draft";
  const isScheduled = deal.status === "scheduled";
  if ((isDraft || isScheduled) && !isAdmin) {
    return <Layout><div className="max-w-7xl mx-auto p-8 text-center"><h1 className="text-2xl font-bold mb-2">Este chollo no está disponible</h1><Link to="/explorar" className="text-cyan-glow font-mono text-xs">[ EXPLORAR CHOLLOS ]</Link></div></Layout>;
  }

  const discount = deal.discount_percentage ?? (deal.previous_price ? Math.round((1 - deal.current_price / deal.previous_price) * 100) : null);

  const fmtDateTime = (s: string) => new Date(s).toLocaleString("es-ES", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <nav className="font-mono text-xs text-muted-foreground mb-4 flex flex-wrap gap-x-1 gap-y-1">
          <Link to="/" className="hover:text-cyan-glow">INICIO</Link> /{" "}
          <Link to="/explorar" className="hover:text-cyan-glow">EXPLORAR</Link>
          {deal.category && <> / <Link to="/categoria/$slug" params={{ slug: deal.category.slug }} className="hover:text-cyan-glow">{deal.category.name.toUpperCase()}</Link></>}
          {deal.subcategory && <> / <Link to="/explorar" search={{ cat: deal.category?.slug, sub: deal.subcategory.slug } as any} className="hover:text-cyan-glow">{deal.subcategory.name.toUpperCase()}</Link></>}
        </nav>

        {/* Avisos de estado */}
        {isExpired && (
          <div className="mb-4 bg-alert-red/10 border border-alert-red/40 text-alert-red px-4 py-3 font-mono text-xs uppercase flex items-center gap-2">
            <AlertCircle className="size-4" /> Esta oferta ha caducado{deal.expires_at && <> el {fmtDateTime(deal.expires_at)}</>} · Es posible que el precio o la disponibilidad hayan cambiado.
          </div>
        )}
        {isDraft && isAdmin && (
          <div className="mb-4 bg-surface-700 border border-surface-600 text-foreground px-4 py-3 font-mono text-xs uppercase flex items-center gap-2">
            <AlertCircle className="size-4" /> Vista previa · Esta publicación está en BORRADOR y no es visible para el público.
          </div>
        )}
        {isScheduled && isAdmin && (
          <div className="mb-4 bg-amber-500/10 border border-amber-500/40 text-amber-400 px-4 py-3 font-mono text-xs uppercase flex items-center gap-2">
            <AlertCircle className="size-4" /> Programado · Se publicará automáticamente el {(deal as any).scheduled_for ? fmtDateTime((deal as any).scheduled_for) : "—"}.
          </div>
        )}

        <div className={`grid lg:grid-cols-2 gap-8 ${isExpired ? "opacity-90" : ""}`}>
          <div>
            {(() => {
              const gallery: string[] = (deal.images && deal.images.length > 0 ? deal.images : (deal.image_url ? [deal.image_url] : [])).filter(Boolean);
              const current = gallery[activeImg] ?? gallery[0];
              return (
                <>
                  <div className={`relative bg-surface-800 border border-surface-700 aspect-[4/3] overflow-hidden ${isExpired ? "grayscale" : ""}`}>
                    {current && <img src={current} alt={deal.title} className="w-full h-full object-cover" />}
                    {isExpired && (
                      <div className="absolute inset-0 bg-surface-900/60 flex items-center justify-center">
                        <span className="bg-alert-red text-white font-mono font-bold text-sm px-4 py-2 -rotate-6 border-2 border-white/40">CHOLLO CADUCADO</span>
                      </div>
                    )}
                  </div>
                  {gallery.length > 1 && (
                    <div className="grid grid-cols-5 gap-2 mt-2">
                      {gallery.map((src, i) => (
                        <button key={src + i} onClick={() => setActiveImg(i)}
                          className={`aspect-square bg-surface-800 border overflow-hidden transition ${isExpired ? "grayscale" : ""} ${i === activeImg ? "border-cyan-glow" : "border-surface-700 hover:border-surface-600"}`}>
                          <img src={src} alt="" className="w-full h-full object-cover" />
                        </button>
                      ))}
                    </div>
                  )}
                </>
              );
            })()}
          </div>

          <div>
            <div className="flex items-center gap-3 mb-3 font-mono text-xs">
              <span className="text-cyan-glow">@{deal.store?.slug?.toUpperCase()}</span>
              <span className="text-muted-foreground">{formatRelativeTime(deal.published_at)}</span>
            </div>
            <h1 className={`text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight mb-4 ${isExpired ? "text-muted-foreground" : ""}`}>{deal.title}</h1>
            {deal.short_description && <p className="text-muted-foreground mb-6">{deal.short_description}</p>}

            <div className={`bg-surface-800 border p-5 mb-5 ${isExpired ? "border-alert-red/30" : "border-surface-700"}`}>
              <div className="flex items-end gap-3 mb-3">
                <span className={`font-mono text-4xl sm:text-5xl font-extrabold tabular-nums leading-none ${isExpired ? "text-muted-foreground line-through" : "text-cyan-glow"}`}>{formatPrice(deal.current_price)}</span>
                {deal.previous_price && (
                  <>
                    <span className="font-mono text-sm text-muted-foreground line-through pb-1">{formatPrice(deal.previous_price)}</span>
                    {discount && <span className="bg-alert-red text-white font-mono font-bold text-xs px-2 py-1 mb-1">-{discount}%</span>}
                  </>
                )}
              </div>
              {deal.shipping_info && <p className="text-xs font-mono text-muted-foreground mb-3">📦 {deal.shipping_info}</p>}

              {/* Fecha de fin de oferta destacada */}
              {deal.expires_at && !isExpired && (
                <div className="mb-4 bg-surface-900 border-l-2 border-amber-400 px-3 py-2 font-mono text-xs">
                  <span className="text-amber-400 uppercase">⏱ Termina:</span> <span className="text-foreground font-bold">{fmtDateTime(deal.expires_at)}</span>
                </div>
              )}

              {isExpired ? (
                <div className="w-full inline-flex items-center justify-center gap-2 bg-surface-700 text-muted-foreground font-mono text-sm font-bold py-4 cursor-not-allowed">
                  [ OFERTA CADUCADA ]
                </div>
              ) : (
                <a href={deal.affiliate_url ?? undefined} target="_blank" rel="noopener nofollow" onClick={trackClick}
                  className="w-full inline-flex items-center justify-center gap-2 bg-cyan-glow text-surface-900 font-mono text-sm font-bold py-4 hover:bg-foreground transition-colors">
                  [ IR A LA OFERTA ] <ExternalLink className="size-4" />
                </a>
              )}
              <p className="flex items-start gap-2 text-[10px] font-mono text-muted-foreground mt-3 leading-relaxed">
                <AlertCircle className="size-3 shrink-0 mt-0.5" /> Enlace de afiliado. Si compras a través de él, recibimos una pequeña comisión sin coste para ti.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <button onClick={() => vote(1)} disabled={votingLoading} className={`flex items-center gap-2 border px-3 py-2 font-mono text-xs disabled:opacity-50 ${myVote === 1 ? "border-cyan-glow text-cyan-glow bg-cyan-glow/10" : "border-surface-700 hover:border-cyan-glow"}`}>
                <ArrowUp className="size-4" /> {deal.votes_up}
              </button>
              <button onClick={() => vote(-1)} disabled={votingLoading} className={`flex items-center gap-2 border px-3 py-2 font-mono text-xs disabled:opacity-50 ${myVote === -1 ? "border-alert-red text-alert-red bg-alert-red/10" : "border-surface-700 hover:border-alert-red"}`}>
                <ArrowDown className="size-4" /> {deal.votes_down}
              </button>
              <div className="flex items-center gap-2 border border-surface-700 px-3 py-2 font-mono text-xs">
                <Flame className="size-4 text-alert-red" /> {deal.temperature}°
              </div>
              <button onClick={toggleFav} className={`flex items-center gap-2 border px-3 py-2 font-mono text-xs ${fav ? "border-cyan-glow text-cyan-glow bg-cyan-glow/10" : "border-surface-700 hover:border-cyan-glow"}`}>
                <Heart className={`size-4 ${fav ? "fill-current" : ""}`} /> {deal.favorite_count}
              </button>
              <div className="flex items-center gap-2 border border-surface-700 px-3 py-2 font-mono text-xs">
                <MessageSquare className="size-4" /> {commentCount}
              </div>
            </div>

            {deal.description && (
              <div className="mt-6 bg-surface-800 border border-surface-700 p-5">
                <h2 className="font-mono text-xs uppercase text-cyan-glow mb-4">Descripción</h2>
                <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-p:text-foreground/90 prose-li:text-foreground/90">
                  <ReactMarkdown>{deal.description}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </div>

        <ShareBox url={`/chollo/${deal.slug}`} title={deal.title} price={deal.current_price} />

        <Comments dealId={deal.id} onCountChange={async () => {
          const { data } = await supabase.from("deals").select("comment_count").eq("id", deal.id).single();
          if (data) setCommentCount(data.comment_count ?? 0);
        }} />

        {related.length > 0 && (
          <section className="mt-12">
            <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4 border-b border-surface-700 pb-2">Chollos relacionados</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {related.map((d: any) => <DealCard key={d.id} deal={d} />)}
            </div>
          </section>
        )}
      </div>
    </Layout>
  );
}
