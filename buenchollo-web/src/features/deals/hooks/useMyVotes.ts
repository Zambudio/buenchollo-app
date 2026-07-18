import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { dealsService } from "@/services/api/deals";

/** Votos del usuario autenticado para un lote de chollos (una grid), en una
 *  sola petición al backend en vez de una por tarjeta. */
export function useMyVotes(dealIds: string[]): Record<string, number> {
  const { user } = useAuth();
  const [votes, setVotes] = useState<Record<string, number>>({});
  const key = dealIds.join(",");

  useEffect(() => {
    if (!user || !key) {
      setVotes({});
      return;
    }
    dealsService
      .getMyVotesBulk(key.split(","))
      .then(setVotes)
      .catch(() => setVotes({}));
  }, [user, key]);

  return votes;
}
