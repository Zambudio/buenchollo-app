import { ThumbsDown, ThumbsUp } from "lucide-react";

interface DealVoteControlProps {
  temperature: number;
  myVote?: number;
  disabled?: boolean;
  size?: "card" | "detail";
  onVote: (vote: 1 | -1) => void;
}

export function DealVoteControl({
  temperature,
  myVote = 0,
  disabled = false,
  size = "card",
  onVote,
}: DealVoteControlProps) {
  const isDetail = size === "detail";
  const buttonSize = isDetail ? "size-8" : "size-7";
  const iconSize = isDetail ? "size-4" : "size-3.5";
  const temperatureColor =
    temperature === 0 ? "text-[#E8EEF7]" : temperature > 0 ? "text-[#9FB3C8]" : "text-[#FF5C7A]";

  return (
    <div
      className={`inline-flex shrink-0 items-center rounded-full border border-surface-600 bg-surface-900/90 font-mono shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] ${
        isDetail ? "gap-1 p-1" : "gap-0.5 p-0.5"
      }`}
      aria-label={`Temperatura: ${temperature} grados`}
    >
      <button
        type="button"
        onClick={() => onVote(-1)}
        disabled={disabled}
        aria-label="Votar negativo"
        aria-pressed={myVote === -1}
        className={`${buttonSize} inline-flex items-center justify-center rounded-full transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
          myVote === -1
            ? "bg-alert-red/15 text-alert-red ring-1 ring-inset ring-alert-red/50"
            : "text-alert-red/80 hover:bg-alert-red/10 hover:text-alert-red"
        }`}
      >
        <ThumbsDown className={iconSize} strokeWidth={2.25} />
      </button>

      <span
        className={`min-w-[3.25em] text-center font-bold tabular-nums ${temperatureColor} ${
          isDetail ? "text-sm" : "text-xs"
        }`}
      >
        {temperature}°
      </span>

      <button
        type="button"
        onClick={() => onVote(1)}
        disabled={disabled}
        aria-label="Votar positivo"
        aria-pressed={myVote === 1}
        className={`${buttonSize} inline-flex items-center justify-center rounded-full transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
          myVote === 1
            ? "bg-sky-500/15 text-sky-400 ring-1 ring-inset ring-sky-400/50"
            : "text-sky-400/80 hover:bg-sky-500/10 hover:text-sky-300"
        }`}
      >
        <ThumbsUp className={iconSize} strokeWidth={2.25} />
      </button>
    </div>
  );
}
