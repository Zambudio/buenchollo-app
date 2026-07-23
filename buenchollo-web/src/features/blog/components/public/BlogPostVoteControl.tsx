import { ThumbsDown, ThumbsUp } from "lucide-react";

interface Props {
  votesUp: number;
  votesDown: number;
  myVote: number;
  disabled?: boolean;
  onVote: (vote: 1 | -1) => void;
}

/** "¿Te ha sido útil este artículo?" — voto simple con dos contadores
 * independientes (a diferencia de la temperatura combinada de los chollos). */
export function BlogPostVoteControl({ votesUp, votesDown, myVote, disabled, onVote }: Props) {
  return (
    <div className="flex items-center gap-1.5" role="group" aria-label="Valorar este artículo">
      <button
        type="button"
        onClick={() => onVote(1)}
        disabled={disabled}
        aria-label="Me ha resultado útil"
        aria-pressed={myVote === 1}
        className={`inline-flex items-center gap-1.5 border px-2.5 py-1.5 font-mono text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
          myVote === 1
            ? "border-cyan-glow text-cyan-glow bg-cyan-glow/10"
            : "border-surface-700 text-muted-foreground hover:border-cyan-glow hover:text-cyan-glow"
        }`}
      >
        <ThumbsUp className="size-3.5" /> {votesUp}
      </button>
      <button
        type="button"
        onClick={() => onVote(-1)}
        disabled={disabled}
        aria-label="No me ha resultado útil"
        aria-pressed={myVote === -1}
        className={`inline-flex items-center gap-1.5 border px-2.5 py-1.5 font-mono text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
          myVote === -1
            ? "border-alert-red text-alert-red bg-alert-red/10"
            : "border-surface-700 text-muted-foreground hover:border-alert-red hover:text-alert-red"
        }`}
      >
        <ThumbsDown className="size-3.5" /> {votesDown}
      </button>
    </div>
  );
}
