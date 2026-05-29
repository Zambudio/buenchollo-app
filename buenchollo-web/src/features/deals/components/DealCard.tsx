import { Link } from "@tanstack/react-router";
import { Heart, Flame } from "lucide-react";
import { formatPrice, formatRelativeTime, calculateDiscount, temperatureColor } from "@/lib/format";
import { useAuth } from "@/hooks/useAuth";
import { favoritesApi } from "@/services/api/deals";
import { useEffect, useState } from "react";
import { toast } from "sonner";

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
  published_at: string;
  created_at?: string | null;
  status?: string;
  expires_at?: string | null;
  scheduled_for?: string | null;
  store?: { name: string; slug: string } | null;
  category?: { name: string; slug: string } | null;
}

export function DealCard({
  deal,
  isFavorite: initialFav = false,
}: {
  deal: DealCardData;
  isFavorite?: boolean;
}) {
  const { user } = useAuth();
  const [fav, setFav] = useState(initialFav);
  const [loading, setLoading] = useState(false);
  const [imgIdx, setImgIdx] = useState(0);
  const [hover, setHover] = useState(false);

  const gallery = (
    deal.images && deal.images.length > 0 ? deal.images : deal.image_url ? [deal.image_url] : []
  ).filter(Boolean);
  const hasMultiple = gallery.length > 1;

  useEffect(() => {
    setFav(initialFav);
  }, [initialFav]);

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
    setLoading(true);
    try {
      const { is_favorited } = await favoritesApi.toggle(deal.id);
      setFav(is_favorited);
    } catch {
      toast.error("No se pudo actualizar el favorito");
    } finally {
      setLoading(false);
    }
  };

  const tempColor = temperatureColor(deal.temperature);
  const discount =
    deal.discount_percentage ?? calculateDiscount(deal.current_price, deal.previous_price);
  const isExpired = deal.status === "expired";

  return (
    <Link
      to="/chollo/$slug"
      params={{ slug: deal.slug }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => {
        setHover(false);
        setImgIdx(0);
      }}
      className={`group bg-surface-800 border border-surface-700 transition-all duration-300 flex flex-col h-full ${isExpired ? "opacity-70" : "hover:border-cyan-glow hover:glow-cyan"}`}
    >
      <div className="relative aspect-[4/3] bg-white overflow-hidden border-b border-surface-700">
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
          onClick={toggleFav}
          disabled={loading}
          aria-label={fav ? "Quitar de favoritos" : "Guardar"}
          className="absolute top-3 left-3 size-9 bg-surface-900/80 backdrop-blur border border-surface-600 flex items-center justify-center hover:border-cyan-glow transition-colors z-10"
        >
          <Heart
            className={`size-4 transition-colors ${fav ? "fill-cyan-glow text-cyan-glow" : "text-foreground"}`}
          />
        </button>
      </div>

      <div className="p-4 sm:p-5 flex flex-col flex-1">
        <div className="flex justify-between items-center mb-3 font-mono text-xs">
          <span className="text-cyan-glow truncate">
            @{deal.store?.slug?.toUpperCase() ?? "STORE"}
          </span>
          <span className={`flex items-center gap-1 font-bold ${tempColor}`}>
            <Flame className="size-3" /> {deal.temperature}°
          </span>
        </div>

        <h3 className="text-foreground font-bold text-base sm:text-lg leading-tight mb-4 line-clamp-2 flex-1 group-hover:text-cyan-glow transition-colors">
          {deal.title}
        </h3>

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

        <div className="font-mono text-[10px] uppercase text-muted-foreground tracking-wider">
          {formatRelativeTime(deal.published_at)}
          {deal.category && <> · {deal.category.name}</>}
        </div>
      </div>
    </Link>
  );
}
