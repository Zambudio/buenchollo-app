/** Diálogo de rechazo de una propuesta: motivo predefinido + texto libre. */
import { useEffect, useId, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { adminInputCls } from "../deal-form";
import {
  buildRejectReason,
  REJECT_REASON_MAX,
  REJECT_REASON_MIN,
  REJECT_REASONS,
} from "../submission-form";

interface Props {
  readonly open: boolean;
  readonly busy?: boolean;
  readonly onClose: () => void;
  readonly onConfirm: (reason: string) => void;
}

export function RejectSubmissionDialog({ open, busy = false, onClose, onConfirm }: Props) {
  const [label, setLabel] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const textId = useId();
  const errorId = useId();

  useEffect(() => {
    if (!open) {
      setLabel("");
      setText("");
      setError(null);
    }
  }, [open]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const reason = buildRejectReason(label, text);
    if (reason.length < REJECT_REASON_MIN) {
      setError("Elige un motivo o escribe uno (mínimo 3 caracteres).");
      return;
    }
    if (reason.length > REJECT_REASON_MAX) {
      setError(`El motivo no puede superar los ${REJECT_REASON_MAX} caracteres.`);
      return;
    }
    setError(null);
    onConfirm(reason);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && !busy && onClose()}>
      <DialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-md">
        <form onSubmit={submit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Rechazar propuesta</DialogTitle>
            <DialogDescription>
              El autor verá el motivo en «Mis chollos» y recibirá un aviso.
            </DialogDescription>
          </DialogHeader>
          <fieldset className="space-y-2">
            <legend className="font-mono text-[10px] uppercase text-muted-foreground mb-1">
              Motivo
            </legend>
            {REJECT_REASONS.map((r) => (
              <label key={r} className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  name="reject-reason"
                  value={r}
                  checked={label === r}
                  onChange={() => setLabel(r)}
                  className="accent-cyan-500"
                />
                {r}
              </label>
            ))}
          </fieldset>
          <label htmlFor={textId} className="block">
            <span className="font-mono text-[10px] uppercase text-muted-foreground block mb-1">
              Detalle (opcional)
            </span>
            <textarea
              id={textId}
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              maxLength={REJECT_REASON_MAX}
              aria-invalid={!!error}
              aria-describedby={error ? errorId : undefined}
              className={adminInputCls}
            />
          </label>
          {error && (
            <p id={errorId} role="alert" className="text-xs text-alert-red">
              {error}
            </p>
          )}
          <DialogFooter className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="border border-surface-700 font-mono text-xs px-4 py-2 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={busy}
              className="bg-alert-red text-white font-mono text-xs font-bold px-4 py-2 disabled:opacity-50"
            >
              {busy ? "Rechazando..." : "Rechazar propuesta"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
