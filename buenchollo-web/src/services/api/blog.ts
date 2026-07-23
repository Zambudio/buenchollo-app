import { apiClient, ApiError } from "./client";
import type { JSONContent } from "@tiptap/core";

/** Body que envía el backend cuando publicar/programar falla por no cumplir
 *  los requisitos mínimos. Status HTTP 400, code === "POST_NOT_PUBLISHABLE". */
export interface PostNotPublishableErrorBody {
  code: "POST_NOT_PUBLISHABLE";
  detail: string;
  missing_fields: string[];
}

const PUBLISH_FIELD_LABELS: Record<string, string> = {
  title: "Título",
  slug: "Slug",
  excerpt: "Extracto",
  content: "Contenido del artículo (no puede estar vacío)",
  cover_image_url: "Imagen de portada",
  cover_image_alt: "Texto alternativo de la portada",
  author_id: "Autor (vuelve a iniciar sesión si el problema persiste)",
  category_id: "Categoría (elige una categoría activa)",
  scheduled_for: "Fecha de programación (debe ser una fecha futura)",
};

/** Type guard: detecta si un error capturado es el "faltan requisitos para
 *  publicar" que el admin debe resolver rellenando esos campos. */
export function isPostNotPublishableError(err: unknown): err is ApiError & {
  data: PostNotPublishableErrorBody;
} {
  return (
    err instanceof ApiError &&
    err.status === 400 &&
    err.data !== null &&
    (err.data as { code?: unknown }).code === "POST_NOT_PUBLISHABLE"
  );
}

/** Traduce el error de publicación a un mensaje legible, listando los
 *  campos que faltan con su nombre en español en vez del nombre técnico
 *  del backend (p. ej. "cover_image_alt"). */
export function formatPostNotPublishableError(
  err: ApiError & { data: PostNotPublishableErrorBody },
): string {
  const labels = err.data.missing_fields.map((field) => PUBLISH_FIELD_LABELS[field] ?? field);
  return `Para publicar, completa antes: ${labels.join(", ")}.`;
}

export type BlogPostStatus = "draft" | "scheduled" | "published" | "archived";

export interface BlogCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  sort_order: number;
}

export interface BlogCategoryCreatePayload {
  name: string;
  slug: string;
  description?: string | null;
  is_active?: boolean;
  sort_order?: number;
}

export type BlogCategoryUpdatePayload = Partial<BlogCategoryCreatePayload>;

export interface AuthorBasic {
  id: string;
  display_name: string | null;
}

export interface BlogDealSummary {
  id: string;
  title: string;
  slug: string;
  image_url: string | null;
  affiliate_url: string;
  store_name: string | null;
  current_price: number | null;
  previous_price: number | null;
  discount_percentage: number | null;
  is_active: boolean;
}

export interface TocEntry {
  level: number;
  text: string;
  id: string;
}

export interface BlogPostCard {
  id: string;
  title: string;
  slug: string;
  excerpt: string | null;
  cover_image_url: string | null;
  cover_image_alt: string | null;
  tags: string[];
  is_featured: boolean;
  published_at: string | null;
  reading_time_minutes: number;
  category: BlogCategory | null;
}

