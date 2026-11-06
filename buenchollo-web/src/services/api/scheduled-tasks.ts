import { apiClient } from "./client";

export type FrequencyPreset = "daily" | "weekly" | "biweekly" | "monthly";
export type PriceCheckReason =
  | "price_increase"
  | "no_longer_deal"
  | "out_of_stock"
  | "not_found"
  | "deal_again"
  | "listing_purged"
  | "product_purged";
export type PriceCheckTransition = "offer_ended" | "reactivated" | "purged";

export interface ScheduledTaskConfig {
  id: string;
  task_type: string;
  enabled: boolean;
  frequency_preset: FrequencyPreset;
  run_hour: number;
  config: {
    price_tolerance_percent?: number;
    min_discount_percent?: number;
    purge_after_days?: number;
    [key: string]: unknown;
  };
  last_run_at: string | null;
}

export interface ScheduledTaskUpdatePayload {
  enabled?: boolean;
  frequency_preset?: FrequencyPreset;
  run_hour?: number;
  config?: Record<string, unknown>;
}

export interface ScheduledTaskCandidate {
  deal_id: string;
  title: string;
  slug: string;
  image_url: string | null;
  description: string | null;
  store_id: string | null;
  store_name: string | null;
  category_id: string | null;
  subcategory_id: string | null;
  external_id: string;
  affiliate_url: string;
  source_url: string | null;
  old_price: number;
  new_price: number | null;
  reason: PriceCheckReason;
  transition: PriceCheckTransition;
}

export interface ScheduledTaskPreview {
  total_checked: number;
  candidates: ScheduledTaskCandidate[];
}

export interface ScheduledTaskRun {
  id: string;
  trigger_type: "manual" | "automatic";
  status: "completed" | "failed";
  started_at: string;
  finished_at: string | null;
  total_checked: number;
  total_affected: number;
  triggered_by: string | null;
  error_message: string | null;
}

export interface ScheduledTaskRunItem {
  id: string;
  deal_id_snapshot: string;
  title: string;
  slug: string;
  image_url: string | null;
  store_name: string | null;
  old_price: number;
  new_price: number | null;
  reason: PriceCheckReason;
  transition: PriceCheckTransition;
}

export interface ScheduledTaskRunDetail extends ScheduledTaskRun {
  items: ScheduledTaskRunItem[];
}

export const scheduledTasksService = {
  list: (): Promise<ScheduledTaskConfig[]> => apiClient.get("/admin/scheduled-tasks"),

  update: (id: string, data: ScheduledTaskUpdatePayload): Promise<ScheduledTaskConfig> =>
    apiClient.put(`/admin/scheduled-tasks/${id}`, data),

  preview: (id: string): Promise<ScheduledTaskPreview> =>
    apiClient.post(`/admin/scheduled-tasks/${id}/preview`, {}),

  /** Ejecuta la revisión ahora y aplica todos los cambios (sin selección). */
  confirm: (id: string): Promise<ScheduledTaskRun> =>
    apiClient.post(`/admin/scheduled-tasks/${id}/confirm`, {}),

  listRuns: (id: string): Promise<ScheduledTaskRun[]> =>
    apiClient.get(`/admin/scheduled-tasks/${id}/runs`),

  getRunDetail: (runId: string): Promise<ScheduledTaskRunDetail> =>
    apiClient.get(`/admin/scheduled-tasks/runs/${runId}`),

  deleteRun: (runId: string): Promise<void> =>
    apiClient.delete(`/admin/scheduled-tasks/runs/${runId}`),

  bulkDeleteRuns: (runIds: string[]): Promise<{ deleted: number }> =>
    apiClient.post(`/admin/scheduled-tasks/runs/bulk-delete`, { run_ids: runIds }),
};
