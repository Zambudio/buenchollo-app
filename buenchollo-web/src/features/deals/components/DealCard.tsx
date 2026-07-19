import { Link } from "@tanstack/react-router";
import { Heart, ExternalLink, MessageSquare, Share2 } from "lucide-react";
import { formatPrice, formatRelativeTime, calculateDiscount } from "@/lib/format";
import { useAuth } from "@/hooks/useAuth";
import { favoritesApi, dealsService } from "@/services/api/deals";
import { errorMessage } from "@/lib/errors";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ShareDialog } from "@/features/deals/components/ShareBox";
import { DealVoteControl } from "@/features/deals/components/DealVoteControl";

export interface DealCardData {
  id: string;
  title: string;
  slug: string;
  image_url: string | null;
  images?: string[] | null;
  current_price: number;
  previous_price: number | null;
  discount_percentage: number | null;
  temperature: number;
  affiliate_url?: string | null;
  comment_count?: number;
  published_at: string;
  created_at?: string | null;
  status?: string;
  expires_at?: string | null;
  scheduled_for?: string | null;
  store?: { id: string; name: string; slug: string } | null;
  category?: { name: string; slug: string } | null;
}

export function DealCard({
  deal,
  isFavorite: initialFav = false,
  myVote: initialVote = 0,
}: {
  deal: DealCardData;
  isFavorite?: boolean;
  myVote?: number;
}) {
  const { user } = useAuth();
  const [fav, setFav] = useState(initialFav);
  const [favLoading, setFavLoading] = useState(false);
  const [imgIdx, setImgIdx] = useState(0);
  const [hover, setHover] = useState(false);

  const [temperature, setTemperature] = useState(deal.temperature);
  const [myVote, setMyVote] = useState(initialVote);
  const [voting, setVoting] = useState(false);

  const gallery = (
    deal.images && deal.images.length > 0 ? deal.images : deal.image_url ? [deal.image_url] : []
  ).filter(Boolean);
  const hasMultiple = gallery.length > 1;

  useEffect(() => {
    setFav(initialFav);
  }, [initialFav]);

  useEffect(() => {
    setMyVote(initialVote);
  }, [initialVote]);

  useEffect(() => {
    setTemperature(deal.temperature);
  }, [deal.temperature]);

  useEffect(() => {
    if (!hover || !hasMultiple) return;
    const t = setInterval(() => setImgIdx((i) => (i + 1) % gallery.length), 1500);
    return () => clearInterval(t);
  }, [hover, hasMultiple, gallery.length]);

  const toggleFav = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) {
      toast.error("Inicia sesión para guardar favoritos");
      return;
    }
    setFavLoading(true);
    try {
      const { is_favorited } = await favoritesApi.toggle(deal.id);
      setFav(is_favorited);
    } catch {
      toast.error("No se pudo actualizar el favorito");
    } finally {
      setFavLoading(false);
    }
  };

  const vote = async (v: 1 | -1) => {
    if (!user) {
      toast.error("Inicia sesión para votar");
      return;
    }
    if (voting) return;
    setVoting(true);
    try {
      const result = await dealsService.vote(deal.id, v);
      setTemperature(result.temperature);
      setMyVote(result.my_vote);
    } catch (e: unknown) {
      toast.error(errorMessage(e, "Error al votar"));
    } finally {
      setVoting(false);
    }
  };

  const trackClick = () => {
    dealsService.trackClick(deal.id).catch(() => {
      /* no crítico */
    });
  };

  const discount =
    deal.discount_percentage ?? calculateDiscount(deal.current_price, deal.previous_price);
  const isExpired = deal.status === "expired";

  return (
    <article
      className={`bg-surface-800 border border-surface-700 rounded-xl overflow-hidden transition-all duration-300 flex flex-col h-full ${isExpired ? "opacity-70" : "hover:border-cyan-glow hover:glow-cyan"}`}
    >
      <Link
        to="/chollo/$slug"
        params={{ slug: deal.slug }}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => {
          setHover(false);
          setImgIdx(0);
        }}
        className="relative aspect-[4/3] bg-white overflow-hidden border-b border-surface-700 block group"
      >
        {gallery.length > 0 ? (
          <>
            {gallery.map((src, i) => (
              <img
                key={src + i}
                src={src}
                alt={deal.title}
                loading="lazy"
                className={`absolute inset-0 w-full h-full object-contain p-3 transition-opacity duration-500 ${isExpired ? "grayscale" : ""} ${i === imgIdx ? "opacity-100" : "opacity-0"} ${i === imgIdx && !isExpired ? "group-hover:scale-105 transition-transform duration-500" : ""}`}
              />
            ))}
            {isExpired && (
              <div className="absolute inset-0 bg-surface-900/60 flex items-center justify-center z-10">
                <span className="bg-alert-red text-white font-mono font-bold text-[10px] px-2 py-1 -rotate-6 border border-white/40">
                  CADUCADO
                </span>
              </div>
            )}
            {hasMultiple && !isExpired && (
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1 z-10">
                {gallery.map((_, i) => (
                  <span
                    key={i}
                    className={`size-1.5 rounded-full transition-all ${i === imgIdx ? "bg-cyan-glow w-4" : "bg-white/60"}`}
                  />
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground font-mono text-xs">
            SIN_IMAGEN
          </div>
        )}
        {discount != null && discount > 0 && !isExpired && (
          <div className="absolute top-3 right-3 bg-alert-red text-white font-mono font-bold text-xs px-2 py-1 z-10">
            -{discount}%
          </div>
        )}
        <button
          type="button"
          onClick={toggleFav}
          disabled={favLoading}
          aria-label={fav ? "Quitar de favoritos" : "Guardar"}
          className="absolute top-3 left-3 size-9 bg-surface-900/80 backdrop-blur border border-surface-600 flex items-center justify-center hover:border-cyan-glow transition-colors z-10"
        >
          <Heart
            className={`size-4 transition-colors ${fav ? "fill-cyan-glow text-cyan-glow" : "text-foreground"}`}
          />
        </button>
      </Link>

      <div className="p-4 sm:p-5 flex flex-col flex-1">
        <div className="flex justify-between items-center mb-3">
          <div className="flex items-center gap-3 font-mono text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <MessageSquare className="size-3.5" /> {deal.comment_count ?? 0}
            </span>
            <ShareDialog
              url={`/chollo/${deal.slug}`}
              title={deal.title}
              price={deal.current_price}
              trigger={
                <button
                  type="button"
                  aria-label="Compartir"
                  className="flex items-center hover:text-cyan-glow transition-colors"
                >
                  <Share2 className="size-3.5" />
                </button>
              }
            />
          </div>

          <DealVoteControl
            temperature={temperature}
            myVote={myVote}
            disabled={voting}
            onVote={vote}
          />
        </div>

        <Link
          to="/chollo/$slug"
          params={{ slug: deal.slug }}
          className="mb-4 flex-1 hover:text-cyan-glow transition-colors"
        >
          <h3 className="text-foreground font-bold text-base sm:text-lg leading-tight line-clamp-2">
            {deal.title}
          </h3>
        </Link>

        <div className="flex items-end gap-3 mb-3">
          <span className="font-mono text-2xl sm:text-3xl font-extrabold text-cyan-glow tabular-nums leading-none">
            {formatPrice(deal.current_price)}
          </span>
          {deal.previous_price && deal.previous_price > deal.current_price && (
            <span className="font-mono text-xs sm:text-sm text-muted-foreground line-through tabular-nums pb-1">
              {formatPrice(deal.previous_price)}
            </span>
          )}
        </div>

        {deal.store && (
          <div className="font-mono text-[11px] text-muted-foreground mb-3">
            Disponible en{" "}
            <Link
              to="/explorar"
              search={{ store: deal.store.id }}
              className="text-foreground hover:text-cyan-glow transition-colors"
            >
              {deal.store.name}
            </Link>
          </div>
        )}

        <div className="mt-auto flex items-center justify-between gap-3">
          <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-wider">
            {formatRelativeTime(deal.published_at)}
          </span>
          <a
            href={deal.affiliate_url ?? undefined}
            target="_blank"
            rel="noopener noreferrer sponsored"
            onClick={trackClick}
            aria-disabled={!deal.affiliate_url}
            className="inline-flex items-center gap-1.5 rounded-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 hover:bg-foreground transition-colors shrink-0"
          >
            IR AL CHOLLO <ExternalLink className="size-3.5" />
          </a>
        </div>
      </div>
    </article>
  );
}
