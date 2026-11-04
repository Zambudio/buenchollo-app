/** Consultas y mutaciones de la cola de moderación de propuestas. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { DealCreatePayload } from "@/services/api/deals";
import { adminSubmissionsApi, type SubmissionStatus } from "@/services/api/submissions";

export const ADMIN_SUBMISSIONS_KEY = ["admin", "submissions"] as const;
export const ADMIN_SUBMISSIONS_COUNT_KEY = [...ADMIN_SUBMISSIONS_KEY, "count"] as const;

export function useAdminSubmissionsList(status: SubmissionStatus) {
  return useQuery({
    queryKey: [...ADMIN_SUBMISSIONS_KEY, "list", status],
    queryFn: () => adminSubmissionsApi.list(status),
  });
}

export function useAdminSubmission(id: string | undefined) {
  return useQuery({
    queryKey: [...ADMIN_SUBMISSIONS_KEY, "detail", id],
    queryFn: () => adminSubmissionsApi.get(id as string),
    enabled: !!id,
    retry: false,
  });
}

export function useAdminSubmissionsCount(enabled: boolean) {
  return useQuery({
    queryKey: ADMIN_SUBMISSIONS_COUNT_KEY,
    queryFn: () => adminSubmissionsApi.count(),
    enabled,
    refetchInterval: enabled ? 60_000 : false,
  });
}

function useInvalidateSubmissions() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ADMIN_SUBMISSIONS_KEY });
}

export function useApproveSubmission() {
  const invalidate = useInvalidateSubmissions();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: DealCreatePayload }) =>
      adminSubmissionsApi.approve(id, payload),
    onSuccess: () => {
      void invalidate();
    },
  });
}

export function useRejectSubmission() {
  const invalidate = useInvalidateSubmissions();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      adminSubmissionsApi.reject(id, reason),
    onSuccess: () => {
      void invalidate();
    },
  });
}
