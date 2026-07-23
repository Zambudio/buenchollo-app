import { useQuery } from "@tanstack/react-query";
import { blogService, type PublicPostsParams } from "@/services/api/blog";

export const BLOG_PUBLIC_KEYS = {
  posts: (params: PublicPostsParams) => ["blog", "posts", params] as const,
  post: (slug: string) => ["blog", "post", slug] as const,
  related: (slug: string) => ["blog", "post", slug, "related"] as const,
  categories: ["blog", "categories"] as const,
};

export function useBlogPosts(params: PublicPostsParams) {
  return useQuery({
    queryKey: BLOG_PUBLIC_KEYS.posts(params),
    queryFn: () => blogService.getPosts(params),
    staleTime: 60 * 1000,
  });
}

export function useBlogPost(slug: string) {
  return useQuery({
    queryKey: BLOG_PUBLIC_KEYS.post(slug),
    queryFn: () => blogService.getPostBySlug(slug),
    enabled: !!slug,
    staleTime: 60 * 1000,
  });
}

export function useRelatedPosts(slug: string, limit = 3) {
  return useQuery({
    queryKey: BLOG_PUBLIC_KEYS.related(slug),
    queryFn: () => blogService.getRelated(slug, limit),
    enabled: !!slug,
    staleTime: 60 * 1000,
  });
}

export function useBlogCategories() {
  return useQuery({
    queryKey: BLOG_PUBLIC_KEYS.categories,
    queryFn: () => blogService.getCategories(),
    staleTime: 5 * 60 * 1000,
  });
}
