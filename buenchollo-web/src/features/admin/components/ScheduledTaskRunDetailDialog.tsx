/** Detalle de un registro de ejecución: lista de chollos borrados + Restaurar. */
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { formatPrice } from "@/lib/format";
import type { ScheduledTaskCandidate } from "@/services/api/scheduled-tasks";
import {
  useRestoreScheduledTaskItem,
  useScheduledTaskRunDetail,
} from "@/features/admin/hooks/useScheduledTasks";

const REASON_LABEL: Record<ScheduledTaskCandidate["reason"], string> = {
  price_increase: "Subió de precio",
  no_longer_deal: "Ya no es oferta",
  out_of_stock: "Sin stock",
};

export function ScheduledTaskRunDetailDialog({
  runId,
  onClose,
}: {
  readonly runId: string | null;
  readonly onClose: () => void;
}) {
  const { data: run, isLoading } = useScheduledTaskRunDetail(runId);
  const restore = useRestoreScheduledTaskItem(runId ?? "");

  return (
    <AlertDialog open={!!runId} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent className="max-w-3xl">
        <AlertDialogHeader>
          <AlertDialogTitle>Chollos afectados en esta ejecución</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="max-h-96 overflow-y-auto mt-2">
              {isLoading ? (
                <p>Cargando...</p>
              ) : (
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="p-2">Título</th>
                      <th className="p-2">Tienda</th>
                      <th className="p-2">Precio</th>
                      <th className="p-2">Motivo</th>
                      <th className="p-2">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {run?.items.map((item) => (
                      <tr key={item.id} className="border-t border-surface-700">
                        <td className="p-2">{item.title}</td>
                        <td className="p-2">{item.store_name ?? "—"}</td>
                        <td className="p-2">
                          {formatPrice(item.old_price)}
                          {item.new_price != null && <> → {formatPrice(item.new_price)}</>}
                        </td>
                        <td className="p-2">{REASON_LABEL[item.reason]}</td>
                        <td className="p-2">
                          {item.restored_at ? (
                            <span className="text-muted-foreground text-xs">Restaurado</span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => restore.mutate(item.id)}
                              disabled={restore.isPending}
                              className="text-cyan-glow text-xs font-mono uppercase hover:underline disabled:opacity-50"
                            >
                              Restaurar
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cerrar</AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
