/** Presentación de la tarjeta de chollo. `DealCard` aporta estado y efectos
 *  (votos, favoritos, tracking); con `preview` se pinta igual pero sin
 *  enlaces ni acciones (vista previa de "Publicar chollo"). */
import { Link } from "@tanstack/react-router";
import { Heart, ExternalLink, MessageSquare, Share2 } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { formatPrice, formatRelativeTime, calculateDiscount } from "@/lib/format";
import { ShareDialog } from "@/features/deals/components/ShareBox";
import { DealVoteControl } from "@/features/deals/components/DealVoteControl";
import { StoreAvailability } from "@/features/deals/components/StoreAvailability";
import { DealAuthor } from "@/features/deals/components/DealAuthor";
import { ProductVoteButton } from "@/features/catalog/ProductVoteButton";
import type { DealAuthor as DealAuthorData } from "@/services/api/submissions";

export interface DealCardData {
  id: string;
  product_id?: string | null;
  title: string;
  short_description?: string | null;
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
  source?: string;
  author?: DealAuthorData | null;
}

export interface DealCardViewProps {
  deal: DealCardData;
  imageLoading?: "eager" | "lazy";
  /** Sin enlaces, votos, favoritos, compartir ni tracking. */
  preview?: boolean;
  temperature: number;
  myVote?: number;
  voting?: boolean;
  onVote?: (vote: 1 | -1) => void;
  fav?: boolean;
  favLoading?: boolean;
  onToggleFav?: (e: React.MouseEvent) => void;
  onCtaClick?: () => void;
}

const noop = () => {};

interface CardLinkProps {
  preview: boolean;
  slug: string;
  className: string;
  children: ReactNode;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  "aria-label"?: string;
}

function CardLink({ preview, slug, className, children, ...rest }: CardLinkProps) {
  if (preview) {
    return (
      <a className={className} onMouseEnter={rest.onMouseEnter} onMouseLeave={rest.onMouseLeave}>
        {children}
      </a>
    );
  }
  return (
    <Link to="/chollo/$slug" params={{ slug }} className={className} {...rest}>
      {children}
    </Link>
  );
}

export function DealCardView({
  deal,
  imageLoading = "lazy",
  preview = false,
  temperature,
  myVote = 0,
  voting = false,
  onVote = noop,
  fav = false,
  favLoading = false,
  onToggleFav,
  onCtaClick,
}: DealCardViewProps) {
  const [imgIdx, setImgIdx] = useState(0);
  const [hover, setHover] = useState(false);

  const gallery = (
    deal.images && deal.images.length > 0 ? deal.images : deal.image_url ? [deal.image_url] : []
  ).filter(Boolean);
  const hasMultiple = gallery.length > 1;

  useEffect(() => {
    if (!hover || !hasMultiple) return;
    const t = setInterval(() => setImgIdx((i) => (i + 1) % gallery.length), 1500);
    return () => clearInterval(t);
  }, [hover, hasMultiple, gallery.length]);

  const discount =
    deal.discount_percentage ?? calculateDiscount(deal.current_price, deal.previous_price);
  const isExpired = deal.status === "expired";

  const shareButton = (
    <button type="button" aria-label="Compartir" disabled={preview}>
      <Share2 />
    </button>
  );

  return (
    <article
      inert={preview || undefined}
      className={`deal-card bg-surface-800 border border-surface-700 rounded-xl overflow-hidden transition-all duration-300 ${isExpired ? "opacity-70" : "hover:border-cyan-glow hover:glow-cyan"}`}
    >
      <CardLink
        preview={preview}
        slug={deal.slug}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => {
          setHover(false);
          setImgIdx(0);
        }}
        className="deal-card-media relative bg-white overflow-hidden block group"
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
      </CardLink>

      <div className="deal-card-body flex flex-col flex-1">
        <div className="deal-card-top">
          <div className="deal-card-votes">
            <DealVoteControl
              temperature={temperature}
              myVote={myVote}
              disabled={preview || voting}
              onVote={onVote}
            />
            {!preview && deal.product_id && <ProductVoteButton productId={deal.product_id} />}
          </div>
          <span className="posted-date deal-card-posted">
            Publicado {formatRelativeTime(deal.published_at)}
          </span>
        </div>

        <h3 className="deal-title card-title text-foreground">
          <CardLink
            preview={preview}
            slug={deal.slug}
            className="hover:text-cyan-glow transition-colors"
          >
            {deal.title}
          </CardLink>
        </h3>

        <div className="deal-card-priceline">
          <span className="deal-price">
            <span className="price-now product-price card-price font-mono tabular-nums leading-none">
              {preview && !(deal.current_price > 0) ? "— €" : formatPrice(deal.current_price)}
            </span>
            {deal.previous_price && deal.previous_price > deal.current_price && (
              <span className="price-old previous-price font-mono tabular-nums">
                <del>{formatPrice(deal.previous_price)}</del>
              </span>
            )}
            {discount != null && discount > 0 && !isExpired && (
              <span className="deal-discount">-{discount}%</span>
            )}
          </span>
          {deal.store && <StoreAvailability store={deal.store} linked={!preview} />}
          {deal.author && <DealAuthor author={deal.author} size="sm" />}
        </div>

        {deal.short_description && (
          <p className="deal-card-description">{deal.short_description}</p>
        )}

        <div className="deal-card-actions product-social-row">
          <div className="social-actions">
            <button
              type="button"
              aria-label="Ver comentarios"
              className="social-count"
              disabled={preview}
            >
              <MessageSquare /> {deal.comment_count ?? 0}
            </button>
            {preview ? (
              shareButton
            ) : (
              <ShareDialog
                url={`/chollo/${deal.slug}`}
                title={deal.title}
                price={deal.current_price}
                trigger={shareButton}
              />
            )}
            <button
              type="button"
              onClick={onToggleFav}
              disabled={preview || favLoading}
              aria-label={fav ? "Quitar de favoritos" : "Guardar"}
              className={fav ? "is-active" : ""}
            >
              <Heart className={fav ? "fill-current" : ""} />
            </button>
          </div>
          <a
            href={preview ? undefined : (deal.affiliate_url ?? undefined)}
            target="_blank"
            rel="noopener noreferrer nofollow sponsored"
            onClick={preview ? undefined : onCtaClick}
            aria-disabled={preview || !deal.affiliate_url}
            aria-label={`Ver oferta de ${deal.title} en ${deal.store?.name ?? "la tienda"}`}
            className="deal-cta btn-cta inline-flex items-center gap-1.5 shrink-0 transition-colors"
          >
            Ir al chollo <ExternalLink className="size-4" />
          </a>
        </div>
      </div>
    </article>
  );
}
