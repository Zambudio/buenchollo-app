import { apiClient, ApiError } from "./client";
import type { DealCreatePayload, DealDetailData } from "./deals";

export type LinkCheckStatus = "published" | "upcoming" | "in_review" | "ok";
export type SubmissionStatus = "pending" | "approved" | "rejected" | "withdrawn";

export interface DealAuthor {
  username: string | null;
  display_name: string | null;
  avatar_url: string | null;
}

export interface UploadedImage {
  url: string;
  width: number;
  height: number;
}

export interface SubmissionPrefill {
  title: string;
  brand: string | null;
  description: string | null;
  current_price: number | null;
  previous_price: number | null;
  image_url: string | null;
  images: string[];
  expires_at: string | null;
}

export interface LinkCheckResult {
  status: LinkCheckStatus;
  canonical_url: string;
  affiliate_url: string;
  asin: string | null;
  store_id: string | null;
  store_name: string | null;
  is_amazon: boolean;
  previously_published: boolean;
  existing_deal: {
    id: string;
    slug: string;
    title: string;
    image_url: string | null;
    current_price: number | null;
  } | null;
  prefill: SubmissionPrefill | null;
  warnings: string[];
}

export interface SubmissionCreatePayload {
  url: string;
  title: string;
  description?: string;
  current_price: number;
  previous_price?: number;
  coupon_code?: string;
  shipping_info?: string;
  store_name?: string;
  category_id: string;
  subcategory_id?: string;
  starts_at?: string;
  expires_at?: string;
  images: string[];
  image_url?: string;
}

export interface Submission {
  id: string;
  status: SubmissionStatus;
  title: string;
  description: string | null;
  original_url: string;
  affiliate_url: string;
  current_price: number;
  previous_price: number | null;
  coupon_code: string | null;
  shipping_info: string | null;
  store_id: string | null;
  store_name: string | null;
  category_id: string | null;
  subcategory_id: string | null;
  starts_at: string | null;
  expires_at: string | null;
  image_url: string | null;
  images: string[];
  warnings: string[];
  rejection_reason: string | null;
  deal_slug: string | null;
  created_at: string;
}

export interface AdminSubmission extends Submission {
  author: DealAuthor | null;
  previously_published: boolean;
}

export function isSubmissionDuplicateError(e: unknown): e is ApiError {
  return e instanceof ApiError && e.status === 409 && e.data?.code === "SUBMISSION_DUPLICATE";
}

export function isProfileIncompleteError(e: unknown): e is ApiError {
  return e instanceof ApiError && e.status === 403 && e.data?.code === "PROFILE_INCOMPLETE";
}

export const submissionsApi = {
  checkLink: (url: string): Promise<LinkCheckResult> =>
    apiClient.post<LinkCheckResult>("/submissions/check-link", { url }),

  create: (payload: SubmissionCreatePayload): Promise<Submission> =>
    apiClient.post<Submission>("/submissions", payload),

  mine: (limit = 20, offset = 0): Promise<Submission[]> =>
    apiClient.get<Submission[]>(`/submissions/mine?limit=${limit}&offset=${offset}`),

  withdraw: (id: string): Promise<void> =>
    apiClient.delete<void>(`/submissions/${encodeURIComponent(id)}`),

  uploadImage: (file: Blob, filename = "image.png"): Promise<UploadedImage> => {
    const formData = new FormData();
    formData.append("file", file, filename);
    return apiClient.upload<UploadedImage>("/submissions/images", formData);
  },

  importImageUrl: (url: string): Promise<UploadedImage> =>
    apiClient.post<UploadedImage>("/submissions/images/from-url", { url }),
};

export const adminSubmissionsApi = {
  list: (status: SubmissionStatus, limit = 50, offset = 0): Promise<AdminSubmission[]> =>
    apiClient.get<AdminSubmission[]>(
      `/admin/submissions?status=${status}&limit=${limit}&offset=${offset}`,
    ),

  count: (): Promise<{ pending: number }> =>
    apiClient.get<{ pending: number }>("/admin/submissions/count"),

  get: (id: string): Promise<AdminSubmission> =>
    apiClient.get<AdminSubmission>(`/admin/submissions/${encodeURIComponent(id)}`),

  approve: (id: string, payload: DealCreatePayload): Promise<DealDetailData> =>
    apiClient.post<DealDetailData>(`/admin/submissions/${encodeURIComponent(id)}/approve`, payload),

  reject: (id: string, reason: string): Promise<AdminSubmission> =>
    apiClient.post<AdminSubmission>(`/admin/submissions/${encodeURIComponent(id)}/reject`, {
      reason,
    }),
};
