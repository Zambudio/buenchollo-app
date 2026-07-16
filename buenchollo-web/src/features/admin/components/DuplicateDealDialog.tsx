/** Diálogo de conflicto 409 DUPLICATE_DEAL del admin (TD-03). */
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface Props {
  readonly existingTitle: string | undefined;
  readonly open: boolean;
  readonly onClose: () => void;
  readonly onGoExisting: () => void;
  readonly onOverwrite: () => void;
}

export function DuplicateDealDialog({
  existingTitle,
  open,
  onClose,
  onGoExisting,
  onOverwrite,
}: Props) {
  return (
    <AlertDialog
      open={open}
      onOpenChange={(o) => {
        if (!o) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Chollo duplicado</AlertDialogTitle>
          <AlertDialogDescription>
            Ya existe el chollo «{existingTitle}» con este ASIN. ¿Qué quieres hacer?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 font-mono text-xs uppercase border border-surface-600 hover:border-foreground transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onGoExisting}
            className="px-4 py-2 font-mono text-xs uppercase border border-cyan-glow text-cyan-glow hover:bg-cyan-glow hover:text-surface-900 transition-colors"
          >
            Ir al chollo existente
          </button>
          <button
            type="button"
            onClick={onOverwrite}
            className="px-4 py-2 font-mono text-xs uppercase bg-alert-red text-white hover:opacity-90 transition-opacity"
          >
            Sobrescribir el existente
          </button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
