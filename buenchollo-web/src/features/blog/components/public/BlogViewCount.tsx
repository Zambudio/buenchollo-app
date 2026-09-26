import { Eye } from "lucide-react";

function formatCount(count: number | null | undefined): string {
  const safeCount = typeof count === "number" && Number.isFinite(count) ? count : 0;
  return Math.max(0, Math.trunc(safeCount))
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function BlogViewCount({ count }: { count?: number | null }) {
  const formatted = formatCount(count);
  return (
    <span
      className="inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground"
      aria-label={`${formatted} visualizaciones validadas`}
    >
      <Eye className="size-4" aria-hidden="true" />
      {formatted} visitas
    </span>
  );
}
