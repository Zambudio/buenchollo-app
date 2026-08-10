/** Listado de registros de ejecución de una tarea programada, con selección
 *  múltiple para borrado en bloque y acceso al detalle de cada uno. */
import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
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
import { formatRelativeTime } from "@/lib/format";
import {
  useBulkDeleteScheduledTaskRuns,
  useDeleteScheduledTaskRun,
  useScheduledTaskRuns,
} from "@/features/admin/hooks/useScheduledTasks";
import { ScheduledTaskRunDetailDialog } from "@/features/admin/components/ScheduledTaskRunDetailDialog";

const TRIGGER_LABEL = { manual: "Manual", automatic: "Automática" } as const;

export function ScheduledTaskRunsPanel({ taskId }: { readonly taskId: string }) {
  const { data: runs, isLoading } = useScheduledTaskRuns(taskId);
  const deleteRun = useDeleteScheduledTaskRun(taskId);
  const bulkDelete = useBulkDeleteScheduledTaskRuns(taskId);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detailRunId, setDetailRunId] = useState<string | null>(null);
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);

  const allSelected = !!runs?.length && runs.every((r) => selected.has(r.id));

  const toggleAll = () => {
    if (!runs) return;
    setSelected(allSelected ? new Set() : new Set(runs.map((r) => r.id)));
  };

  const toggleOne = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBulkDelete = () => {
    bulkDelete.mutate(Array.from(selected));
    setSelected(new Set());
    setConfirmBulkDelete(false);
  };

  if (isLoading) return <p className="text-sm text-muted-foreground">Cargando registros...</p>;

  return (
    <div className="bg-surface-800 border border-surface-700 overflow-x-auto">
      <div className="flex items-center justify-between p-3 border-b border-surface-700">
        <h3 className="font-mono text-sm uppercase text-cyan-glow">Registro de ejecuciones</h3>
        {selected.size > 0 && (
          <button
            type="button"
            onClick={() => setConfirmBulkDelete(true)}
            className="flex items-center gap-2 text-xs font-mono uppercase text-alert-red hover:underline"
          >
            <Trash2 className="size-4" /> Eliminar {selected.size} seleccionado(s)
          </button>
        )}
      </div>
      <table className="w-full text-sm">
        <thead className="border-b border-surface-700 font-mono text-xs uppercase text-muted-foreground">
          <tr>
            <th className="p-3 w-10">
              <Checkbox checked={allSelected} onCheckedChange={toggleAll} aria-label="Seleccionar todos" />
            </th>
            <th className="text-left p-3">Fecha</th>
            <th className="text-left p-3">Tipo</th>
            <th className="text-right p-3">Revisados</th>
            <th className="text-right p-3">Borrados</th>
            <th className="p-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {runs?.map((run) => (
            <tr key={run.id} className="border-b border-surface-700/50 hover:bg-surface-700/30">
              <td className="p-3">
                <Checkbox
                  checked={selected.has(run.id)}
                  onCheckedChange={() => toggleOne(run.id)}
                  aria-label={`Seleccionar registro del ${run.started_at}`}
                />
              </td>
              <td className="p-3 text-muted-foreground font-mono text-xs">
                {formatRelativeTime(run.started_at)}
              </td>
              <td className="p-3 font-mono text-xs uppercase">{TRIGGER_LABEL[run.trigger_type]}</td>
              <td className="p-3 text-right font-mono">{run.total_checked}</td>
              <td className="p-3 text-right font-mono text-alert-red">{run.total_affected}</td>
              <td className="p-3 flex gap-1">
                <button
                  type="button"
                  onClick={() => setDetailRunId(run.id)}
                  className="text-xs font-mono uppercase text-cyan-glow hover:underline"
                >
                  Ver
                </button>
                <button
                  type="button"
                  onClick={() => {
                    deleteRun.mutate(run.id);
                    setSelected((prev) => {
                      const next = new Set(prev);
                      next.delete(run.id);
                      return next;
                    });
                  }}
                  className="p-1 hover:text-alert-red"
                  title="Eliminar registro"
                >
                  <Trash2 className="size-4" />
                </button>
              </td>
            </tr>
          ))}
          {runs?.length === 0 && (
            <tr>
              <td colSpan={6} className="p-6 text-center text-muted-foreground font-mono text-xs">
                SIN_EJECUCIONES
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <ScheduledTaskRunDetailDialog runId={detailRunId} onClose={() => setDetailRunId(null)} />

      <AlertDialog open={confirmBulkDelete} onOpenChange={setConfirmBulkDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar {selected.size} registro(s)</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará permanentemente los registros seleccionados. No se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleBulkDelete}>Eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
