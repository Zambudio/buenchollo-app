import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { formatRelativeTime } from "@/lib/format";
import { commentsApi, type CommentItem } from "@/services/api/comments";
import { ArrowUp, ArrowDown, MessageSquare, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface Props {
  dealId: string;
  onCountChange?: () => void;
}

export function Comments({ dealId, onCountChange }: Props) {
  const { user } = useAuth();
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const list = await commentsApi.list(dealId, !!user);
      setComments(list);
    } catch {
      toast.error("No se pudieron cargar los comentarios");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dealId, user?.id]);

  const post = async (content: string, parentId: string | null) => {
    if (!user) {
      toast.error("Inicia sesión para comentar");
      return false;
    }
    const trimmed = content.trim();
    if (trimmed.length < 2) {
      toast.error("Comentario demasiado corto");
      return false;
    }
    try {
      await commentsApi.create(dealId, trimmed.slice(0, 1000), parentId);
      await load();
      onCountChange?.();
      return true;
    } catch {
      toast.error("Error al comentar");
      return false;
    }
  };

  const vote = async (commentId: string, value: 1 | -1) => {
    if (!user) {
      toast.error("Inicia sesión para votar");
      return;
    }
    try {
      await commentsApi.vote(commentId, value);
      await load();
    } catch {
      toast.error("No se pudo registrar el voto");
    }
  };

  const remove = async (commentId: string, ownerId: string) => {
    if (!user || user.id !== ownerId) return;
    if (!confirm("¿Eliminar este comentario?")) return;
    try {
      await commentsApi.remove(commentId);
      await load();
      onCountChange?.();
    } catch {
      toast.error("Error al eliminar");
    }
  };

  const roots = comments.filter((c) => !c.parent_id);
  const childrenOf = (id: string) => comments.filter((c) => c.parent_id === id);

  const renderComment = (c: CommentItem, depth: number) => {
    const prof = c.author;
    const my = c.my_vote ?? 0;
    const score = (c.votes_up ?? 0) - (c.votes_down ?? 0);
    const kids = childrenOf(c.id);
    return (
      <div key={c.id} className={depth > 0 ? "ml-4 sm:ml-8 border-l-2 border-surface-700 pl-3 sm:pl-4 mt-3" : ""}>
        <div className="bg-surface-800 border border-surface-700 p-3 sm:p-4">
          <div className="flex items-center gap-2 mb-2 font-mono text-xs">
            {prof?.avatar_url ? (
              <img src={prof.avatar_url} alt="" className="size-6 rounded-full object-cover" />
            ) : (
              <div className="size-6 rounded-full bg-surface-700 flex items-center justify-center text-[10px] text-cyan-glow">
                {(prof?.display_name ?? "U").slice(0, 1).toUpperCase()}
              </div>
            )}
            <span className="text-cyan-glow">@{prof?.display_name ?? "usuario"}</span>
            <span className="text-muted-foreground">{formatRelativeTime(c.created_at)}</span>
            {user?.id === c.user_id && (
              <button onClick={() => remove(c.id, c.user_id)} className="ml-auto text-muted-foreground hover:text-alert-red" title="Eliminar">
                <Trash2 className="size-3.5" />
              </button>
            )}
          </div>
          <p className="text-sm whitespace-pre-line break-words">{c.content}</p>
          <div className="flex items-center gap-1 mt-3 font-mono text-xs">
            <button
              onClick={() => vote(c.id, 1)}
              className={`flex items-center gap-1 px-2 py-1 border ${my === 1 ? "border-cyan-glow text-cyan-glow bg-cyan-glow/10" : "border-surface-700 hover:border-cyan-glow"}`}
              aria-label="Me gusta"
            >
              <ArrowUp className="size-3.5" /> {c.votes_up}
            </button>
            <button
              onClick={() => vote(c.id, -1)}
              className={`flex items-center gap-1 px-2 py-1 border ${my === -1 ? "border-alert-red text-alert-red bg-alert-red/10" : "border-surface-700 hover:border-alert-red"}`}
              aria-label="No me gusta"
            >
              <ArrowDown className="size-3.5" /> {c.votes_down}
            </button>
            <span className={`px-2 py-1 ${score > 0 ? "text-cyan-glow" : score < 0 ? "text-alert-red" : "text-muted-foreground"}`}>
              {score > 0 ? "+" : ""}
              {score}
            </span>
            <button
              onClick={() => {
                setReplyTo(replyTo === c.id ? null : c.id);
                setReplyText("");
              }}
              className="ml-auto flex items-center gap-1 px-2 py-1 border border-surface-700 hover:border-cyan-glow"
            >
              <MessageSquare className="size-3.5" /> Responder
            </button>
          </div>

          {replyTo === c.id && (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const ok = await post(replyText, c.id);
                if (ok) {
                  setReplyText("");
                  setReplyTo(null);
                }
              }}
              className="mt-3"
            >
              <textarea
                value={replyText}
                onChange={(e) => setReplyText(e.target.value.slice(0, 1000))}
                placeholder={user ? `Responder a @${prof?.display_name ?? "usuario"}...` : "Inicia sesión para responder"}
                disabled={!user}
                rows={2}
                className="w-full bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow disabled:opacity-50"
              />
              <div className="flex gap-2 mt-2">
                <button
                  type="submit"
                  disabled={!user || replyText.trim().length < 2}
                  className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-3 py-1.5 hover:bg-foreground disabled:opacity-50"
                >
                  [ RESPONDER ]
                </button>
                <button
                  type="button"
                  onClick={() => setReplyTo(null)}
                  className="border border-surface-700 font-mono text-xs px-3 py-1.5 hover:border-alert-red"
                >
                  Cancelar
                </button>
              </div>
            </form>
          )}
        </div>
        {kids.map((k) => renderComment(k, depth + 1))}
      </div>
    );
  };

  return (
    <section className="mt-12">
      <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4 border-b border-surface-700 pb-2">
        Comentarios ({comments.length})
      </h2>

      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const ok = await post(text, null);
          if (ok) setText("");
        }}
        className="mb-6"
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, 1000))}
          placeholder={user ? "Comparte tu opinión sobre este chollo..." : "Inicia sesión para comentar"}
          disabled={!user}
          rows={3}
          className="w-full bg-surface-800 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow disabled:opacity-50"
        />
        <div className="flex justify-between items-center mt-2">
          <span className="font-mono text-[10px] text-muted-foreground">{text.length}/1000</span>
          <button
            type="submit"
            disabled={!user || text.trim().length < 2}
            className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 hover:bg-foreground disabled:opacity-50"
          >
            [ ENVIAR ]
          </button>
        </div>
      </form>

      <div className="space-y-3">
        {loading && <p className="text-muted-foreground text-sm font-mono">Cargando comentarios...</p>}
        {!loading && roots.length === 0 && (
          <p className="text-muted-foreground text-sm font-mono">Sé el primero en comentar.</p>
        )}
        {!loading && roots.map((c) => renderComment(c, 0))}
      </div>
    </section>
  );
}
