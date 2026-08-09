import { createFileRoute } from "@tanstack/react-router";
import { Skeleton } from "@/components/ui/skeleton";
import { useScheduledTasksConfig } from "@/features/admin/hooks/useScheduledTasks";
import { ScheduledTaskConfigPanel } from "@/features/admin/components/ScheduledTaskConfigPanel";
import { ScheduledTaskRunsPanel } from "@/features/admin/components/ScheduledTaskRunsPanel";

export const Route = createFileRoute("/admin/tareas-programadas")({
  component: AdminScheduledTasks,
});

function AdminScheduledTasks() {
  const { data: tasks, isLoading, isError } = useScheduledTasksConfig();
  const priceCheckTask = tasks?.find((t) => t.task_type === "price_check");

  return (
    <div className="space-y-6">
      <h2 className="font-mono text-sm uppercase text-cyan-glow">Tareas programadas</h2>

      {isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : isError || !priceCheckTask ? (
        <div className="text-center py-12 border border-red-500/30 bg-red-500/5 text-red-400">
          Error al cargar la configuración.
        </div>
      ) : (
        <>
          <ScheduledTaskConfigPanel task={priceCheckTask} />
          <ScheduledTaskRunsPanel taskId={priceCheckTask.id} />
        </>
      )}
    </div>
  );
}
