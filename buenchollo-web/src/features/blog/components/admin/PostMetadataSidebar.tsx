import { useAuth } from "@/hooks/useAuth";
import { useBlogImages } from "@/features/blog/hooks/useBlogImages";
import { useAdminCategories } from "@/features/blog/hooks/useBlogAdmin";
import type { BlogPostFormInput } from "@/features/blog/schemas/blogPostSchema";

export function PostMetadataSidebar({
  form,
  setForm,
  postId,
}: {
  form: BlogPostFormInput & { tags: string[] };
  setForm: (
    updater: (f: BlogPostFormInput & { tags: string[] }) => BlogPostFormInput & { tags: string[] },
  ) => void;
  postId: string;
}) {
  const { user } = useAuth();
  const { data: categories } = useAdminCategories();
  const { uploadImage, uploading } = useBlogImages(user?.id, postId);

  return (
    <aside className="space-y-4 border border-surface-700 bg-surface-800/40 p-4">
      <div>
        <label
          className="text-xs font-mono uppercase text-muted-foreground"
          htmlFor="post-category"
        >
          Categoría
        </label>
        <select
          id="post-category"
          value={form.category_id ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value || undefined }))}
          className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
        >
          <option value="">Sin categoría</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="text-xs font-mono uppercase text-muted-foreground" htmlFor="post-tags">
          Tags (opcional, separados por coma)
        </label>
        <input
          id="post-tags"
          value={form.tags.join(", ")}
          onChange={(e) =>
            setForm((f) => ({
              ...f,
              tags: e.target.value
                .split(",")
                .map((t) => t.trim())
                .filter(Boolean),
            }))
          }
          placeholder="p. ej. auriculares, bluetooth, comparativa"
          className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
        />
      </div>

      <div>
        <span className="text-xs font-mono uppercase text-muted-foreground">Imagen de portada</span>
        {form.cover_image_url && (
          <img
            src={String(form.cover_image_url)}
            alt=""
            className="w-full h-32 object-cover rounded mt-1"
          />
        )}
        <label className="mt-2 block text-xs font-mono uppercase border border-surface-700 px-3 py-2 text-center cursor-pointer">
          {uploading ? "Subiendo..." : "Subir imagen"}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,image/avif"
            className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const url = await uploadImage(file);
              if (url) setForm((f) => ({ ...f, cover_image_url: url }));
            }}
          />
        </label>
        <label
          className="text-xs font-mono uppercase text-muted-foreground mt-2 block"
          htmlFor="post-cover-alt"
        >
          Alt de portada (obligatorio para publicar)
        </label>
        <input
          id="post-cover-alt"
          value={String(form.cover_image_alt ?? "")}
          onChange={(e) => setForm((f) => ({ ...f, cover_image_alt: e.target.value }))}
          placeholder="p. ej. Auriculares inalámbricos sobre una mesa de madera"
          className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
        />
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={!!form.is_featured}
          onChange={(e) => setForm((f) => ({ ...f, is_featured: e.target.checked }))}
        />
        Artículo destacado
      </label>

      <details className="text-sm">
        <summary className="cursor-pointer font-mono text-xs uppercase text-muted-foreground">
          SEO (todo opcional)
        </summary>
        <div className="space-y-2 mt-2">
          <div>
            <label className="text-xs text-muted-foreground" htmlFor="seo-title">
              Título SEO — vacío usa el título del artículo
            </label>
            <input
              id="seo-title"
              value={String(form.seo_title ?? "")}
              onChange={(e) => setForm((f) => ({ ...f, seo_title: e.target.value }))}
              placeholder="p. ej. Mejores auriculares 2026: guía de compra y precios"
              className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground" htmlFor="seo-desc">
              Descripción SEO — vacío usa el extracto
            </label>
            <textarea
              id="seo-desc"
              value={String(form.seo_description ?? "")}
              onChange={(e) => setForm((f) => ({ ...f, seo_description: e.target.value }))}
              placeholder="p. ej. Comparativa 2026 de los mejores auriculares: precio, autonomía y sonido."
              className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
              rows={2}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground" htmlFor="canonical-url">
              URL canónica — vacío usa la URL real del artículo
            </label>
            <input
              id="canonical-url"
              value={String(form.canonical_url ?? "")}
              onChange={(e) => setForm((f) => ({ ...f, canonical_url: e.target.value }))}
              placeholder="https://buenchollotech.com/blog/mi-articulo"
              className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground" htmlFor="og-image">
              Imagen Open Graph — vacío usa la portada
            </label>
            <input
              id="og-image"
              value={String(form.og_image_url ?? "")}
              onChange={(e) => setForm((f) => ({ ...f, og_image_url: e.target.value }))}
              placeholder="https://.../imagen-para-compartir.png"
              className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
            />
          </div>
        </div>
      </details>
    </aside>
  );
}
