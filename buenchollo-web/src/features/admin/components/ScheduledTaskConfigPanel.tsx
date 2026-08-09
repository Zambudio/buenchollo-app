/** Configuración + ejecución manual (con confirmación) de una tarea programada. */
import { useState } from "react";
import { Play } from "lucide-react";
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
import { formatPrice } from "@/lib/format";
import type {
  ScheduledTaskCandidate,
  ScheduledTaskConfig,
  ScheduledTaskPreview,
} from "@/services/api/scheduled-tasks";
import {
  useConfirmScheduledTask,
  usePreviewScheduledTask,
  useUpdateScheduledTask,
} from "@/features/admin/hooks/useScheduledTasks";

const REASON_LABEL: Record<ScheduledTaskCandidate["reason"], string> = {
  price_increase: "Subió de precio",
  no_longer_deal: "Ya no es oferta",
  out_of_stock: "Sin stock",
};

const FREQUENCY_LABEL: Record<ScheduledTaskConfig["frequency_preset"], string> = {
  daily: "Diario",
  weekly: "Semanal",
  biweekly: "Cada 2 semanas",
  monthly: "Mensual",
};

export function ScheduledTaskConfigPanel({ task }: { readonly task: ScheduledTaskConfig }) {
  const [pendingPreview, setPendingPreview] = useState<ScheduledTaskPreview | null>(null);
  const update = useUpdateScheduledTask();
  const preview = usePreviewScheduledTask();
  const confirm = useConfirmScheduledTask(task.id);

  const tolerance = task.config.price_tolerance_percent ?? 10;

  const handleRunNow = async () => {
    const result = await preview.mutateAsync(task.id);
    if (result.candidates.length === 0) {
      setPendingPreview(null);
      return;
    }
    setPendingPreview(result);
  };

  const handleConfirm = () => {
    if (!pendingPreview) return;
    confirm.mutate(pendingPreview);
    setPendingPreview(null);
  };

  return (
    <div className="bg-surface-800 border border-surface-700 p-4 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h3 className="font-mono text-sm uppercase text-cyan-glow">Revisión de precios (Amazon)</h3>
        <label className="flex items-center gap-2 text-xs font-mono uppercase">
          <input
            type="checkbox"
            checked={task.enabled}
            onChange={(e) => update.mutate({ id: task.id, data: { enabled: e.target.checked } })}
          />
          Activada
        </label>
      </div>

      <div className="grid sm:grid-cols-3 gap-3">
        <label className="text-xs font-mono uppercase text-muted-foreground">
          Frecuencia
          <select
            value={task.frequency_preset}
            onChange={(e) =>
              update.mutate({
                id: task.id,
                data: { frequency_preset: e.target.value as ScheduledTaskConfig["frequency_preset"] },
              })
            }
            className="mt-1 w-full bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
          >
            {Object.entries(FREQUENCY_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label className="text-xs font-mono uppercase text-muted-foreground">
          Hora (0-23)
          <input
            type="number"
            min={0}
            max={23}
            value={task.run_hour}
            onChange={(e) =>
              update.mutate({ id: task.id, data: { run_hour: Number(e.target.value) } })
            }
            className="mt-1 w-full bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
          />
        </label>

        <label className="text-xs font-mono uppercase text-muted-foreground">
          Tolerancia de precio (%)
          <input
            type="number"
            min={0}
            max={100}
            value={tolerance}
            onChange={(e) =>
              update.mutate({
                id: task.id,
                data: { config: { ...task.config, price_tolerance_percent: Number(e.target.value) } },
              })
            }
            className="mt-1 w-full bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
          />
        </label>
      </div>

      <div className="flex items-center justify-between flex-wrap gap-3 text-xs font-mono text-muted-foreground">
        <span>
          Última ejecución:{" "}
          {task.last_run_at ? new Date(task.last_run_at).toLocaleString("es-ES") : "nunca"}
        </span>
        <button
          type="button"
          onClick={handleRunNow}
          disabled={preview.isPending}
          className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center gap-2 hover:bg-foreground disabled:opacity-50"
        >
          <Play className="size-4" /> {preview.isPending ? "REVISANDO..." : "EJECUTAR AHORA"}
        </button>
      </div>

      <AlertDialog open={!!pendingPreview} onOpenChange={(open) => !open && setPendingPreview(null)}>
        <AlertDialogContent className="max-w-2xl">
          <AlertDialogHeader>
            <AlertDialogTitle>
              Se van a borrar {pendingPreview?.candidates.length ?? 0} chollo(s), ¿deseas continuar?
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="max-h-80 overflow-y-auto mt-2">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="p-2">Título</th>
                      <th className="p-2">Tienda</th>
                      <th className="p-2">Precio</th>
                      <th className="p-2">Motivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingPreview?.candidates.map((c) => (
                      <tr key={c.deal_id} className="border-t border-surface-700">
                        <td className="p-2">{c.title}</td>
                        <td className="p-2">{c.store_name ?? "—"}</td>
                        <td className="p-2">
                          {formatPrice(c.old_price)}
                          {c.new_price != null && <> → {formatPrice(c.new_price)}</>}
                        </td>
                        <td className="p-2">{REASON_LABEL[c.reason]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirm}>Eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
