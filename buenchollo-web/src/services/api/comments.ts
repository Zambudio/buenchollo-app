import { apiClient } from "./client";

export interface CommentAuthor {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
}

export interface CommentItem {
  id: string;
  deal_id: string;
  user_id: string;
  parent_id: string | null;
  content: string;
  votes_up: number;
  votes_down: number;
  created_at: string;
  author: CommentAuthor | null;
  my_vote: number;
}

interface CommentsListResponse {
  comments: CommentItem[];
}

export const commentsApi = {
  /** Lista comentarios de un chollo. Si hay sesión, devuelve además `my_vote` por comentario. */
  list: (dealId: string, withMyVotes: boolean): Promise<CommentItem[]> => {
    const endpoint = withMyVotes
      ? `/deals/${dealId}/comments/with-my-votes`
      : `/deals/${dealId}/comments`;
    return apiClient.get<CommentsListResponse>(endpoint).then((r) => r.comments);
  },

  create: (dealId: string, content: string, parentId: string | null): Promise<CommentItem> =>
    apiClient.post<CommentItem>(`/deals/${dealId}/comments`, { content, parent_id: parentId }),

  remove: (commentId: string): Promise<void> =>
    apiClient.delete(`/deals/comments/${commentId}`),

  /** Vota un comentario. Repetir el mismo voto lo retira. */
  vote: (commentId: string, value: 1 | -1): Promise<{ my_vote: number }> =>
    apiClient.post<{ my_vote: number }>(`/deals/comments/${commentId}/vote`, { vote: value }),
};
