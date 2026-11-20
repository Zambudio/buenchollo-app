import { useAuth } from "@/hooks/useAuth";
import { favoritesApi, dealsService } from "@/services/api/deals";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { DealCardView, type DealCardData } from "@/features/deals/components/DealCardView";

export type { DealCardData };

export function DealCard({
  deal,
  isFavorite: initialFav = false,
  imageLoading = "lazy",
}: {
  deal: DealCardData;
  isFavorite?: boolean;
  imageLoading?: "eager" | "lazy";
}) {
  const { user } = useAuth();
  const [fav, setFav] = useState(initialFav);
  const [favLoading, setFavLoading] = useState(false);

  useEffect(() => {
    setFav(initialFav);
  }, [initialFav]);

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

  const trackClick = () => {
    dealsService.trackClick(deal.id).catch(() => {
      /* no crítico */
    });
  };

  return (
    <DealCardView
      deal={deal}
      imageLoading={imageLoading}
      fav={fav}
      favLoading={favLoading}
      onToggleFav={toggleFav}
      onCtaClick={trackClick}
    />
  );
}
