import { useAuth } from "@/hooks/useAuth";
import { favoritesApi, dealsService } from "@/services/api/deals";
import { errorMessage } from "@/lib/errors";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { DealCardView, type DealCardData } from "@/features/deals/components/DealCardView";

export type { DealCardData };

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

  const [temperature, setTemperature] = useState(deal.temperature);
  const [myVote, setMyVote] = useState(initialVote);
  const [voting, setVoting] = useState(false);

  useEffect(() => {
    setFav(initialFav);
  }, [initialFav]);

  useEffect(() => {
    setMyVote(initialVote);
  }, [initialVote]);

  useEffect(() => {
    setTemperature(deal.temperature);
  }, [deal.temperature]);

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

  return (
    <DealCardView
      deal={deal}
      imageLoading={imageLoading}
      temperature={temperature}
      myVote={myVote}
      voting={voting}
      onVote={vote}
      fav={fav}
      favLoading={favLoading}
      onToggleFav={toggleFav}
      onCtaClick={trackClick}
    />
  );
}
