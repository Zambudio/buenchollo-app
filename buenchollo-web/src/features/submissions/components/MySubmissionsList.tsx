import { Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { formatPrice, formatRelativeTime } from "@/lib/format";
import { submissionsApi, type Submission, type SubmissionStatus } from "@/services/api/submissions";
import { PublishDealButton } from "./PublishDealButton";

export const MY_SUBMISSIONS_KEY = ["submissions", "mine"] as const;

const STATUS_LABEL: Record<SubmissionStatus, string> = {
  pending: "En revisión",
  approved: "Publicado",
  rejected: "Rechazado",
  withdrawn: "Retirado",
};

const STATUS_CLASS: Record<SubmissionStatus, string> = {
  pending: "border-amber-400/50 text-amber-400",
  approved: "border-emerald-400/50 text-emerald-400",
  rejected: "border-alert-red/60 text-alert-red",
  withdrawn: "border-surface-600 text-muted-foreground",
};

function SubmissionRow({
  submission: s,
  onWithdraw,
  disabled,
}: {
  submission: Submission;
  onWithdraw: () => void;
  disabled: boolean;
}) {
  const title =
    s.status === "approved" && s.deal_slug ? (
      <Link
        to="/chollo/$slug"
        params={{ slug: s.deal_slug }}
        className="font-bold hover:text-cyan-glow transition-colors break-words"
      >
        {s.title}
      </Link>
    ) : (
      <span className="font-bold break-words">{s.title}</span>
    );

  return (
    <li className="bg-surface-800 border border-surface-700 p-3 sm:p-4 flex gap-3">
      <div className="size-16 sm:size-20 shrink-0 bg-white border border-surface-700 overflow-hidden">
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
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mb-1">
          <span
            className={`font-mono text-[10px] uppercase tracking-wider border px-1.5 py-0.5 ${STATUS_CLASS[s.status]}`}
          >
            {STATUS_LABEL[s.status]}
          </span>
          <span className="font-mono text-[10px] text-muted-foreground uppercase">
            {formatRelativeTime(s.created_at)}
          </span>
        </div>
        <div className="text-sm sm:text-base">{title}</div>
        <div className="font-mono text-sm text-cyan-glow mt-1">{formatPrice(s.current_price)}</div>
        {s.status === "rejected" && s.rejection_reason && (
          <p className="text-xs text-muted-foreground mt-2 break-words">
            Motivo: {s.rejection_reason}
          </p>
        )}
        {s.status === "pending" && (
          <button
            type="button"
            onClick={onWithdraw}
            disabled={disabled}
            className="mt-2 font-mono text-xs border border-surface-600 px-3 py-1.5 hover:border-alert-red hover:text-alert-red transition-colors disabled:opacity-50"
          >
            Retirar
          </button>
        )}
      </div>
    </li>
  );
}

export function MySubmissionsList() {
  const qc = useQueryClient();
  const [target, setTarget] = useState<Submission | null>(null);
  const { data, isLoading, isError } = useQuery({
    queryKey: MY_SUBMISSIONS_KEY,
    queryFn: () => submissionsApi.mine(),
  });
  const withdraw = useMutation({
    mutationFn: (id: string) => submissionsApi.withdraw(id),
    onSuccess: () => {
      toast.success("Chollo retirado");
      return qc.invalidateQueries({ queryKey: MY_SUBMISSIONS_KEY });
    },
    onError: () => {
      toast.error("No se pudo retirar el chollo. Inténtalo de nuevo.");
      return qc.invalidateQueries({ queryKey: MY_SUBMISSIONS_KEY });
    },
  });

  if (isLoading) {
    return (
      <div className="font-mono text-xs text-muted-foreground py-12 text-center">CARGANDO...</div>
    );
  }
  if (isError) {
    return (
      <div className="bg-surface-800 border border-surface-700 p-8 text-center text-muted-foreground font-mono text-sm">
        No se pudieron cargar tus chollos.
      </div>
    );
  }
  if (!data || data.length === 0) {
    return (
      <div className="bg-surface-800 border border-surface-700 p-8 sm:p-12 text-center">
        <p className="text-muted-foreground font-mono text-sm mb-4">
          Todavía no has publicado ningún chollo.
        </p>
        <div className="flex justify-center">
          <PublishDealButton />
        </div>
      </div>
    );
  }

  return (
    <>
      <ul className="space-y-3">
        {data.map((s) => (
          <SubmissionRow
            key={s.id}
            submission={s}
            disabled={withdraw.isPending}
            onWithdraw={() => setTarget(s)}
          />
        ))}
      </ul>
      <AlertDialog open={target !== null} onOpenChange={(o) => !o && setTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Retirar este chollo?</AlertDialogTitle>
            <AlertDialogDescription>
              {target?.title} dejará de estar en revisión. Podrás volver a publicarlo más tarde.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (target) withdraw.mutate(target.id);
              }}
            >
              Retirar chollo
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
