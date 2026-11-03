/** Vista previa no interactiva de la tarjeta del chollo. Usa la misma
 *  estructura y clases que `DealCard` para verse igual que en el listado. */
import { ExternalLink, Heart, MessageSquare, Share2, Tag } from "lucide-react";
import { DealVoteControl } from "@/features/deals/components/DealVoteControl";
import { calculateDiscount, formatPrice } from "@/lib/format";

interface SubmissionPreviewCardProps {
  title: string;
  currentPrice: number | null;
  previousPrice: number | null;
  image: string | null;
  storeName: string | null;
  couponCode?: string;
}

const noop = () => {};

export function SubmissionPreviewCard({
  title,
  currentPrice,
  previousPrice,
  image,
  storeName,
  couponCode,
}: SubmissionPreviewCardProps) {
  const discount = calculateDiscount(currentPrice, previousPrice);
  const shownTitle = title.trim() || "Título del chollo";

  return (
    <figure aria-label="Vista previa de la tarjeta" className="m-0">
      <article
        inert
        className="deal-card bg-surface-800 border border-surface-700 rounded-xl overflow-hidden flex flex-col h-full"
      >
        <a className="relative aspect-[4/3] bg-white overflow-hidden border-b border-surface-700 block">
          {image ? (
            <img
              src={image}
              alt=""
              width="300"
              height="300"
              className="absolute inset-0 w-full h-full object-contain p-3"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-muted-foreground font-mono text-xs">
              SIN_IMAGEN
            </div>
          )}
          {discount != null && discount > 0 && (
            <div
              className="badge-discount absolute top-3 right-3 z-10"
              data-testid="preview-discount"
            >
              -{discount}%
            </div>
          )}
        </a>

        <div className="deal-card-body flex flex-col flex-1">
          <h3 className="deal-title card-title text-foreground text-base sm:text-lg mb-4 flex-1 break-words">
            {shownTitle}
          </h3>

          <div className="deal-price flex flex-wrap items-end gap-x-3 gap-y-1 mb-3">
            <span className="price-now product-price card-price font-mono tabular-nums leading-none">
              {currentPrice != null ? formatPrice(currentPrice) : "— €"}
            </span>
            {previousPrice != null && currentPrice != null && previousPrice > currentPrice && (
              <span className="price-old previous-price font-mono tabular-nums pb-1">
                <del>{formatPrice(previousPrice)}</del>
              </span>
            )}
          </div>

          {storeName && (
            <span className="store availability meta">
              <span>Disponible en</span>
              <span className="text-cyan-glow">{storeName}</span>
            </span>
          )}

          {couponCode?.trim() && (
            <span className="mb-3 inline-flex max-w-full items-center gap-1.5 self-start border border-dashed border-cyan-glow/60 px-2 py-0.5 font-mono text-xs text-cyan-glow">
              <Tag className="size-3.5 shrink-0" aria-hidden="true" />
              <span className="truncate">{couponCode.trim()}</span>
            </span>
          )}

          <div className="mt-auto flex items-center justify-between gap-3">
            <span className="posted-date font-mono uppercase tracking-wider">ahora</span>
            <span className="deal-cta btn-cta inline-flex items-center gap-1.5 font-mono text-xs px-4 py-2 shrink-0">
              IR AL CHOLLO <ExternalLink className="size-3.5" />
            </span>
          </div>

          <div className="product-social-row card-social-row">
            <DealVoteControl temperature={0} disabled onVote={noop} />
            <div className="social-actions">
              <button type="button" tabIndex={-1} aria-hidden="true">
                <Heart />
              </button>
              <button type="button" tabIndex={-1} aria-hidden="true" className="social-count">
                <MessageSquare /> 0
              </button>
              <button type="button" tabIndex={-1} aria-hidden="true">
                <Share2 />
              </button>
            </div>
          </div>
        </div>
      </article>
      <figcaption className="sr-only">
        {shownTitle}
        {currentPrice != null ? `, ${formatPrice(currentPrice)}` : ""}
        {discount ? `, ${discount}% de descuento` : ""}
      </figcaption>
    </figure>
  );
}
