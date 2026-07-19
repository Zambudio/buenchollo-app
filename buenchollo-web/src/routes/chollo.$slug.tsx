import { logError } from "@/lib/logger";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { dealsService, favoritesApi, type DealDetailData } from "@/services/api/deals";
import { Layout } from "@/components/layout/Layout";
import { DealCard, type DealCardData } from "@/features/deals/components/DealCard";
import { useMyVotes } from "@/features/deals/hooks/useMyVotes";
import { Comments } from "@/features/deals/components/Comments";
import { ShareDialog } from "@/features/deals/components/ShareBox";
import { DealVoteControl } from "@/features/deals/components/DealVoteControl";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  type CarouselApi,
} from "@/components/ui/carousel";
import { useAuth } from "@/hooks/useAuth";
import { formatPrice, formatRelativeTime, calculateDiscount } from "@/lib/format";
import { errorMessage } from "@/lib/errors";
import {
  Heart,
  ExternalLink,
  MessageSquare,
  Share2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  X,
  Pencil,
} from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";

const SITE = "https://buenchollotech.com";

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
    const m = loaderData?.meta as DealDetailData | null | undefined;
    const url = `${SITE}/chollo/${params.slug}`;
    if (!m) {
      return {
        meta: [{ title: `${params.slug} · BuenChollo Tech` }, { property: "og:url", content: url }],
        links: [{ rel: "canonical", href: url }],
      };
    }
    const desc =
      (m.short_description || (m.description ? String(m.description).slice(0, 200) : "")) +
      (m.current_price ? ` · ${m.current_price}€` : "");
    const img = (m.images && m.images[0]) || m.image_url || undefined;
    const title = `${m.title} — ${m.current_price ? `${m.current_price}€` : "Chollo"} · BuenChollo Tech`;
    return {
      meta: [
        { title },
        { name: "description", content: desc.slice(0, 200) },
        { property: "og:title", content: m.title },
        { property: "og:description", content: desc.slice(0, 200) },
        { property: "og:url", content: url },
        { property: "og:type", content: "product" },
        ...(img
          ? [
              { property: "og:image", content: img },
              { name: "twitter:image", content: img },
            ]
          : []),
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
  const loaderData = Route.useLoaderData();
  const { user, isAdmin } = useAuth();
  const [deal, setDeal] = useState<DealDetailData | null>(
    (loaderData?.meta as DealDetailData | null) ?? null,
  );
  const [related, setRelated] = useState<DealCardData[]>([]);
  const [commentCount, setCommentCount] = useState(0);
  const [myVote, setMyVote] = useState<number>(0);
  const [votingLoading, setVotingLoading] = useState(false);
  const [fav, setFav] = useState(false);
  const [loading, setLoading] = useState(!loaderData?.meta);
  const [activeImg, setActiveImg] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [relatedApi, setRelatedApi] = useState<CarouselApi>();
  const [relatedCanPrev, setRelatedCanPrev] = useState(false);
  const [relatedCanNext, setRelatedCanNext] = useState(false);
  const relatedVotes = useMyVotes(related.map((d) => d.id));

  useEffect(() => {
    if (!relatedApi) return;
    const onSelect = () => {
      setRelatedCanPrev(relatedApi.canScrollPrev());
      setRelatedCanNext(relatedApi.canScrollNext());
    };
    onSelect();
    relatedApi.on("select", onSelect);
    relatedApi.on("reInit", onSelect);
    return () => {
      relatedApi.off("select", onSelect);
    };
  }, [relatedApi]);

  // Efecto 1: carga los datos públicos del deal (no necesita auth).
  // Si el loader del router ya trajo el deal para este slug (SSR), lo
  // reutiliza en vez de repetir el fetch; "relacionados" ya no bloquea
  // el pintado del deal principal.
  useEffect(() => {
    let cancelled = false;
    const loadDeal = async () => {
      const dealFromLoader = loaderData?.meta as DealDetailData | null | undefined;
      setLoading(!dealFromLoader);
      try {
        const data = dealFromLoader ?? (await dealsService.getBySlug(slug));
        if (cancelled) return;
        setDeal(data);
        setCommentCount(data.comment_count ?? 0);

        if (data.category_id) {
          dealsService
            .search({ category_id: data.category_id, limit: 13 })
            .then((rel) => {
              if (cancelled) return;
              setRelated(rel.filter((d) => d.id !== data.id).slice(0, 12));
            })
            .catch((error) => logError("Error cargando chollos relacionados", error));
        }
      } catch (error) {
        logError("Error cargando el detalle del chollo", error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadDeal();
    return () => {
      cancelled = true;
    };
  }, [slug, loaderData]);

  // Efecto 2: carga el estado del usuario (voto y favorito) — solo cuando deal y user están listos
  useEffect(() => {
    if (!user || !deal) return;
    let cancelled = false;
    const loadUserState = async () => {
      const [myVoteVal, isFav] = await Promise.all([
        dealsService.getMyVote(deal.id).catch(() => 0),
        favoritesApi.check(deal.id).catch(() => false),
      ]);
      if (cancelled) return;
      setMyVote(myVoteVal);
      setFav(isFav);
    };
    loadUserState();
    return () => {
      cancelled = true;
    };
    // Reaccionamos sólo a cambios de identidad de deal/user, no a sus
    // referencias completas (que cambian en cada render por setDeal/votes).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deal?.id, user?.id]);

  const vote = async (v: number) => {
    if (!user) {
      toast.error("Inicia sesión para votar");
      return;
    }
    if (!deal || votingLoading) return;
    setVotingLoading(true);
    try {
      const result = await dealsService.vote(deal.id, v as 1 | -1);
      setMyVote(result.my_vote);
      setDeal((d) =>
        d
          ? {
              ...d,
              temperature: result.temperature,
              votes_up: result.votes_up,
              votes_down: result.votes_down,
            }
          : d,
      );
    } catch (e: unknown) {
      toast.error(errorMessage(e, "Error al votar"));
    } finally {
      setVotingLoading(false);
    }
  };

  const toggleFav = async () => {
    if (!user) {
      toast.error("Inicia sesión para guardar");
      return;
    }
    if (!deal) return;
    try {
      const result = await favoritesApi.toggle(deal.id);
      setFav(result.is_favorited);
    } catch (e: unknown) {
      toast.error(errorMessage(e, "Error al guardar el favorito"));
    }
  };

  const trackClick = async () => {
    if (!deal) return;
    try {
      await dealsService.trackClick(deal.id);
    } catch {
      /* no crítico */
    }
  };

  if (loading)
    return (
      <Layout>
        <div className="max-w-7xl mx-auto p-8 font-mono text-sm">CARGANDO...</div>
      </Layout>
    );
  if (!deal)
    return (
      <Layout>
        <div className="max-w-7xl mx-auto p-8 text-center">
          <h1 className="text-2xl font-bold mb-2">Chollo no encontrado</h1>
          <Link to="/explorar" className="text-cyan-glow font-mono text-xs">
            EXPLORAR CHOLLOS
          </Link>
        </div>
      </Layout>
    );

  // Estados ocultos al público
  const isExpired = deal.status === "expired";
  const isDraft = deal.status === "draft";
  const isScheduled = deal.status === "scheduled";
  if ((isDraft || isScheduled) && !isAdmin) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto p-8 text-center">
          <h1 className="text-2xl font-bold mb-2">Este chollo no está disponible</h1>
          <Link to="/explorar" className="text-cyan-glow font-mono text-xs">
            EXPLORAR CHOLLOS
          </Link>
        </div>
      </Layout>
    );
  }

  const discount =
    deal.discount_percentage ?? calculateDiscount(deal.current_price, deal.previous_price);

  const fmtDateTime = (s: string) =>
    new Date(s).toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <nav className="font-mono text-xs text-muted-foreground mb-4 flex flex-wrap gap-x-1 gap-y-1">
          <Link to="/" className="hover:text-cyan-glow">
            INICIO
          </Link>{" "}
          /{" "}
          <Link to="/explorar" className="hover:text-cyan-glow">
            EXPLORAR
          </Link>
          {deal.category && (
            <>
              {" "}
              /{" "}
              <Link
                to="/categoria/$slug"
                params={{ slug: deal.category.slug }}
                className="hover:text-cyan-glow"
              >
                {deal.category.name.toUpperCase()}
              </Link>
            </>
          )}
          {deal.subcategory && (
            <>
              {" "}
              /{" "}
              <Link
                to="/explorar"
                search={{ cat: deal.category?.slug, sub: deal.subcategory.slug }}
                className="hover:text-cyan-glow"
              >
                {deal.subcategory.name.toUpperCase()}
              </Link>
            </>
          )}
        </nav>

        {/* Avisos de estado */}
        {isExpired &&
          (() => {
            const deleteDate = deal.expires_at
              ? new Date(new Date(deal.expires_at).getTime() + 2 * 24 * 60 * 60 * 1000)
              : null;
            return (
              <div className="mb-4 bg-alert-red/10 border border-alert-red/40 text-alert-red px-4 py-3 font-mono text-xs uppercase flex items-center gap-2">
                <AlertCircle className="size-4" />
                <span>
                  Esta oferta ha caducado
                  {deal.expires_at && <> el {fmtDateTime(deal.expires_at)}</>} · Es posible que el
                  precio o la disponibilidad hayan cambiado.
                  {deleteDate && (
                    <>
                      {" "}
                      ·{" "}
                      <strong>
                        Esta publicación se borrará el {fmtDateTime(deleteDate.toISOString())}.
                      </strong>
                    </>
                  )}
                </span>
              </div>
            );
          })()}
        {isDraft && isAdmin && (
          <div className="mb-4 bg-surface-700 border border-surface-600 text-foreground px-4 py-3 font-mono text-xs uppercase flex items-center gap-2">
            <AlertCircle className="size-4" /> Vista previa · Esta publicación está en BORRADOR y no
            es visible para el público.
          </div>
        )}
        {isScheduled && isAdmin && (
          <div className="mb-4 bg-amber-500/10 border border-amber-500/40 text-amber-400 px-4 py-3 font-mono text-xs uppercase flex items-center gap-2">
            <AlertCircle className="size-4" /> Programado · Se publicará automáticamente el{" "}
            {deal.scheduled_for ? fmtDateTime(deal.scheduled_for) : "—"}.
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-8">
          <div>
            {(() => {
              const gallery: string[] = (
                deal.images && deal.images.length > 0
                  ? deal.images
                  : deal.image_url
                    ? [deal.image_url]
                    : []
              ).filter(Boolean);
              const current = gallery[activeImg] ?? gallery[0];
              const prev = () => setActiveImg((i) => Math.max(0, i - 1));
              const next = () => setActiveImg((i) => Math.min(gallery.length - 1, i + 1));
              return (
                <>
                  {/* Imagen principal con flechas y botón agrandar */}
                  <div className="relative bg-white border border-surface-700 aspect-[4/3] overflow-hidden flex items-center justify-center group/img">
                    {current && (
                      <img
                        src={current}
                        alt={deal.title}
                        className="w-full h-full object-contain p-4"
                      />
                    )}

                    {/* Flechas de navegación */}
                    {gallery.length > 1 && (
                      <>
                        <button
                          type="button"
                          onClick={prev}
                          disabled={activeImg === 0}
                          className="absolute left-2 top-1/2 -translate-y-1/2 bg-surface-900/80 border border-surface-600 p-1.5 hover:border-cyan-glow disabled:opacity-20 transition z-10"
                          aria-label="Foto anterior"
                        >
                          <ChevronLeft className="size-5" />
                        </button>
                        <button
                          type="button"
                          onClick={next}
                          disabled={activeImg === gallery.length - 1}
                          className="absolute right-2 top-1/2 -translate-y-1/2 bg-surface-900/80 border border-surface-600 p-1.5 hover:border-cyan-glow disabled:opacity-20 transition z-10"
                          aria-label="Foto siguiente"
                        >
                          <ChevronRight className="size-5" />
                        </button>
                      </>
                    )}

                    {/* Botón agrandar */}
                    <button
                      type="button"
                      onClick={() => setLightboxOpen(true)}
                      className="absolute bottom-2 right-2 bg-surface-900/90 border border-surface-600 px-2 py-1.5 flex items-center gap-1.5 font-mono text-[10px] uppercase hover:border-cyan-glow transition z-10"
                      aria-label="Ver imagen ampliada"
                    >
                      <Maximize2 className="size-3" /> Agrandar
                    </button>

                    {/* Contador */}
                    {gallery.length > 1 && (
                      <span className="absolute bottom-2 left-2 bg-surface-900/80 font-mono text-[10px] px-2 py-1 text-muted-foreground z-10">
                        {activeImg + 1} / {gallery.length}
                      </span>
                    )}
                  </div>

                  {/* Miniaturas */}
                  {gallery.length > 1 && (
                    <div className="grid grid-cols-6 gap-1.5 mt-2">
                      {gallery.map((src, i) => (
                        <button
                          key={src + i}
                          type="button"
                          onClick={() => setActiveImg(i)}
                          aria-label={`Ver foto ${i + 1}`}
                          className={`aspect-square bg-white border overflow-hidden transition ${i === activeImg ? "border-cyan-glow" : "border-surface-700 hover:border-surface-500"}`}
                        >
                          <img src={src} alt="" className="w-full h-full object-contain p-1" />
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Gráfica Keepa — histórico de precios */}
                  {deal.show_keepa_chart && deal.external_id && (
                    <div className="mt-3 border border-surface-700 bg-surface-900 p-3">
                      <p className="font-mono text-[10px] uppercase text-muted-foreground mb-2">
                        Histórico de precios
                      </p>
                      <img
                        src={`https://graph.keepa.com/pricehistory.png?asin=${deal.external_id}&domain=es`}
                        alt="Histórico de precios en Amazon"
                        className="w-full rounded-xl"
                        loading="lazy"
                        referrerPolicy="no-referrer"
                      />
                    </div>
                  )}

                  {/* Lightbox — estilo Amazon */}
                  {lightboxOpen && (
                    <div
                      role="dialog"
                      aria-modal="true"
                      aria-label="Visor de imágenes"
                      className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-6"
                      onClick={() => setLightboxOpen(false)}
                      onKeyDown={(e) => e.key === "Escape" && setLightboxOpen(false)}
                    >
                      <div
                        role="document"
                        className="bg-surface-900 border border-surface-700 flex w-full max-w-5xl h-[88vh] shadow-2xl"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {/* Imagen principal */}
                        <div className="relative flex-1 flex items-center justify-center overflow-hidden border-r border-surface-700 bg-white">
                          <img
                            src={current}
                            alt={deal.title}
                            className="w-full h-full object-contain p-8"
                          />
                          {gallery.length > 1 && (
                            <>
                              <button
                                type="button"
                                onClick={prev}
                                disabled={activeImg === 0}
                                aria-label="Foto anterior"
                                className="absolute left-3 top-1/2 -translate-y-1/2 bg-surface-900/90 border border-surface-600 p-2.5 hover:border-cyan-glow disabled:opacity-20 transition"
                              >
                                <ChevronLeft className="size-6" />
                              </button>
                              <button
                                type="button"
                                onClick={next}
                                disabled={activeImg === gallery.length - 1}
                                aria-label="Foto siguiente"
                                className="absolute right-3 top-1/2 -translate-y-1/2 bg-surface-900/90 border border-surface-600 p-2.5 hover:border-cyan-glow disabled:opacity-20 transition"
                              >
                                <ChevronRight className="size-6" />
                              </button>
                              <span className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-surface-900/80 font-mono text-[10px] px-2 py-1 text-muted-foreground">
                                {activeImg + 1} / {gallery.length}
                              </span>
                            </>
                          )}
                        </div>

                        {/* Panel derecho: cerrar + miniaturas */}
                        <div className="w-36 shrink-0 flex flex-col bg-surface-900">
                          <div className="flex justify-end p-2 border-b border-surface-700">
                            <button
                              type="button"
                              onClick={() => setLightboxOpen(false)}
                              aria-label="Cerrar"
                              className="p-1.5 border border-surface-600 hover:border-alert-red hover:text-alert-red transition"
                            >
                              <X className="size-4" />
                            </button>
                          </div>
                          <div className="flex-1 overflow-y-auto p-2 grid grid-cols-2 gap-1.5 content-start">
                            {gallery.map((src, i) => (
                              <button
                                key={src + i}
                                type="button"
                                onClick={() => setActiveImg(i)}
                                aria-label={`Ver foto ${i + 1}`}
                                className={`aspect-square bg-white border overflow-hidden transition ${i === activeImg ? "border-cyan-glow ring-1 ring-cyan-glow/30" : "border-surface-700 hover:border-surface-500"}`}
                              >
                                <img
                                  src={src}
                                  alt=""
                                  className="w-full h-full object-contain p-0.5"
                                />
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              );
            })()}
          </div>

          <div>
            <div className="mb-3 font-mono text-xs text-muted-foreground">
              Publicado {formatRelativeTime(deal.published_at)}
            </div>
            <h1
              className={`text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight mb-4 ${isExpired ? "text-muted-foreground" : ""}`}
            >
              {deal.title}
            </h1>
            {deal.short_description && (
              <p className="text-muted-foreground mb-6">{deal.short_description}</p>
            )}

            <div
              className={`bg-surface-800 border p-5 mb-5 ${isExpired ? "border-alert-red/30" : "border-surface-700"}`}
            >
              <div className="flex items-end gap-3 mb-3">
                <span
                  className={`font-mono text-4xl sm:text-5xl font-extrabold tabular-nums leading-none ${isExpired ? "text-muted-foreground line-through" : "text-cyan-glow"}`}
                >
                  {formatPrice(deal.current_price)}
                </span>
                {deal.previous_price && (
                  <>
                    <span className="font-mono text-sm text-muted-foreground line-through pb-1">
                      {formatPrice(deal.previous_price)}
                    </span>
                    {discount && (
                      <span className="bg-alert-red text-white font-mono font-bold text-xs px-2 py-1 mb-1">
                        -{discount}%
                      </span>
                    )}
                  </>
                )}
              </div>
              {deal.store && (
                <p className="mb-3 font-mono text-[11px] text-muted-foreground">
                  Disponible en{" "}
                  <Link
                    to="/explorar"
                    search={{ store: deal.store.id }}
                    className="font-bold text-foreground transition-colors hover:text-cyan-glow"
                  >
                    {deal.store.name}
                  </Link>
                </p>
              )}
              {deal.shipping_info && (
                <p className="text-xs font-mono text-muted-foreground mb-3">
                  📦 {deal.shipping_info}
                </p>
              )}

              {/* Fecha de fin de oferta destacada */}
              {deal.expires_at && !isExpired && (
                <div className="mb-4 bg-surface-900 border-l-2 border-amber-400 px-3 py-2 font-mono text-xs">
                  <span className="text-amber-400 uppercase">⏱ Termina:</span>{" "}
                  <span className="text-foreground font-bold">{fmtDateTime(deal.expires_at)}</span>
                </div>
              )}

              <a
                href={deal.affiliate_url ?? undefined}
                target="_blank"
                rel="noopener nofollow"
                onClick={trackClick}
                className={`w-full inline-flex items-center justify-center gap-2 rounded-full font-mono text-sm font-bold py-4 transition-colors ${
                  isExpired
                    ? "bg-surface-700 text-muted-foreground border border-alert-red/30 hover:bg-surface-600"
                    : "bg-cyan-glow text-surface-900 hover:bg-foreground"
                }`}
              >
                {isExpired ? (
                  <>
                    VER OFERTA — PUEDE HABER CADUCADO <ExternalLink className="size-4" />
                  </>
                ) : (
                  <>
                    IR A LA OFERTA <ExternalLink className="size-4" />
                  </>
                )}
              </a>
            </div>

            <div className="flex flex-wrap gap-2">
              <DealVoteControl
                temperature={deal.temperature}
                myVote={myVote}
                disabled={votingLoading}
                size="detail"
                onVote={vote}
              />
              <button
                type="button"
                onClick={toggleFav}
                aria-label={fav ? "Quitar de favoritos" : "Guardar en favoritos"}
                className={`flex items-center gap-2 border px-3 py-2 font-mono text-xs ${fav ? "border-pink-500 text-pink-500 bg-pink-500/10" : "border-surface-700 hover:border-pink-500"}`}
              >
                <Heart className={`size-4 ${fav ? "fill-current" : ""}`} />
              </button>
              <div className="flex items-center gap-2 border border-surface-700 px-3 py-2 font-mono text-xs">
                <MessageSquare className="size-4" /> {commentCount}
              </div>
              <ShareDialog
                url={`/chollo/${deal.slug}`}
                title={deal.title}
                price={deal.current_price}
                trigger={
                  <button
                    type="button"
                    aria-label="Compartir"
                    className="flex items-center gap-2 border border-surface-700 px-3 py-2 font-mono text-xs hover:border-cyan-glow hover:text-cyan-glow transition-colors"
                  >
                    <Share2 className="size-4" />
                  </button>
                }
              />
              {isAdmin && (
                <Link
                  to="/admin/chollos"
                  search={{ edit: deal.id }}
                  className="flex items-center gap-2 border border-amber-500/50 text-amber-400 px-3 py-2 font-mono text-xs hover:border-amber-400 hover:bg-amber-400/10 transition-colors"
                >
                  <Pencil className="size-4" /> EDITAR
                </Link>
              )}
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

        {related.length > 0 && (
          <section className="mt-8">
            <div className="flex items-center justify-between mb-4 border-b border-surface-700 pb-3">
              <div className="flex items-center gap-3">
                <div className="size-2 bg-cyan-glow rounded-full animate-pulse" />
                <h2 className="text-foreground font-bold text-lg tracking-tight font-mono">
                  CHOLLOS RELACIONADOS
                </h2>
              </div>
              {deal.category && (
                <Link
                  to="/categoria/$slug"
                  params={{ slug: deal.category.slug }}
                  className="font-mono text-xs text-cyan-glow hover:text-foreground shrink-0"
                >
                  VER MÁS DE {deal.category.name.toUpperCase()}
                </Link>
              )}
            </div>

            <Carousel setApi={setRelatedApi} opts={{ align: "start" }} className="px-1">
              <CarouselContent>
                {related.map((d) => (
                  <CarouselItem key={d.id} className="basis-[85%] sm:basis-1/2 lg:basis-1/4">
                    <DealCard deal={d} myVote={relatedVotes[d.id]} />
                  </CarouselItem>
                ))}
              </CarouselContent>
              <button
                type="button"
                onClick={() => relatedApi?.scrollPrev()}
                disabled={!relatedCanPrev}
                aria-label="Anteriores"
                className="absolute -left-3 top-1/2 -translate-y-1/2 bg-surface-900/80 border border-surface-600 p-1.5 hover:border-cyan-glow disabled:opacity-20 transition z-10"
              >
                <ChevronLeft className="size-5" />
              </button>
              <button
                type="button"
                onClick={() => relatedApi?.scrollNext()}
                disabled={!relatedCanNext}
                aria-label="Siguientes"
                className="absolute -right-3 top-1/2 -translate-y-1/2 bg-surface-900/80 border border-surface-600 p-1.5 hover:border-cyan-glow disabled:opacity-20 transition z-10"
              >
                <ChevronRight className="size-5" />
              </button>
            </Carousel>
          </section>
        )}

        <Comments
          dealId={deal.id}
          onCountChange={async () => {
            try {
              const fresh = await dealsService.getBySlug(deal.slug);
              setCommentCount(fresh.comment_count ?? 0);
            } catch {
              /* no crítico */
            }
          }}
        />
      </div>
    </Layout>
  );
}
