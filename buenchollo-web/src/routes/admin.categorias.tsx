import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { categoriesService, type Category } from "@/services/api/categories";
import { slugify } from "@/lib/format";
import { errorMessage } from "@/lib/errors";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/admin/categorias")({ component: AdminCategories });

function AdminCategories() {
  const [cats, setCats] = useState<Category[]>([]);
  const [name, setName] = useState("");
  const [parentId, setParentId] = useState("");

  const load = () => {
    categoriesService
      .getAdminAll()
      .then(setCats)
      .catch((err: unknown) => toast.error(errorMessage(err)));
  };
  useEffect(() => {
    load();
  }, []);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim().length < 2) return;
    try {
      await categoriesService.create({
        name: name.trim(),
        slug: slugify(name) + "-" + Date.now().toString(36).slice(-4),
        parent_id: parentId || null,
        icon: null,
        display_order: 0,
        is_active: true,
      });
      toast.success("Creada");
      setName("");
      load();
    } catch (error: unknown) {
      toast.error(errorMessage(error));
    }
  };
  const remove = async (id: string) => {
    if (!confirm("¿Eliminar?")) return;
    try {
      await categoriesService.delete(id);
      load();
    } catch (error: unknown) {
      toast.error(errorMessage(error));
    }
  };

  const top = cats.filter((c) => !c.parent_id);
  const inputCls =
    "bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-sm outline-none focus:border-cyan-glow";

  return (
    <div>
      <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4">Categorías</h2>
      <form
        onSubmit={add}
        className="bg-surface-800 border border-surface-700 p-4 mb-6 flex flex-wrap gap-2"
      >
        <input
          placeholder="Nombre"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputCls + " flex-1 min-w-48"}
        />
        <select value={parentId} onChange={(e) => setParentId(e.target.value)} className={inputCls}>
          <option value="">— Categoría principal —</option>
          {top.map((t) => (
            <option key={t.id} value={t.id}>
              Sub de: {t.name}
            </option>
          ))}
        </select>
        <button className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 flex items-center gap-2">
          <Plus className="size-4" /> AÑADIR
        </button>
      </form>
      <div className="space-y-2">
        {top.map((t) => (
          <div key={t.id} className="bg-surface-800 border border-surface-700 p-3">
            <div className="flex items-center justify-between">
              <span className="font-bold">
                {t.name} <span className="font-mono text-xs text-muted-foreground">/{t.slug}</span>
              </span>
              <button onClick={() => remove(t.id)} className="p-1 hover:text-alert-red">
                <Trash2 className="size-4" />
              </button>
            </div>
            <ul className="ml-4 mt-2 space-y-1">
              {cats
                .filter((c) => c.parent_id === t.id)
                .map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center justify-between text-sm font-mono text-muted-foreground"
                  >
                    <span>
                      › {s.name} <span className="text-xs">/{s.slug}</span>
                    </span>
                    <button onClick={() => remove(s.id)} className="p-1 hover:text-alert-red">
                      <Trash2 className="size-3" />
                    </button>
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
