/** Cola de propuestas con pestañas por estado. */
import { formatPrice, formatRelativeTime } from "@/lib/format";
import { DealAuthor } from "@/features/deals/components/DealAuthor";
import type { AdminSubmission, SubmissionStatus } from "@/services/api/submissions";
import { QUEUE_TABS } from "../submission-form";
import { SubmissionWarnings } from "./SubmissionWarnings";

interface Props {
  readonly status: SubmissionStatus;
  readonly onStatusChange: (status: SubmissionStatus) => void;
  readonly items: AdminSubmission[] | undefined;
  readonly loading: boolean;
  readonly error: boolean;
  readonly selectedId: string | undefined;
  readonly onSelect: (id: string) => void;
}

export function SubmissionQueue({
  status,
  onStatusChange,
  items,
  loading,
  error,
  selectedId,
  onSelect,
}: Props) {
  return (
    <section aria-label="Cola de propuestas" className="min-w-0 space-y-3">
      <div role="tablist" aria-label="Estado" className="grid grid-cols-2 sm:grid-cols-4 gap-1">
        {QUEUE_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={status === tab.value}
            onClick={() => onStatusChange(tab.value)}
            className={`font-mono text-[11px] uppercase px-2 py-2 border ${
              status === tab.value
                ? "border-cyan-glow text-cyan-glow bg-surface-700"
                : "border-surface-700 hover:border-cyan-glow/60"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="font-mono text-xs text-muted-foreground">CARGANDO...</p>
      ) : error ? (
        <p role="alert" className="font-mono text-xs text-alert-red">
          No se pudo cargar la cola.
        </p>
      ) : !items || items.length === 0 ? (
        <p className="font-mono text-xs text-muted-foreground border border-surface-700 p-4">
          No hay propuestas en esta lista.
        </p>
      ) : (
        <ul className="space-y-2">
          {items.map((s) => (
            <li
              key={s.id}
              className={`relative bg-surface-800 border p-3 flex gap-3 ${
                selectedId === s.id
                  ? "border-cyan-glow"
                  : "border-surface-700 hover:border-cyan-glow/60"
              }`}
            >
              <div className="size-14 shrink-0 bg-white border border-surface-700 overflow-hidden">
                {s.image_url ? (
                  <img
                    src={s.image_url}
                    alt=""
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    className="size-full object-contain p-1"
                  />
                ) : null}
              </div>
              <div className="min-w-0 flex-1 space-y-1">
                <button
                  type="button"
                  onClick={() => onSelect(s.id)}
                  aria-current={selectedId === s.id ? "true" : undefined}
                  className="block w-full text-left text-sm font-bold break-words hover:text-cyan-glow after:absolute after:inset-0"
                >
                  {s.title}
                </button>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                  <span className="font-mono text-sm text-cyan-glow">
                    {formatPrice(s.current_price)}
                  </span>
                  <span className="font-mono text-[10px] uppercase text-muted-foreground">
                    {formatRelativeTime(s.created_at)}
                  </span>
                </div>
                <DealAuthor author={s.author} size="sm" />
                <SubmissionWarnings submission={s} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
