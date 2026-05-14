import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { formatRelativeTime } from "@/lib/format";
import { ArrowUp, ArrowDown, MessageSquare, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface CommentRow {
  id: string;
  deal_id: string;
  user_id: string;
  parent_id: string | null;
  content: string;
  created_at: string;
  votes_up: number;
  votes_down: number;
}

interface ProfileLite {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
}

interface Props {
  dealId: string;
  onCountChange?: () => void;
}

export function Comments({ dealId, onCountChange }: Props) {
  const { user } = useAuth();
  const [comments, setComments] = useState<CommentRow[]>([]);
  const [profiles, setProfiles] = useState<Record<string, ProfileLite>>({});
  const [myVotes, setMyVotes] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState("");

  const load = async () => {
    setLoading(true);
    const { data: cmts } = await supabase
      .from("deal_comments")
      .select("id,deal_id,user_id,parent_id,content,created_at,votes_up,votes_down")
      .eq("deal_id", dealId)
      .order("created_at", { ascending: true });
    const list = (cmts ?? []) as CommentRow[];
    setComments(list);

    const userIds = [...new Set(list.map((c) => c.user_id))];
    if (userIds.length > 0) {
      const { data: profs } = await supabase
        .from("profiles")
        .select("user_id, display_name, avatar_url")
        .in("user_id", userIds);
      const map: Record<string, ProfileLite> = {};
      (profs ?? []).forEach((p: any) => (map[p.user_id] = p));
      setProfiles(map);
    } else {
      setProfiles({});
    }

    if (user && list.length > 0) {
      const { data: votes } = await supabase
        .from("comment_votes")
        .select("comment_id,vote")
        .eq("user_id", user.id)
        .in("comment_id", list.map((c) => c.id));
      const vm: Record<string, number> = {};
      (votes ?? []).forEach((v: any) => (vm[v.comment_id] = v.vote));
      setMyVotes(vm);
    } else {
      setMyVotes({});
    }
    setLoading(false);
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
    const { error } = await supabase.from("deal_comments").insert({
      deal_id: dealId,
      user_id: user.id,
      parent_id: parentId,
      content: trimmed.slice(0, 1000),
    });
    if (error) {
      toast.error("Error al comentar");
      return false;
    }
    await load();
    onCountChange?.();
    return true;
  };

  const vote = async (commentId: string, value: 1 | -1) => {
    if (!user) {
      toast.error("Inicia sesión para votar");
      return;
    }
    const current = myVotes[commentId] ?? 0;
    if (current === value) {
      await supabase.from("comment_votes").delete().eq("comment_id", commentId).eq("user_id", user.id);
    } else {
      await supabase
        .from("comment_votes")
        .upsert({ comment_id: commentId, user_id: user.id, vote: value }, { onConflict: "comment_id,user_id" });
    }
    await load();
  };

  const remove = async (commentId: string, ownerId: string) => {
    if (!user || user.id !== ownerId) return;
    if (!confirm("¿Eliminar este comentario?")) return;
    const { error } = await supabase.from("deal_comments").delete().eq("id", commentId);
    if (error) {
      toast.error("Error al eliminar");
      return;
    }
    await load();
    onCountChange?.();
  };

  const roots = comments.filter((c) => !c.parent_id);
  const childrenOf = (id: string) => comments.filter((c) => c.parent_id === id);

  const renderComment = (c: CommentRow, depth: number) => {
    const prof = profiles[c.user_id];
    const my = myVotes[c.id] ?? 0;
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