export interface BlogPostPage {
  items: BlogPostCard[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface BlogPostDetail {
  id: string;
  title: string;
  slug: string;
  excerpt: string | null;
  content: JSONContent;
  cover_image_url: string | null;
  cover_image_alt: string | null;
  tags: string[];
  is_featured: boolean;
  status: BlogPostStatus;
  published_at: string | null;
  updated_at: string;
  category: BlogCategory | null;
  author: AuthorBasic | null;
  seo_title: string | null;
  seo_description: string | null;
  canonical_url: string | null;
  og_image_url: string | null;
  reading_time_minutes: number;
  word_count: number;
  toc: TocEntry[];
  has_affiliate_links: boolean;
  products: Record<string, BlogDealSummary>;
  votes_up: number;
  votes_down: number;
}

export interface PostVoteResponse {
  votes_up: number;
  votes_down: number;
  my_vote: number;
}

export interface BlogPostAdminListItem {
  id: string;
  title: string;
  slug: string;
  status: BlogPostStatus;
  cover_image_url: string | null;
  is_featured: boolean;
  updated_at: string;
  published_at: string | null;
  scheduled_for: string | null;
  category: BlogCategory | null;
  author: AuthorBasic | null;
}

export interface BlogPostAdminPage {
  items: BlogPostAdminListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface BlogPostCreatePayload {
  title: string;
  slug?: string | null;
  excerpt?: string | null;
  content?: JSONContent | null;
  cover_image_url?: string | null;
  cover_image_alt?: string | null;
  category_id?: string | null;
  tags?: string[];
  seo_title?: string | null;
  seo_description?: string | null;
  canonical_url?: string | null;
  og_image_url?: string | null;
  is_featured?: boolean;
}

export type BlogPostUpdatePayload = Partial<BlogPostCreatePayload>;

export interface SitemapEntry {
  slug: string;
  updated_at: string;
  published_at: string | null;
}

export interface PublicPostsParams {
  category?: string;
  search?: string;
  featured?: boolean;
  page?: number;
  page_size?: number;
}

export interface AdminPostsParams {
  status?: string;
  category_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

function toQueryString(params: object): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, unknown>)) {
    if (value !== undefined && value !== "") qs.append(key, String(value));
  }
  const str = qs.toString();
  return str ? `?${str}` : "";
}

export const blogService = {
  // --- Público ---
  getPosts: (params: PublicPostsParams = {}): Promise<BlogPostPage> =>
    apiClient.get<BlogPostPage>(`/blog/posts${toQueryString(params)}`),

  getPostBySlug: (slug: string): Promise<BlogPostDetail> =>
    apiClient.get<BlogPostDetail>(`/blog/posts/${encodeURIComponent(slug)}`),

  getRelated: (slug: string, limit = 3): Promise<BlogPostCard[]> =>
    apiClient.get<BlogPostCard[]>(`/blog/posts/${encodeURIComponent(slug)}/related?limit=${limit}`),

  getCategories: (): Promise<BlogCategory[]> => apiClient.get<BlogCategory[]>("/blog/categories"),

  getSitemap: (): Promise<SitemapEntry[]> => apiClient.get<SitemapEntry[]>("/blog/sitemap"),

  /** Vota "¿te ha sido útil?" (1 o -1). Repetir el mismo voto lo retira. Requiere sesión. */
  vote: (postId: string, vote: 1 | -1): Promise<PostVoteResponse> =>
    apiClient.post<PostVoteResponse>(`/blog/posts/${postId}/vote`, { vote }),

  getMyVote: (postId: string): Promise<number> =>
    apiClient.get<{ my_vote: number }>(`/blog/posts/${postId}/my-vote`).then((r) => r.my_vote),

  // --- Admin: artículos ---
  adminList: (params: AdminPostsParams = {}): Promise<BlogPostAdminPage> =>
    apiClient.get<BlogPostAdminPage>(`/blog/admin/posts${toQueryString(params)}`),

  adminGet: (postId: string): Promise<BlogPostDetail> =>
    apiClient.get<BlogPostDetail>(`/blog/admin/posts/${postId}`),

  create: (data: BlogPostCreatePayload): Promise<BlogPostDetail> =>
    apiClient.post<BlogPostDetail>("/blog/admin/posts", data),

  update: (postId: string, data: BlogPostUpdatePayload): Promise<BlogPostDetail> =>
    apiClient.put<BlogPostDetail>(`/blog/admin/posts/${postId}`, data),

  delete: (postId: string): Promise<void> => apiClient.delete(`/blog/admin/posts/${postId}`),

  publish: (postId: string): Promise<BlogPostDetail> =>
    apiClient.post<BlogPostDetail>(`/blog/admin/posts/${postId}/publish`, {}),

  schedule: (postId: string, scheduledFor: string): Promise<BlogPostDetail> =>
    apiClient.post<BlogPostDetail>(`/blog/admin/posts/${postId}/schedule`, {
      scheduled_for: scheduledFor,
    }),

  archive: (postId: string): Promise<BlogPostDetail> =>
    apiClient.post<BlogPostDetail>(`/blog/admin/posts/${postId}/archive`, {}),

  // --- Admin: categorías ---
  adminListCategories: (): Promise<BlogCategory[]> =>
    apiClient.get<BlogCategory[]>("/blog/admin/categories"),

  createCategory: (data: BlogCategoryCreatePayload): Promise<BlogCategory> =>
    apiClient.post<BlogCategory>("/blog/admin/categories", data),

  updateCategory: (categoryId: string, data: BlogCategoryUpdatePayload): Promise<BlogCategory> =>
    apiClient.put<BlogCategory>(`/blog/admin/categories/${categoryId}`, data),

  deleteCategory: (categoryId: string): Promise<void> =>
    apiClient.delete(`/blog/admin/categories/${categoryId}`),
};
