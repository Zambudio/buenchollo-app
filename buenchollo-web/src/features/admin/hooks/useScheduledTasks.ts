import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  scheduledTasksService,
  type ScheduledTaskUpdatePayload,
} from "@/services/api/scheduled-tasks";
import { errorMessage } from "@/lib/errors";

const KEYS = {
  config: ["scheduled-tasks", "config"] as const,
  runs: (taskId: string) => ["scheduled-tasks", taskId, "runs"] as const,
  runDetail: (runId: string) => ["scheduled-tasks", "run", runId] as const,
};

export function useScheduledTasksConfig() {
  return useQuery({ queryKey: KEYS.config, queryFn: scheduledTasksService.list });
}

export function useUpdateScheduledTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ScheduledTaskUpdatePayload }) =>
      scheduledTasksService.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.config }),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function usePreviewScheduledTask() {
  return useMutation({
    mutationFn: (id: string) => scheduledTasksService.preview(id),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useConfirmScheduledTask(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => scheduledTasksService.confirm(taskId),
    onSuccess: (run) => {
      qc.invalidateQueries({ queryKey: KEYS.config });
      qc.invalidateQueries({ queryKey: KEYS.runs(taskId) });
      toast.success(`Revisión aplicada: ${run.total_affected} cambio(s) de oferta`);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useScheduledTaskRuns(taskId: string) {
  return useQuery({
    queryKey: KEYS.runs(taskId),
    queryFn: () => scheduledTasksService.listRuns(taskId),
    enabled: !!taskId,
  });
}

export function useScheduledTaskRunDetail(runId: string | null) {
  return useQuery({
    queryKey: KEYS.runDetail(runId ?? ""),
    queryFn: () => scheduledTasksService.getRunDetail(runId as string),
    enabled: !!runId,
  });
}

export function useDeleteScheduledTaskRun(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => scheduledTasksService.deleteRun(runId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.runs(taskId) }),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useBulkDeleteScheduledTaskRuns(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runIds: string[]) => scheduledTasksService.bulkDeleteRuns(runIds),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.runs(taskId) }),
    onError: (e) => toast.error(errorMessage(e)),
  });
}
