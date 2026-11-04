/** Pantalla de moderación: cola + revisión de la propuesta seleccionada. */
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import type { DealDetailData } from "@/services/api/deals";
import type { SubmissionStatus } from "@/services/api/submissions";
import { useAdminCatalogs } from "../hooks/useAdminCatalogs";
import { useAdminSubmission, useAdminSubmissionsList } from "../hooks/useAdminSubmissions";
import { useTelegramHandoff } from "../hooks/useTelegramHandoff";
import { SubmissionQueue } from "./SubmissionQueue";
import { SubmissionReviewPanel } from "./SubmissionReviewPanel";
import { TelegramHandoffPanel } from "./TelegramHandoffPanel";

interface Props {
  readonly selectedId: string | undefined;
  readonly onSelect: (id: string | undefined) => void;
}

export function SubmissionsAdminPage({ selectedId, onSelect }: Props) {
  const nav = useNavigate();
  const [status, setStatus] = useState<SubmissionStatus>("pending");
  const list = useAdminSubmissionsList(status);
  const detail = useAdminSubmission(selectedId);
  const { stores, cats, subcats } = useAdminCatalogs();
  const telegram = useTelegramHandoff();

  useEffect(() => {
    if (selectedId && detail.isError) {
      toast.error("No se encontró la propuesta");
      onSelect(undefined);
    }
  }, [selectedId, detail.isError, onSelect]);

  const handleApproved = (deal: DealDetailData, publishTelegram: boolean) => {
    toast.success("Propuesta aprobada y publicada", {
      description: deal.title,
      action: {
        label: "Ver chollo",
        onClick: () => nav({ to: "/chollo/$slug", params: { slug: deal.slug } }),
      },
    });
    onSelect(undefined);
    if (publishTelegram) telegram.openFromDeal(deal);
  };

  const submission = selectedId && detail.data?.id === selectedId ? detail.data : undefined;
  const hasSelection = !!selectedId;

  return (
    <div>
      <TelegramHandoffPanel handoff={telegram} />
      <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4">
        Propuestas de la comunidad
      </h2>
      <div
        className={`grid gap-4 ${hasSelection ? "xl:grid-cols-[minmax(0,320px)_minmax(0,1fr)]" : ""}`}
      >
        <div className={hasSelection ? "hidden xl:block" : ""}>
          <SubmissionQueue
            status={status}
            onStatusChange={setStatus}
            items={list.data}
            loading={list.isLoading}
            error={list.isError}
            selectedId={selectedId}
            onSelect={onSelect}
          />
        </div>
        {hasSelection &&
          (submission ? (
            <SubmissionReviewPanel
              key={submission.id}
              submission={submission}
              stores={stores}
              cats={cats}
              subcats={subcats}
              onApproved={handleApproved}
              onRejected={() => onSelect(undefined)}
              onClose={() => onSelect(undefined)}
            />
          ) : (
            <p className="font-mono text-xs text-muted-foreground">CARGANDO PROPUESTA...</p>
          ))}
      </div>
    </div>
  );
}
