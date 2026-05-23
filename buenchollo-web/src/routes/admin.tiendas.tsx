import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { storesService, type Store, type StoreCreate } from "@/services/api/stores";
import { slugify } from "@/lib/format";
import { Plus, Pencil, Trash2, X, Check } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/admin/tiendas")({ component: AdminStores });

const inputCls = "bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-sm outline-none focus:border-cyan-glow w-full";

function AdminStores() {
  const [stores, setStores] = useState<Store[]>([]);
  const [form, setForm] = useState<StoreCreate>({ name: "", slug: "", domain: "", logo_url: "", affiliate_id: "", affiliate_url_template: "", is_active: true });
  const [editing, setEditing] = useState<Store | null>(null);

  const load = () => storesService.getAdminAll().then(setStores).catch(e => toast.error(e.message));
  useEffect(() => { load(); }, []);

  const handleNameChange = (name: string) => {
    setForm(f => ({ ...f, name, slug: slugify(name) + "-" + Date.now().toString(36).slice(-4) }));
  };

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.name.trim().length < 2) return;
    try {
      await storesService.create({ ...form, name: form.name.trim() });
      toast.success("Tienda creada");
      setForm({ name: "", slug: "", domain: "", logo_url: "", affiliate_id: "", affiliate_url_template: "", is_active: true });
      load();
    } catch (e: any) { toast.error(e.message); }
  };

  const save = async () => {
    if (!editing) return;
    try {
      await storesService.update(editing.id, {
        name: editing.name,
        slug: editing.slug,
        domain: editing.domain,
        logo_url: editing.logo_url,
        affiliate_id: editing.affiliate_id,
        affiliate_url_template: editing.affiliate_url_template,
        is_active: editing.is_active,
      });
      toast.success("Guardado");
      setEditing(null);
      load();
    } catch (e: any) { toast.error(e.message); }
  };

  const remove = async (id: string) => {
    if (!confirm("¿Eliminar tienda?")) return;
    try {
      await storesService.delete(id);
      load();
    } catch (e: any) { toast.error(e.message); }
  };

  return (
    <div>
      <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4">Tiendas</h2>

      {/* Formulario nueva tienda */}
      <form onSubmit={add} className="bg-surface-800 border border-surface-700 p-4 mb-6 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="font-mono text-xs text-muted-foreground mb-1 block">NOMBRE *</label>
            <input placeholder="Amazon" value={form.name} onChange={e => handleNameChange(e.target.value)} className={inputCls} />
          </div>
          <div>
            <label className="font-mono text-xs text-muted-foreground mb-1 block">SLUG *</label>
            <input placeholder="amazon" value={form.slug} onChange={e => setForm(f => ({ ...f, slug: e.target.value }))} className={inputCls} />
          </div>
          <div>
            <label className="font-mono text-xs text-muted-foreground mb-1 block">DOMINIO</label>
            <input placeholder="amazon.es" value={form.domain ?? ""} onChange={e => setForm(f => ({ ...f, domain: e.target.value || null }))} className={inputCls} />
          </div>
          <div>
            <label className="font-mono text-xs text-muted-foreground mb-1 block">LOGO URL</label>
            <input placeholder="https://..." value={form.logo_url ?? ""} onChange={e => setForm(f => ({ ...f, logo_url: e.target.value || null }))} className={inputCls} />
          </div>
          <div>
            <label className="font-mono text-xs text-muted-foreground mb-1 block">AFFILIATE ID</label>
            <input placeholder="buenchollo0b-21" value={form.affiliate_id ?? ""} onChange={e => setForm(f => ({ ...f, affiliate_id: e.target.value || null }))} className={inputCls} />
          </div>
          <div>
            <label className="font-mono text-xs text-muted-foreground mb-1 block">URL TEMPLATE</label>
            <input placeholder="https://amzn.to/{{asin}}" value={form.affiliate_url_template ?? ""} onChange={e => setForm(f => ({ ...f, affiliate_url_template: e.target.value || null }))} className={inputCls} />
          </div>
        </div>
        <button type="submit" className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center gap-2">
          <Plus className="size-4" /> AÑADIR TIENDA
        </button>
      </form>

      {/* Lista */}
      <div className="space-y-2">
        {stores.map(s => (
          <div key={s.id} className="bg-surface-800 border border-surface-700 p-3">
            {editing?.id === s.id ? (
              <div className="space-y-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input value={editing.name} onChange={e => setEditing(ed => ed && ({ ...ed, name: e.target.value }))} className={inputCls} placeholder="Nombre" />
                  <input value={editing.slug} onChange={e => setEditing(ed => ed && ({ ...ed, slug: e.target.value }))} className={inputCls} placeholder="Slug" />
                  <input value={editing.domain ?? ""} onChange={e => setEditing(ed => ed && ({ ...ed, domain: e.target.value || null }))} className={inputCls} placeholder="Dominio" />
                  <input value={editing.logo_url ?? ""} onChange={e => setEditing(ed => ed && ({ ...ed, logo_url: e.target.value || null }))} className={inputCls} placeholder="Logo URL" />
                  <input value={editing.affiliate_id ?? ""} onChange={e => setEditing(ed => ed && ({ ...ed, affiliate_id: e.target.value || null }))} className={inputCls} placeholder="Affiliate ID" />
                  <input value={editing.affiliate_url_template ?? ""} onChange={e => setEditing(ed => ed && ({ ...ed, affiliate_url_template: e.target.value || null }))} className={inputCls} placeholder="URL Template" />
                </div>
                <div className="flex items-center gap-2">
                  <label className="font-mono text-xs flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={editing.is_active} onChange={e => setEditing(ed => ed && ({ ...ed, is_active: e.target.checked }))} />
                    ACTIVA
                  </label>
                  <button type="button" onClick={save} className="ml-auto p-1 hover:text-cyan-glow"><Check className="size-4" /></button>
                  <button type="button" onClick={() => setEditing(null)} className="p-1 hover:text-muted-foreground"><X className="size-4" /></button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-3 min-w-0">
                  {s.logo_url && <img src={s.logo_url} alt={s.name} className="size-6 object-contain shrink-0" />}
                  <div className="min-w-0">
                    <span className="font-bold">{s.name}</span>
                    <span className="font-mono text-xs text-muted-foreground ml-2">/{s.slug}</span>
                    {s.domain && <span className="font-mono text-xs text-muted-foreground ml-2">· {s.domain}</span>}
                    {!s.is_active && <span className="ml-2 font-mono text-xs text-alert-red">INACTIVA</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button type="button" onClick={() => setEditing(s)} className="p-1 hover:text-cyan-glow"><Pencil className="size-4" /></button>
                  <button type="button" onClick={() => remove(s.id)} className="p-1 hover:text-alert-red"><Trash2 className="size-4" /></button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
