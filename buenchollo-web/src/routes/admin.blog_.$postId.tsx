import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, lazy, Suspense } from "react";
import { toast } from "sonner";
import { Eye, Send, CalendarClock, Archive, Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  useAdminPost,
  useUpdatePost,
  usePublishPost,
  useSchedulePost,
  useArchivePost,
  useDeletePost,
} from "@/features/blog/hooks/useBlogAdmin";
import { PostMetadataSidebar } from "@/features/blog/components/admin/PostMetadataSidebar";
import type { BlogPostFormInput } from "@/features/blog/schemas/blogPostSchema";
import type { JSONContent } from "@tiptap/core";
import type { BlogPostUpdatePayload } from "@/services/api/blog";

const BlogEditor = lazy(() =>
  import("@/features/blog/components/editor/BlogEditor").then((m) => ({ default: m.BlogEditor })),
);

export const Route = createFileRoute("/admin/blog_/$postId")({
  component: AdminBlogEdit,
});

function AdminBlogEdit() {
  const { postId } = Route.useParams();
  const navigate = useNavigate();
  const { data: post, isLoading } = useAdminPost(postId);
  const update = useUpdatePost(postId);
  const publish = usePublishPost();
  const schedule = useSchedulePost();
  const archive = useArchivePost();
  const del = useDeletePost();

  const [form, setForm] = useState<(BlogPostFormInput & { tags: string[] }) | null>(null);
  const [content, setContent] = useState<JSONContent | null>(null);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduledFor, setScheduledFor] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    if (!post) return;
    setForm({
      title: post.title,
      excerpt: post.excerpt ?? "",
      cover_image_url: post.cover_image_url ?? "",
      cover_image_alt: post.cover_image_alt ?? "",
      category_id: post.category?.id ?? "",
      tags: post.tags,
      seo_title: post.seo_title ?? "",
      seo_description: post.seo_description ?? "",
      canonical_url: post.canonical_url ?? "",
      og_image_url: post.og_image_url ?? "",
      is_featured: post.is_featured,
    });
    setContent(post.content);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [post?.id]);

  if (isLoading || !form || !content || !post) {
    return <div className="h-96 border border-surface-700 animate-pulse" />;
  }

  const buildPayload = (): BlogPostUpdatePayload => ({
    title: form.title,
    excerpt: form.excerpt || null,
    content: content ?? undefined,
    cover_image_url: form.cover_image_url || null,
    cover_image_alt: form.cover_image_alt || null,
    category_id: form.category_id || null,
    tags: form.tags,
    seo_title: form.seo_title || null,
    seo_description: form.seo_description || null,
    canonical_url: form.canonical_url || null,
    og_image_url: form.og_image_url || null,
    is_featured: !!form.is_featured,
  });

  // Las mutaciones (useUpdatePost/usePublishPost/useSchedulePost) ya
  // muestran su propio toast de error en `onError` (con los nombres de
  // campo traducidos para publish/schedule) — aquí solo evitamos seguir al
  // siguiente paso si el anterior falla, sin volver a mostrar el error.
  const saveDraft = async () => {
    try {
      await update.mutateAsync(buildPayload());
      toast.success("Guardado");
    } catch {
      /* el toast ya lo muestra la mutación */
    }
  };

  const publishOrUpdate = async () => {
    try {
      await update.mutateAsync(buildPayload());
      if (post.status !== "published") await publish.mutateAsync(postId);
      else toast.success("Artículo actualizado");
    } catch {
      /* el toast ya lo muestra la mutación */
    }
  };

  const confirmSchedule = async () => {
    if (!scheduledFor) {
      toast.error("Indica fecha y hora");
      return;
    }
    try {
      await update.mutateAsync(buildPayload());
      await schedule.mutateAsync({ postId, scheduledFor: new Date(scheduledFor).toISOString() });
      setScheduleOpen(false);
    } catch {
      /* el toast ya lo muestra la mutación */
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h2 className="font-mono text-sm uppercase text-cyan-glow">
          Editar artículo · <span className="text-muted-foreground">{post.status}</span>
        </h2>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={saveDraft}
            className="border border-surface-700 text-xs font-mono uppercase px-3 py-2 hover:border-cyan-glow"
          >
            Guardar borrador
          </button>
          <Link
            to="/admin/blog/$postId/preview"
            params={{ postId }}
            className="border border-surface-700 text-xs font-mono uppercase px-3 py-2 hover:border-cyan-glow flex items-center gap-1.5"
          >
            <Eye className="size-3.5" /> Previsualizar
          </Link>
          <button
            type="button"
            onClick={() => setScheduleOpen((v) => !v)}
            className="border border-amber-500/50 text-amber-400 text-xs font-mono uppercase px-3 py-2 flex items-center gap-1.5"
          >
            <CalendarClock className="size-3.5" /> Programar
          </button>
          <button
            type="button"
            onClick={publishOrUpdate}
            className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 hover:bg-foreground flex items-center gap-1.5"
          >
            <Send className="size-3.5" /> {post.status === "published" ? "Actualizar" : "Publicar"}
          </button>
          {post.status !== "archived" && (
            <button
              type="button"
              onClick={() => archive.mutate(postId)}
              className="border border-surface-700 text-xs font-mono uppercase px-3 py-2 flex items-center gap-1.5"
            >
              <Archive className="size-3.5" /> Archivar
            </button>
          )}
          <button
            type="button"
            onClick={() => setDeleteOpen(true)}
            className="border border-red-500/40 text-red-400 text-xs font-mono uppercase px-3 py-2 flex items-center gap-1.5"
          >
            <Trash2 className="size-3.5" /> Eliminar
          </button>
        </div>
      </div>

      {scheduleOpen && (
        <div className="mb-4 border border-amber-500/40 bg-amber-500/5 p-3 flex flex-wrap items-end gap-2">
          <div>
            <label
              className="text-xs font-mono uppercase text-muted-foreground"
              htmlFor="schedule-at"
            >
              Fecha y hora de publicación
            </label>
            <input
              id="schedule-at"
              type="datetime-local"
              value={scheduledFor}
              onChange={(e) => setScheduledFor(e.target.value)}
              className="mt-1 bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow block"
            />
          </div>
          <button
            type="button"
            onClick={confirmSchedule}
            className="bg-amber-500 text-surface-900 font-mono text-xs font-bold px-3 py-2"
          >
            Confirmar programación
          </button>
        </div>
      )}

      <div className="grid lg:grid-cols-[minmax(0,1fr)_280px] gap-4">
        <div className="space-y-3 min-w-0">
          <input
            value={form.title}
            onChange={(e) => setForm((f) => f && { ...f, title: e.target.value })}
            placeholder="p. ej. Los 7 mejores auriculares con cancelación de ruido de 2026"
            aria-label="Título"
            className="w-full bg-surface-900 border border-surface-700 px-3 py-2 text-lg font-bold outline-none focus:border-cyan-glow"
          />
          <textarea
            value={form.excerpt}
            onChange={(e) => setForm((f) => f && { ...f, excerpt: e.target.value })}
            placeholder="p. ej. Comparamos precio, autonomía y calidad de sonido para ayudarte a elegir sin líos. Obligatorio para publicar."
            aria-label="Extracto"
            rows={2}
            className="w-full bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
          />
          <Suspense fallback={<div className="h-96 border border-surface-700 animate-pulse" />}>
            <BlogEditor
              postId={postId}
              initialContent={content}
              onChange={setContent}
              isPersisted
              onAutosave={async (doc) => {
                await update.mutateAsync({ content: doc });
              }}
            />
          </Suspense>
        </div>
        <PostMetadataSidebar
          form={form}
          setForm={(fn) => setForm((f) => (f ? fn(f) : f))}
          postId={postId}
        />
      </div>

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar artículo</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará permanentemente «{post.title}». No se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                await del.mutateAsync(postId);
                navigate({ to: "/admin/blog" });
              }}
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
