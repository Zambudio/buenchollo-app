import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowLeft, Trash2, Pencil } from "lucide-react";
import { toast } from "sonner";
import {
  useAdminCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from "@/features/blog/hooks/useBlogAdmin";
import { blogCategoryFormSchema } from "@/features/blog/schemas/blogPostSchema";
import { slugify } from "@/features/blog/utils/slugify";
import { errorMessage } from "@/lib/errors";
import type { BlogCategory } from "@/services/api/blog";

export const Route = createFileRoute("/admin/blog_/categorias")({
  component: AdminBlogCategories,
});

const EMPTY = { name: "", slug: "", description: "", is_active: true, sort_order: 0 };

function AdminBlogCategories() {
  const { data: categories, isLoading } = useAdminCategories();
  const create = useCreateCategory();
  const update = useUpdateCategory();
  const del = useDeleteCategory();
  const [form, setForm] = useState(EMPTY);
  const [editing, setEditing] = useState<BlogCategory | null>(null);
  const [pendingDelete, setPendingDelete] = useState<BlogCategory | null>(null);
  // El slug se autocompleta desde el nombre solo mientras el admin no lo
  // haya tocado a mano (al crear) — al editar una categoría existente no
  // queremos regenerarlo nunca solo.
  const [slugAutoFollowsName, setSlugAutoFollowsName] = useState(true);

  const startEdit = (c: BlogCategory) => {
    setEditing(c);
    setSlugAutoFollowsName(false);
    setForm({
      name: c.name,
      slug: c.slug,
      description: c.description ?? "",
      is_active: c.is_active,
      sort_order: c.sort_order,
    });
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = blogCategoryFormSchema.safeParse(form);
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? "Datos inválidos");
      return;
    }
    try {
      if (editing) {
        await update.mutateAsync({ id: editing.id, data: parsed.data });
        toast.success("Categoría actualizada");
      } else {
        await create.mutateAsync(parsed.data);
        toast.success("Categoría creada");
      }
      setForm(EMPTY);
      setEditing(null);
      setSlugAutoFollowsName(true);
    } catch (e: unknown) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <div>
      <Link
        to="/admin/blog"
        className="inline-flex items-center gap-1.5 text-xs font-mono uppercase text-muted-foreground hover:text-cyan-glow mb-4"
      >
        <ArrowLeft className="size-3.5" /> Volver al blog
      </Link>
      <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4">Categorías del blog</h2>

      <form
        onSubmit={submit}
        className="grid sm:grid-cols-2 gap-3 mb-6 border border-surface-700 p-4 bg-surface-800/40"
      >
        <div>
          <label className="text-xs font-mono uppercase text-muted-foreground" htmlFor="cat-name">
            Nombre
          </label>
          <input
            id="cat-name"
            value={form.name}
            onChange={(e) => {
              const name = e.target.value;
              // Autocompleta el slug a partir del nombre mientras el admin
              // no lo haya editado a mano (evita que "no sepa qué poner").
              const autoSlug = slugAutoFollowsName ? slugify(name) : form.slug;
              setForm({ ...form, name, slug: autoSlug });
            }}
            placeholder="p. ej. Auriculares"
            className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
          />
        </div>
        <div>
          <label className="text-xs font-mono uppercase text-muted-foreground" htmlFor="cat-slug">
            Slug (parte de la URL, se rellena solo)
          </label>
          <input
            id="cat-slug"
            value={form.slug}
            onChange={(e) => {
              setSlugAutoFollowsName(false);
              setForm({ ...form, slug: e.target.value });
            }}
            placeholder="p. ej. auriculares"
            className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="text-xs font-mono uppercase text-muted-foreground" htmlFor="cat-desc">
            Descripción (opcional, solo uso interno)
          </label>
          <input
            id="cat-desc"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="p. ej. Guías y comparativas de auriculares y cascos"
            className="mt-1 w-full bg-surface-900 border border-surface-700 px-2 py-1.5 text-sm outline-none focus:border-cyan-glow"
          />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
          Activa
        </label>
        <div className="sm:col-span-2 flex gap-2">
          <button
            type="submit"
            className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 hover:bg-foreground"
          >
            {editing ? "Guardar cambios" : "Crear categoría"}
          </button>
          {editing && (
            <button
              type="button"
              onClick={() => {
                setEditing(null);
                setForm(EMPTY);
                setSlugAutoFollowsName(true);
              }}
              className="border border-surface-700 text-xs font-mono uppercase px-4 py-2"
            >
              Cancelar
            </button>
          )}
        </div>
      </form>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando...</p>
      ) : (
        <ul className="divide-y divide-surface-700 border border-surface-700">
          {categories?.map((c) => (
            <li key={c.id} className="flex items-center justify-between px-3 py-2">
              <div>
                <p className="font-medium">
                  {c.name}{" "}
                  {!c.is_active && (
                    <span className="text-xs text-muted-foreground">(inactiva)</span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground font-mono">{c.slug}</p>
              </div>
              <div className="flex gap-1">
                <button
                  type="button"
                  aria-label={`Editar ${c.name}`}
                  onClick={() => startEdit(c)}
                  className="p-1.5 hover:text-cyan-glow"
                >
                  <Pencil className="size-4" />
                </button>
                <button
                  type="button"
                  aria-label={`Eliminar ${c.name}`}
                  onClick={() => setPendingDelete(c)}
                  className="p-1.5 hover:text-red-400"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {pendingDelete && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-surface-800 border border-surface-700 p-5 max-w-sm w-full">
            <p className="font-bold mb-2">Eliminar categoría</p>
            <p className="text-sm text-muted-foreground mb-4">
              ¿Eliminar «{pendingDelete.name}»? Los artículos quedarán sin categoría.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setPendingDelete(null)}
                className="border border-surface-700 text-xs font-mono uppercase px-3 py-1.5"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await del.mutateAsync(pendingDelete.id);
                    toast.success("Categoría eliminada");
                  } catch (e: unknown) {
                    toast.error(errorMessage(e));
                  }
                  setPendingDelete(null);
                }}
                className="bg-red-500 text-white text-xs font-mono uppercase px-3 py-1.5"
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
