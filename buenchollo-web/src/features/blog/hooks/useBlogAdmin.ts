import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  blogService,
  formatPostNotPublishableError,
  isPostNotPublishableError,
  type AdminPostsParams,
  type BlogCategoryCreatePayload,
  type BlogCategoryUpdatePayload,
  type BlogPostCreatePayload,
  type BlogPostUpdatePayload,
} from "@/services/api/blog";
import { errorMessage } from "@/lib/errors";

/** Muestra el error de publicación con nombres de campo en español; para
 *  cualquier otro error cae al mensaje genérico de `errorMessage`. */
function toastPublishError(e: unknown) {
  if (isPostNotPublishableError(e)) {
    toast.error(formatPostNotPublishableError(e));
    return;
  }
  toast.error(errorMessage(e));
}

const KEYS = {
  adminList: (params: AdminPostsParams) => ["blog", "admin", "posts", params] as const,
  adminPost: (id: string) => ["blog", "admin", "posts", id] as const,
  adminCategories: ["blog", "admin", "categories"] as const,
};

export function useAdminPosts(params: AdminPostsParams) {
  return useQuery({
    queryKey: KEYS.adminList(params),
    queryFn: () => blogService.adminList(params),
  });
}

export function useAdminPost(postId: string | undefined) {
  return useQuery({
    queryKey: KEYS.adminPost(postId ?? ""),
    queryFn: () => blogService.adminGet(postId as string),
    enabled: !!postId,
  });
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>, postId?: string) {
  qc.invalidateQueries({ queryKey: ["blog", "admin", "posts"] });
  qc.invalidateQueries({ queryKey: ["blog", "posts"] });
  if (postId) qc.invalidateQueries({ queryKey: KEYS.adminPost(postId) });
}

export function useCreatePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BlogPostCreatePayload) => blogService.create(data),
    onSuccess: () => invalidateAll(qc),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useUpdatePost(postId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BlogPostUpdatePayload) => blogService.update(postId, data),
    onSuccess: () => invalidateAll(qc, postId),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useDeletePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) => blogService.delete(postId),
    onSuccess: () => invalidateAll(qc),
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function usePublishPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) => blogService.publish(postId),
    onSuccess: (_data, postId) => {
      invalidateAll(qc, postId);
      toast.success("Artículo publicado");
    },
    onError: toastPublishError,
  });
}

export function useSchedulePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ postId, scheduledFor }: { postId: string; scheduledFor: string }) =>
      blogService.schedule(postId, scheduledFor),
    onSuccess: (_data, { postId }) => {
      invalidateAll(qc, postId);
      toast.success("Artículo programado");
    },
    onError: toastPublishError,
  });
}

export function useArchivePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) => blogService.archive(postId),
    onSuccess: (_data, postId) => {
      invalidateAll(qc, postId);
      toast.success("Artículo archivado");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useAdminCategories() {
  return useQuery({
    queryKey: KEYS.adminCategories,
    queryFn: () => blogService.adminListCategories(),
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BlogCategoryCreatePayload) => blogService.createCategory(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.adminCategories });
      qc.invalidateQueries({ queryKey: ["blog", "categories"] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BlogCategoryUpdatePayload }) =>
      blogService.updateCategory(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.adminCategories });
      qc.invalidateQueries({ queryKey: ["blog", "categories"] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => blogService.deleteCategory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.adminCategories });
      qc.invalidateQueries({ queryKey: ["blog", "categories"] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
}
