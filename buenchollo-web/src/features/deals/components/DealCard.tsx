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
import { StoreAvailability } from "@/features/deals/components/StoreAvailability";

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
  imageLoading = "lazy",
}: {
  deal: DealCardData;
  isFavorite?: boolean;
  myVote?: number;
  imageLoading?: "eager" | "lazy";
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
      className={`deal-card bg-surface-800 border border-surface-700 rounded-xl overflow-hidden transition-all duration-300 flex flex-col h-full ${isExpired ? "opacity-70" : "hover:border-cyan-glow hover:glow-cyan"}`}
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
        aria-label={`Ver oferta: ${deal.title} por ${deal.current_price} euros`}
      >
        {gallery.length > 0 ? (
          <>
            {gallery.map((src, i) => (
              <img
                key={src + i}
                src={src}
                alt={deal.title}
                width="300"
                height="300"
                loading={imageLoading}
                decoding="async"
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
          <div className="badge-discount absolute top-3 right-3 z-10">-{discount}%</div>
        )}
      </Link>

      <div className="deal-card-body flex flex-col flex-1">
        <h3 className="deal-title card-title text-foreground text-base sm:text-lg mb-4 flex-1">
          <Link
            to="/chollo/$slug"
            params={{ slug: deal.slug }}
            className="hover:text-cyan-glow transition-colors"
          >
            {deal.title}
          </Link>
        </h3>

        <div className="deal-price flex items-end gap-3 mb-3">
          <span className="price-now product-price card-price font-mono tabular-nums leading-none">
            {formatPrice(deal.current_price)}
          </span>
          {deal.previous_price && deal.previous_price > deal.current_price && (
            <span className="price-old previous-price font-mono tabular-nums pb-1">
              <del>{formatPrice(deal.previous_price)}</del>
            </span>
          )}
        </div>

        {deal.store && <StoreAvailability store={deal.store} />}

        <div className="mt-auto flex items-center justify-between gap-3">
          <span className="posted-date font-mono uppercase tracking-wider">
            {formatRelativeTime(deal.published_at)}
          </span>
          <a
            href={deal.affiliate_url ?? undefined}
            target="_blank"
            rel="noopener noreferrer nofollow sponsored"
            onClick={trackClick}
            aria-disabled={!deal.affiliate_url}
            aria-label={`Ver oferta de ${deal.title} en ${deal.store?.name ?? "la tienda"}`}
            className="deal-cta btn-cta inline-flex items-center gap-1.5 font-mono text-xs px-4 py-2 transition-colors shrink-0"
          >
            IR AL CHOLLO <ExternalLink className="size-3.5" />
          </a>
        </div>

        <div className="product-social-row card-social-row">
          <DealVoteControl
            temperature={temperature}
            myVote={myVote}
            disabled={voting}
            onVote={vote}
          />
          <div className="social-actions">
            <button
              type="button"
              onClick={toggleFav}
              disabled={favLoading}
              aria-label={fav ? "Quitar de favoritos" : "Guardar"}
              className={fav ? "is-active" : ""}
            >
              <Heart className={fav ? "fill-current" : ""} />
            </button>
            <button type="button" aria-label="Ver comentarios" className="social-count">
              <MessageSquare /> {deal.comment_count ?? 0}
            </button>
            <ShareDialog
              url={`/chollo/${deal.slug}`}
              title={deal.title}
              price={deal.current_price}
              trigger={
                <button type="button" aria-label="Compartir">
                  <Share2 />
                </button>
              }
            />
          </div>
        </div>
      </div>
    </article>
  );
}
