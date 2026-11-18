import { commentsApi } from "@/services/api/comments";
import { CommentsThread } from "@/features/comments/CommentsThread";

/** Comentarios de un chollo. */
export function Comments({
  dealId,
  onCountChange,
}: {
  dealId: string;
  onCountChange?: () => void;
}) {
  return (
    <CommentsThread
      targetId={dealId}
      api={commentsApi}
      subject="este chollo"
      onCountChange={onCountChange}
    />
  );
}
