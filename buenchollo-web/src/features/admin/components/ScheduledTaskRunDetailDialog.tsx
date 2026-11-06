/** Detalle de un registro de ejecución: ofertas terminadas, reactivadas o eliminadas. */
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
import { describeChange, summarizeTransitions } from "@/features/admin/lib/price-check";
import { useScheduledTaskRunDetail } from "@/features/admin/hooks/useScheduledTasks";

export function ScheduledTaskRunDetailDialog({
  runId,
  onClose,
}: {
  readonly runId: string | null;
  readonly onClose: () => void;
}) {
  const { data: run, isLoading } = useScheduledTaskRunDetail(runId);

  return (
    <AlertDialog open={!!runId} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent className="max-w-3xl">
        <AlertDialogHeader>
          <AlertDialogTitle>Cambios de oferta en esta ejecución</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="max-h-96 overflow-y-auto overflow-x-auto mt-2">
              {isLoading ? (
                <p>Cargando...</p>
              ) : (
                <>
                  <p className="mb-2 font-mono text-xs">{summarizeTransitions(run?.items ?? [])}</p>
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="p-2">Título</th>
                        <th className="p-2">Tienda</th>
                        <th className="p-2">Precio</th>
                        <th className="p-2">Cambio</th>
                      </tr>
                    </thead>
                    <tbody>
                      {run?.items.map((item) => (
                        <tr key={item.id} className="border-t border-surface-700">
                          <td className="p-2">
                            {item.reason === "product_purged" ? (
                              item.title
                            ) : (
                              <a href={`/chollo/${item.slug}`} className="hover:text-cyan-glow">
                                {item.title}
                              </a>
                            )}
                          </td>
                          <td className="p-2">{item.store_name ?? "—"}</td>
                          <td className="p-2 whitespace-nowrap">
                            {formatPrice(item.old_price)}
                            {item.new_price != null && <> → {formatPrice(item.new_price)}</>}
                          </td>
                          <td className="p-2">{describeChange(item.transition, item.reason)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
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
