import { Link } from "@tanstack/react-router";
import { Trophy } from "lucide-react";
import { useProductVote } from "./productVotes";

/** Voto al producto para el top de su categoría, distinto del voto al chollo. */
export function ProductVoteButton({ productId }: { productId: string }) {
  const { isLoggedIn, voted, pending, toggle } = useProductVote(productId);

  if (!isLoggedIn) {
    return (
      <Link
        className="vote-chip"
        to="/login"
        aria-label="Inicia sesión para votar este producto en el top"
      >
        <Trophy aria-hidden="true" /> Votar producto
      </Link>
    );
  }

  return (
    <button
      className={`vote-chip ${voted ? "is-voted" : ""}`}
      type="button"
      aria-label={
        voted ? "Retirar voto a este producto del top" : "Votar este producto para el top"
      }
      aria-pressed={voted}
      disabled={pending}
      onClick={() => void toggle()}
    >
      <Trophy aria-hidden="true" /> {voted ? "Producto votado" : "Votar producto"}
    </button>
  );
}
