import { Link } from "@tanstack/react-router";
import { Trophy } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { errorMessage } from "@/lib/errors";
import { catalogService } from "@/services/api/catalog";
import { PRODUCT_VOTE_EVENT, publishProductVote, type VoteChange } from "./productVoteEvents";

type PendingVote = { resolve: (voted: boolean) => void; reject: (error: unknown) => void };
const pendingVotes = new Map<string, PendingVote[]>();
let flushTimer: ReturnType<typeof setTimeout> | undefined;

// Las tarjetas visibles consultan el estado del usuario en una sola petición.
function loadVote(productId: string): Promise<boolean> {
  return new Promise((resolve, reject) => {
    pendingVotes.set(productId, [...(pendingVotes.get(productId) ?? []), { resolve, reject }]);
    if (flushTimer) return;
    flushTimer = setTimeout(async () => {
      flushTimer = undefined;
      const queued = [...pendingVotes.entries()];
      pendingVotes.clear();
      for (let start = 0; start < queued.length; start += 50) {
        const batch = queued.slice(start, start + 50);
        try {
          const voted = new Set(await catalogService.myVotes(batch.map(([id]) => id)));
          batch.forEach(([id, listeners]) =>
            listeners.forEach(({ resolve }) => resolve(voted.has(id))),
          );
        } catch (error) {
          batch.forEach(([, listeners]) => listeners.forEach(({ reject }) => reject(error)));
        }
      }
    }, 0);
  });
}

export function ProductVoteButton({ productId }: { productId: string }) {
  const { user } = useAuth();
  const userId = user?.id;
  const [voted, setVoted] = useState(false);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    setVoted(false);
    void loadVote(productId)
      .then((value) => {
        if (!cancelled) setVoted(value);
      })
      .catch(() => {
        // El botón sigue utilizable aunque no se pueda consultar el estado previo.
      });
    return () => {
      cancelled = true;
    };
  }, [productId, userId]);

  useEffect(() => {
    const syncVote = (event: Event) => {
      const change = (event as CustomEvent<VoteChange>).detail;
      if (change.productId === productId) setVoted(change.voted);
    };
    window.addEventListener(PRODUCT_VOTE_EVENT, syncVote);
    return () => window.removeEventListener(PRODUCT_VOTE_EVENT, syncVote);
  }, [productId]);

  if (!user) {
    return (
      <Link
        className="product-top-vote"
        to="/login"
        aria-label="Inicia sesión para votar este producto en el top"
      >
        <Trophy aria-hidden="true" /> Votar producto
      </Link>
    );
  }

  const toggleVote = async () => {
    if (pending) return;
    setPending(true);
    try {
      const result = await catalogService.vote(productId);
      setVoted(result.voted);
      publishProductVote(productId, result.voted, "card");
      toast.success(result.voted ? "Producto votado para el top" : "Voto al producto retirado");
    } catch (error) {
      toast.error(errorMessage(error, "No se pudo votar este producto"));
    } finally {
      setPending(false);
    }
  };

  return (
    <button
      className={`product-top-vote ${voted ? "is-voted" : ""}`}
      type="button"
      aria-label={
        voted ? "Retirar voto a este producto del top" : "Votar este producto para el top"
      }
      aria-pressed={voted}
      disabled={pending}
      onClick={() => void toggleVote()}
    >
      <Trophy aria-hidden="true" /> {voted ? "Producto votado" : "Votar producto"}
    </button>
  );
}
