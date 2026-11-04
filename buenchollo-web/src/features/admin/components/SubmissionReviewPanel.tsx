/** Revisión de una propuesta: enlaces, avisos y DealFormPanel precargado
 *  con acciones de aprobar (opcionalmente con Telegram) y rechazar. */
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { errorMessage } from "@/lib/errors";
import { formatRelativeTime } from "@/lib/format";
import { dealFormSchema } from "@/lib/validation/deals";
import { DealAuthor } from "@/features/deals/components/DealAuthor";
import type { Category } from "@/services/api/categories";
import { isDuplicateDealError, type DealDetailData } from "@/services/api/deals";
import type { Store } from "@/services/api/stores";
import type { AdminSubmission } from "@/services/api/submissions";
import { buildDealPayload, resolveCategorySelection, type DealForm } from "../deal-form";
import { SUBMISSION_STATUS_LABEL, submissionToDealForm } from "../submission-form";
import { useDealImages } from "../hooks/useDealImages";
import { useApproveSubmission, useRejectSubmission } from "../hooks/useAdminSubmissions";
import { DealFormPanel } from "./DealFormPanel";
import { RejectSubmissionDialog } from "./RejectSubmissionDialog";
import { SubmissionWarnings } from "./SubmissionWarnings";

interface Props {
  readonly submission: AdminSubmission;
  readonly stores: Store[];
  readonly cats: Category[];
  readonly subcats: Category[];
  readonly onApproved: (deal: DealDetailData, publishTelegram: boolean) => void;
  readonly onRejected: () => void;
  readonly onClose: () => void;
}

function ExternalUrl({ label, url }: { label: string; url: string }) {
  return (
    <div className="min-w-0">
      <span className="font-mono text-[10px] uppercase text-muted-foreground block">{label}</span>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer nofollow"
        className="inline-flex items-start gap-1 text-xs text-cyan-glow hover:underline break-all"
      >
        <span className="min-w-0">{url}</span>
        <ExternalLink aria-hidden="true" className="size-3 shrink-0 mt-0.5" />
      </a>
    </div>
  );
}

export function SubmissionReviewPanel({
  submission: s,
  stores,
  cats,
  subcats,
  onApproved,
  onRejected,
  onClose,
}: Props) {
  const { user } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState<DealForm>(() => submissionToDealForm(s));
  const [publishTelegram, setPublishTelegram] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const images = useDealImages(form, setForm, user?.id);
  const approve = useApproveSubmission();
  const reject = useRejectSubmission();
  const pending = s.status === "pending";
  // Telegram solo tiene sentido si el chollo queda publicado al aprobar.
  const publishesNow = form.status === "active";

  const handleApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (approve.isPending) return;
    const parsed = dealFormSchema.safeParse({
      title: form.title,
      affiliate_url: form.affiliate_url,
      current_price: form.current_price,
      previous_price: form.previous_price,
      short_description: form.short_description,
      description: form.description,
    });
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? "Datos inválidos");
      return;
    }
    if (form.status === "scheduled" && !form.scheduled_for) {
      toast.error("Indica la fecha y hora de publicación");
      return;
    }
    const categorySelection = resolveCategorySelection(
      form.category_id,
      form.subcategory_id,
      cats,
      subcats,
    );
    const payload = buildDealPayload({ ...form, ...categorySelection }, null);
    try {
      const deal = await approve.mutateAsync({ id: s.id, payload });
      onApproved(deal, publishTelegram && publishesNow);
    } catch (err: unknown) {
      if (isDuplicateDealError(err)) {
        const { slug } = err.data.existing_deal;
        toast.error("Ya hay un chollo activo para este producto", {
          description: err.data.existing_deal.title,
          action: {
            label: "Ver chollo",
            onClick: () => nav({ to: "/chollo/$slug", params: { slug } }),
          },
        });
        return;
      }
      toast.error(errorMessage(err, "No se pudo aprobar la propuesta"));
    }
  };

  const handleReject = async (reason: string) => {
    try {
      await reject.mutateAsync({ id: s.id, reason });
      setRejectOpen(false);
      toast.success("Propuesta rechazada");
      onRejected();
    } catch (err: unknown) {
      toast.error(errorMessage(err, "No se pudo rechazar la propuesta"));
    }
  };

  return (
    <section aria-labelledby="submission-review-title" className="min-w-0 space-y-4">
      <div className="bg-surface-800 border border-surface-700 p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span className="font-mono text-[10px] uppercase text-muted-foreground">
              {SUBMISSION_STATUS_LABEL[s.status]} · {formatRelativeTime(s.created_at)}
            </span>
            <h2 id="submission-review-title" className="font-bold break-words">
              {s.title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 inline-flex items-center gap-1 border border-surface-700 px-2 py-1 font-mono text-[10px] uppercase hover:border-cyan-glow"
          >
            <ArrowLeft aria-hidden="true" className="size-3" /> Volver a la cola
          </button>
        </div>
        <DealAuthor author={s.author} size="sm" />
        <div className="grid gap-2">
          <ExternalUrl label="Enlace original" url={s.original_url} />
          <ExternalUrl label="Enlace reescrito" url={s.affiliate_url} />
        </div>
        <SubmissionWarnings submission={s} />
        {s.status === "rejected" && s.rejection_reason && (
          <p className="text-xs text-muted-foreground break-words">
            Motivo del rechazo: {s.rejection_reason}
          </p>
        )}
        {s.status === "approved" && s.deal_slug && (
          <Link
            to="/chollo/$slug"
            params={{ slug: s.deal_slug }}
            className="text-xs text-cyan-glow hover:underline"
          >
            Ver chollo publicado
          </Link>
        )}
      </div>

      {pending && (
        <DealFormPanel
          form={form}
          setForm={setForm}
          isEditing={false}
          stores={stores}
          cats={cats}
          subcats={subcats}
          images={images}
          onSubmit={handleApprove}
          onCancel={onClose}
          onOpenTelegram={() => undefined}
          heading="Revisar y publicar"
          submitLabel={approve.isPending ? "PUBLICANDO..." : "Aprobar y publicar"}
          showTelegramButton={false}
          footer={
            publishesNow ? (
              <label className="flex items-center gap-2 font-mono text-xs cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={publishTelegram}
                  onChange={(e) => setPublishTelegram(e.target.checked)}
                  className="accent-cyan-500"
                />
                Publicar también en Telegram
              </label>
            ) : null
          }
          extraActions={
            <button
              type="button"
              onClick={() => setRejectOpen(true)}
              className="border border-alert-red/60 text-alert-red font-mono text-xs px-4 py-2 hover:bg-alert-red/10"
            >
              Rechazar
            </button>
          }
        />
      )}

      <RejectSubmissionDialog
        open={rejectOpen}
        busy={reject.isPending}
        onClose={() => setRejectOpen(false)}
        onConfirm={handleReject}
      />
    </section>
  );
}
