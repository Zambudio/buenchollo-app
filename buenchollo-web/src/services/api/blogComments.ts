import { apiClient } from "./client";

export interface BlogCommentAuthor {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
}

export interface BlogCommentItem {
  id: string;
  blog_post_id: string;
  user_id: string;
  parent_id: string | null;
  content: string;
  votes_up: number;
  votes_down: number;
  created_at: string;
  author: BlogCommentAuthor | null;
  my_vote: number;
}

interface BlogCommentsListResponse {
  comments: BlogCommentItem[];
}

export const blogCommentsApi = {
  /** Lista comentarios de un artículo. Si hay sesión, incluye `my_vote` por comentario. */
  list: (postId: string, withMyVotes: boolean): Promise<BlogCommentItem[]> => {
    const endpoint = withMyVotes
      ? `/blog/posts/${postId}/comments/with-my-votes`
      : `/blog/posts/${postId}/comments`;
    return apiClient.get<BlogCommentsListResponse>(endpoint).then((r) => r.comments);
  },

  create: (postId: string, content: string, parentId: string | null): Promise<BlogCommentItem> =>
    apiClient.post<BlogCommentItem>(`/blog/posts/${postId}/comments`, {
      content,
      parent_id: parentId,
    }),

  remove: (commentId: string): Promise<void> => apiClient.delete(`/blog/comments/${commentId}`),

  /** Vota un comentario. Repetir el mismo voto lo retira. */
  vote: (commentId: string, value: 1 | -1): Promise<{ my_vote: number }> =>
    apiClient.post<{ my_vote: number }>(`/blog/comments/${commentId}/vote`, { vote: value }),
};
