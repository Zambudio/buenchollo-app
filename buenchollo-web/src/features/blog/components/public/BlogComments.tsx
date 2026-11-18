import { blogCommentsApi } from "@/services/api/blogComments";
import { CommentsThread } from "@/features/comments/CommentsThread";

/** Comentarios de un artículo del blog. */
export function BlogComments({ postId }: { postId: string }) {
  return (
    <CommentsThread
      targetId={postId}
      api={blogCommentsApi}
      subject="este artículo"
      className="mt-10 not-prose"
    />
  );
}
