import { dealsService } from "@/services/api/deals";
import type { BlogDealSummary } from "@/services/api/blog";

export interface ProductRecommendationNodeAttrs {
  mode: "deal" | "manual";
  deal_id: string | null;
  name: string | null;
  image_url: string | null;
  affiliate_url: string | null;
  note: string | null;
  button_text: string | null;
  badge: string | null;
}

/** Bloque público de producto recomendado. Identificable como recomendación
 * (no como anuncio agresivo), CTA visible, accesible por teclado, y con
 * `rel="sponsored nofollow noopener"` — el destino del enlace nunca se oculta. */
export function ProductRecommendationCard({
  attrs,
  deal,
}: {
  attrs: ProductRecommendationNodeAttrs;
  deal?: BlogDealSummary;
}) {
  const isDealMode = attrs.mode === "deal";
  const title = isDealMode ? deal?.title : attrs.name;
  const image = isDealMode ? deal?.image_url : attrs.image_url;
  const href = isDealMode ? deal?.affiliate_url : attrs.affiliate_url;
  const store = isDealMode ? deal?.store_name : null;
  const showPrice = isDealMode && deal?.is_active && deal.current_price != null;

  if (!title || !href) return null;

  const handleClick = () => {
    if (isDealMode && attrs.deal_id) {
      dealsService.trackClick(attrs.deal_id).catch(() => {
        /* no crítico */
      });
    }
  };

  return (
    <aside className="not-prose my-6 border border-cyan-glow/40 bg-surface-800/60 rounded-lg p-4 flex gap-4 items-center">
      {image && (
        <img
          src={image}
          alt={title}
          loading="lazy"
          className="size-20 object-cover rounded shrink-0"
        />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-mono uppercase tracking-wide text-cyan-glow mb-1">
          {attrs.badge || "Recomendación"} {store ? `· ${store}` : ""}
        </p>
        <p className="font-bold leading-snug">{title}</p>
        {attrs.note && <p className="text-sm text-muted-foreground mt-1">{attrs.note}</p>}
        {showPrice && (
          <p className="text-sm mt-1">
            <span className="font-bold text-cyan-glow">{deal!.current_price!.toFixed(2)} €</span>
            {deal!.previous_price != null && (
              <span className="line-through text-muted-foreground ml-2">
                {deal!.previous_price.toFixed(2)} €
              </span>
            )}
          </p>
        )}
        <a
          href={href}
          target="_blank"
          rel="sponsored nofollow noopener"
          onClick={handleClick}
          className="inline-block mt-2 bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-3 py-1.5 hover:bg-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-glow"
        >
          {attrs.button_text || "Ver oferta"}
        </a>
      </div>
    </aside>
  );
}
