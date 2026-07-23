import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { lazy, Suspense } from "react";
import { useCreatePost } from "@/features/blog/hooks/useBlogAdmin";
import { PostMetadataSidebar } from "@/features/blog/components/admin/PostMetadataSidebar";
import type { BlogPostFormInput } from "@/features/blog/schemas/blogPostSchema";
import type { JSONContent } from "@tiptap/core";

const BlogEditor = lazy(() =>
  import("@/features/blog/components/editor/BlogEditor").then((m) => ({ default: m.BlogEditor })),
);

export const Route = createFileRoute("/admin/blog_/nuevo")({
  component: AdminBlogNew,
});

const EMPTY_DOC: JSONContent = { type: "doc", content: [{ type: "paragraph" }] };

function AdminBlogNew() {
  const navigate = useNavigate();
  const create = useCreatePost();
  const [provisionalId] = useState(() => crypto.randomUUID());
  const [form, setForm] = useState<BlogPostFormInput & { tags: string[] }>({
    title: "",
    excerpt: "",
    cover_image_url: "",
    cover_image_alt: "",
    category_id: "",
    tags: [],
    seo_title: "",
    seo_description: "",
    canonical_url: "",
    og_image_url: "",
    is_featured: false,
  });
  const [content, setContent] = useState<JSONContent>(EMPTY_DOC);

  const saveDraft = async () => {
    if (form.title.trim().length < 3) {
      toast.error("El título debe tener al menos 3 caracteres");
      return;
    }
    try {
      const created = await create.mutateAsync({
        title: form.title,
        excerpt: form.excerpt || null,
        content,
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
      toast.success("Borrador creado");
      navigate({ to: "/admin/blog/$postId", params: { postId: created.id }, replace: true });
    } catch {
      /* el toast de error ya lo muestra la mutación (useCreatePost) */
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="font-mono text-sm uppercase text-cyan-glow">Nuevo artículo</h2>
        <button
          type="button"
          onClick={saveDraft}
          disabled={create.isPending}
          className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 hover:bg-foreground disabled:opacity-50"
        >
          Guardar borrador
        </button>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_280px] gap-4">
        <div className="space-y-3 min-w-0">
          <input
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="p. ej. Los 7 mejores auriculares con cancelación de ruido de 2026"
            aria-label="Título"
            className="w-full bg-surface-900 border border-surface-700 px-3 py-2 text-lg font-bold outline-none focus:border-cyan-glow"
          />
          <textarea
            value={form.excerpt}
            onChange={(e) => setForm((f) => ({ ...f, excerpt: e.target.value }))}
            placeholder="p. ej. Comparamos precio, autonomía y calidad de sonido para ayudarte a elegir sin líos. Obligatorio para publicar."
            aria-label="Extracto"
            rows={2}
            className="w-full bg-surface-900 border border-surface-700 px-3 py-2 text-sm outline-none focus:border-cyan-glow"
          />
          <Suspense fallback={<div className="h-96 border border-surface-700 animate-pulse" />}>
            <BlogEditor
              postId={provisionalId}
              initialContent={content}
              onChange={setContent}
              isPersisted={false}
            />
          </Suspense>
        </div>
        <PostMetadataSidebar form={form} setForm={setForm} postId={provisionalId} />
      </div>
    </div>
  );
}
