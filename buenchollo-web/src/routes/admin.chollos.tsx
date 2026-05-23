import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState, useRef } from "react";
import { dealsService } from "@/services/api/deals";
import { categoriesService } from "@/services/api/categories";
import { storesService } from "@/services/api/stores";
import { formatPrice, formatRelativeTime, slugify } from "@/lib/format";
import { Plus, Trash2, Edit3, Upload, X, GripVertical, Wand2, Send, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { TelegramPanel } from "@/components/TelegramPanel";

export const Route = createFileRoute("/admin/chollos")({ component: AdminDeals });

const STATUS_OPTIONS = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activos" },
  { value: "scheduled", label: "Programados" },
  { value: "expired", label: "Caducados" },
  { value: "draft", label: "Borradores" },
];

function AdminDeals() {
  const { user } = useAuth();
  const [deals, setDeals] = useState<any[]>([]);
  const [stores, setStores] = useState<any[]>([]);
  const [cats, setCats] = useState<any[]>([]);
  const [subcats, setSubcats] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState<any>(empty());
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [uploading, setUploading] = useState(false);
  const [amazonUrl, setAmazonUrl] = useState("");
  const [autofilling, setAutofilling] = useState(false);
  const [showTelegramPanel, setShowTelegramPanel] = useState(false);
  const [telegramDealData, setTelegramDealData] = useState<any>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function empty() {
    return { title: "", short_description: "", description: "", image_url: "", images: [] as string[], current_price: "", previous_price: "",
      shipping_info: "", affiliate_url: "", store_id: "", category_id: "", subcategory_id: "", brand: "", status: "active", expires_at: "", scheduled_for: "" };
  }

  const load = () => {
    dealsService.getAdminAll(statusFilter).then(setDeals).catch((err) => toast.error(err.message));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [statusFilter]);

  useEffect(() => {
    Promise.all([
      storesService.getAll(),
      categoriesService.getAll(),
    ]).then(([s, c]) => {
      setStores(s || []);
      setCats((c || []).filter((x: any) => !x.parent_id));
      setSubcats((c || []).filter((x: any) => x.parent_id));
    });
  }, []);

  const startNew = () => { setEditing(null); setForm(empty()); setShowForm(true); };
  const startEdit = (d: any) => {
    setEditing(d);
    setForm({
      ...d,
      current_price: String(d.current_price),
      previous_price: d.previous_price ? String(d.previous_price) : "",
      expires_at: d.expires_at ? d.expires_at.slice(0, 16) : "",
      scheduled_for: d.scheduled_for ? d.scheduled_for.slice(0, 16) : "",
      images: d.images ?? [],
      subcategory_id: d.subcategory_id ?? "",
    });
    setShowForm(true);
  };

  const autofillFromAmazon = async () => {
    const url = amazonUrl.trim();
    if (!url) { toast.error("Introduce una URL"); return; }
    if (!/amazon\./i.test(url) && !/amzn\./i.test(url)) {
      toast.error("La URL no parece de Amazon");
      return;
    }
    setAutofilling(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/products/preview-from-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Error en la API del NAS");
      }

      const d = await response.json();
      const amazonStore = stores.find(s => s.name.toLowerCase().includes("amazon"));
      
      const updatedForm = (f: any) => ({
        ...f,
        title: d.title ?? f.title,
        short_description: d.short_description || f.short_description,
        description: d.long_description || f.description,
        image_url: d.image_url ?? f.image_url,
        images: d.images && d.images.length > 0 ? d.images : (d.image_url ? [d.image_url] : f.images),
        brand: d.brand ?? f.brand,
        current_price: d.current_price != null ? String(d.current_price) : f.current_price,
        previous_price: d.original_price != null ? String(d.original_price) : f.previous_price,
        affiliate_url: url,
        store_id: amazonStore?.id || f.store_id,
        category_id: d.category_id ?? f.category_id,
        subcategory_id: d.subcategory_id ?? f.subcategory_id,
        expires_at: d.expires_at ? d.expires_at.slice(0, 16) : f.expires_at,
        telegram_text: d.telegram_text ?? f.telegram_text,
      });
      setForm(updatedForm);

      if (!showForm) { setEditing(null); setShowForm(true); }
      toast.success("Datos importados desde tu NAS");

      // Abrir panel Telegram automáticamente con los datos importados
      const allImages = d.images && d.images.length > 0 ? d.images : (d.image_url ? [d.image_url] : []);
      openTelegramPanel({
        title: d.title || "",
        current_price: d.current_price != null ? String(d.current_price) : "",
        previous_price: d.original_price != null ? String(d.original_price) : "",
        short_description: d.short_description || "",
        description: d.long_description || "",
        affiliate_url: url,
        expires_at: d.expires_at ? d.expires_at.slice(0, 16) : "",
        images: allImages,
        image_url: allImages[0] ?? null,
      });
    } catch (e: any) {
      toast.error("Error desde el NAS: " + e.message);
    } finally {
      setAutofilling(false);
    }
  };

  /** Abre el panel completo con los datos del formulario actual */
  const openTelegramPanel = (source?: any) => {
    const data = source ?? form;
    const allImages = (data.images ?? []).filter(Boolean);
    if (data.image_url && !allImages.includes(data.image_url)) allImages.unshift(data.image_url);
    setTelegramDealData({
      title: data.title || "",
      current_price: parseFloat(data.current_price) || 0,
      previous_price: data.previous_price ? parseFloat(data.previous_price) : null,
      discount_percentage: data.previous_price && data.current_price
        ? Math.round((1 - parseFloat(data.current_price) / parseFloat(data.previous_price)) * 100)
        : null,
      description: data.description || data.short_description || null,
      affiliate_url: data.affiliate_url || "",
      expires_at: data.expires_at ? new Date(data.expires_at).toISOString() : null,
      images: allImages,
      image_url: allImages[0] ?? null,
    });
    setShowTelegramPanel(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    // imagen principal: primera del array si existe, si no la del campo image_url
    const allImages = form.images.filter(Boolean);
    if (form.image_url && !allImages.includes(form.image_url)) allImages.unshift(form.image_url);
    const mainImage = allImages[0] ?? null;

    const payload: any = {
      title: form.title.slice(0, 200),
      slug: editing?.slug ?? slugify(form.title) + "-" + Date.now().toString(36),
      short_description: form.short_description?.slice(0, 300) || null,
      description: form.description || null,
      image_url: mainImage,
      images: allImages,
      current_price: +form.current_price,
      previous_price: form.previous_price ? +form.previous_price : null,
      discount_percentage: form.previous_price && form.current_price ? Math.round((1 - +form.current_price / +form.previous_price) * 100) : null,
      shipping_info: form.shipping_info || null,
      affiliate_url: form.affiliate_url,
      store_id: form.store_id || null,
      category_id: form.category_id || null,
      subcategory_id: form.subcategory_id || null,
      brand: form.brand || null,
      status: form.status,
      expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
      scheduled_for: form.status === "scheduled" && form.scheduled_for ? new Date(form.scheduled_for).toISOString() : null,
      published_at: form.status === "active" && !editing ? new Date().toISOString() : undefined,
    };
    if (payload.published_at === undefined) delete payload.published_at;
    let savedDeal: any = null;
    try {
      if (editing) {
        savedDeal = await dealsService.update(editing.id, payload);
        toast.success("Chollo actualizado");
      } else {
        savedDeal = await dealsService.create({ ...payload, source: "manual" });
        toast.success("Chollo creado");
      }
      
      setShowForm(false);
      load();
    } catch (error: any) {
      toast.error(error.message);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("¿Eliminar este chollo?")) return;
    try {
      await dealsService.delete(id);
      load();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const addImageUrl = () => {
    const url = (form.image_url || "").trim();
    if (!url) return;
    if (form.images.includes(url)) { setForm({ ...form, image_url: "" }); return; }
    setForm({ ...form, images: [...form.images, url], image_url: "" });
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    const newUrls: string[] = [];
    const { supabase } = await import("@/integrations/supabase/client");
    for (const file of Array.from(files)) {
      if (!file.type.startsWith("image/")) { toast.error(`${file.name}: no es imagen`); continue; }
      if (file.size > 5 * 1024 * 1024) { toast.error(`${file.name}: máx 5MB`); continue; }
      const ext = file.name.split(".").pop();
      const path = `${user!.id}/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;
      const { error } = await supabase.storage.from("deal-images").upload(path, file);
      if (error) { toast.error(error.message); continue; }
      const { data: { publicUrl } } = supabase.storage.from("deal-images").getPublicUrl(path);
      newUrls.push(publicUrl);
    }
    setForm((f: any) => ({ ...f, images: [...f.images, ...newUrls] }));
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
    if (newUrls.length) toast.success(`${newUrls.length} imagen(es) subida(s)`);
  };

  const removeImage = (i: number) => {
    setForm({ ...form, images: form.images.filter((_: any, idx: number) => idx !== i) });
  };

  const moveImage = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= form.images.length) return;
    const arr = [...form.images];
    [arr[i], arr[j]] = [arr[j], arr[i]];
    setForm({ ...form, images: arr });
  };

  const filteredSubcats = subcats.filter((s) => s.parent_id === form.category_id);
  const inputCls = "w-full bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-sm outline-none focus:border-cyan-glow";

  return (
    <div>
      {/* Panel lateral de Telegram */}
      {showTelegramPanel && telegramDealData && (
        <TelegramPanel
          dealData={telegramDealData}
          onClose={() => setShowTelegramPanel(false)}
        />
      )}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="font-mono text-sm uppercase text-cyan-glow">Gestión de chollos</h2>
        <div className="flex items-center gap-2">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="bg-surface-900 border border-surface-700 px-3 py-2 font-mono text-xs uppercase outline-none focus:border-cyan-glow">
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <button onClick={startNew} className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center gap-2 hover:bg-foreground">
            <Plus className="size-4" /> NUEVO
          </button>
        </div>
      </div>

      {/* AUTOCOMPLETAR DESDE AMAZON */}
      <div className="bg-surface-800 border border-cyan-glow/40 p-4 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <Wand2 className="size-4 text-cyan-glow" />
          <h3 className="font-mono text-xs uppercase text-cyan-glow">Autocompletar desde Amazon</h3>
        </div>
        <p className="font-mono text-[10px] text-muted-foreground mb-3">
          Pega tu URL de afiliado de Amazon y rellenaremos título, imagen, marca y precios automáticamente.
        </p>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="url"
            placeholder="https://www.amazon.es/dp/..."
            value={amazonUrl}
            onChange={(e) => setAmazonUrl(e.target.value)}
            className={inputCls + " flex-1"}
          />
          <button
            type="button"
            onClick={autofillFromAmazon}
            disabled={autofilling}
            className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2 flex items-center justify-center gap-2 hover:bg-foreground disabled:opacity-50"
          >
            {autofilling ? <Loader2 className="size-4 animate-spin" /> : <Wand2 className="size-4" />}
            {autofilling ? "PROCESANDO..." : "[ AUTOCOMPLETAR ]"}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={save} className="bg-surface-800 border border-surface-700 p-5 mb-6 space-y-3">
          <h3 className="font-mono text-xs uppercase text-cyan-glow">{editing ? "Editar chollo" : "Nuevo chollo"}</h3>
          <input placeholder="Título *" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className={inputCls} />
          <input placeholder="Descripción corta" value={form.short_description} onChange={(e) => setForm({ ...form, short_description: e.target.value })} className={inputCls} />
          <textarea placeholder="Descripción larga" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className={inputCls} />

          {/* IMÁGENES */}
          <div className="border border-surface-700 p-3 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase text-cyan-glow">Imágenes ({form.images.length})</span>
              <span className="font-mono text-[10px] text-muted-foreground">La primera es la principal</span>
            </div>
            <div className="flex gap-2">
              <input placeholder="Añadir por URL..." value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addImageUrl(); } }}
                className={inputCls + " flex-1"} />
              <button type="button" onClick={addImageUrl} className="border border-surface-700 px-3 font-mono text-xs hover:border-cyan-glow">[ AÑADIR URL ]</button>
            </div>
            <div className="flex items-center gap-2">
              <input ref={fileRef} type="file" accept="image/*" multiple onChange={(e) => handleFiles(e.target.files)} className="hidden" />
              <button type="button" onClick={() => fileRef.current?.click()} disabled={uploading}
                className="border border-surface-700 px-3 py-2 font-mono text-xs hover:border-cyan-glow flex items-center gap-2 disabled:opacity-50">
                <Upload className="size-3" /> {uploading ? "SUBIENDO..." : "[ SUBIR ARCHIVOS ]"}
              </button>
              <span className="font-mono text-[10px] text-muted-foreground">JPG/PNG/WEBP · máx 5MB</span>
            </div>
            {form.images.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
                {form.images.map((url: string, i: number) => (
                  <div key={i} className="relative group bg-surface-900 border border-surface-700 aspect-square overflow-hidden">
                    <img src={url} alt="" className="w-full h-full object-cover" />
                    {i === 0 && <span className="absolute top-1 left-1 bg-cyan-glow text-surface-900 font-mono text-[9px] font-bold px-1">PRINCIPAL</span>}
                    <div className="absolute inset-0 bg-surface-900/80 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-1">
                      <button type="button" onClick={() => moveImage(i, -1)} disabled={i === 0} className="p-1 hover:text-cyan-glow disabled:opacity-30"><GripVertical className="size-3 rotate-90" /></button>
                      <button type="button" onClick={() => moveImage(i, 1)} disabled={i === form.images.length - 1} className="p-1 hover:text-cyan-glow disabled:opacity-30"><GripVertical className="size-3 -rotate-90" /></button>
                      <button type="button" onClick={() => removeImage(i)} className="p-1 hover:text-alert-red"><X className="size-3" /></button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="grid sm:grid-cols-3 gap-3">
            <input type="number" step="0.01" placeholder="Precio actual *" required value={form.current_price} onChange={(e) => setForm({ ...form, current_price: e.target.value })} className={inputCls} />
            <input type="number" step="0.01" placeholder="Precio anterior" value={form.previous_price} onChange={(e) => setForm({ ...form, previous_price: e.target.value })} className={inputCls} />
            <input placeholder="Marca" value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} className={inputCls} />
          </div>
          <input placeholder="Envío (texto)" value={form.shipping_info} onChange={(e) => setForm({ ...form, shipping_info: e.target.value })} className={inputCls} />
          <input placeholder="Enlace afiliado *" required value={form.affiliate_url} onChange={(e) => setForm({ ...form, affiliate_url: e.target.value })} className={inputCls} />
          <div className="grid sm:grid-cols-4 gap-3">
            <select value={form.store_id} onChange={(e) => setForm({ ...form, store_id: e.target.value })} className={inputCls}>
              <option value="">— Tienda —</option>
              {stores.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value, subcategory_id: "" })} className={inputCls}>
              <option value="">— Categoría —</option>
              {cats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select value={form.subcategory_id} onChange={(e) => setForm({ ...form, subcategory_id: e.target.value })} className={inputCls} disabled={!form.category_id || filteredSubcats.length === 0}>
              <option value="">{form.category_id ? (filteredSubcats.length ? "— Subcategoría —" : "Sin subcategorías") : "Elige categoría primero"}</option>
              {filteredSubcats.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className={inputCls}>
              <option value="active">Activo</option>
              <option value="expired">Caducado</option>
              <option value="scheduled">Programado</option>
              <option value="draft">Borrador</option>
            </select>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="font-mono text-[10px] uppercase text-muted-foreground block mb-1">Caduca el (opcional)</span>
              <input type="datetime-local" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} className={inputCls} />
            </label>
            {form.status === "scheduled" && (
              <label className="block">
                <span className="font-mono text-[10px] uppercase text-cyan-glow block mb-1">Publicar el *</span>
                <input type="datetime-local" required value={form.scheduled_for} onChange={(e) => setForm({ ...form, scheduled_for: e.target.value })} className={inputCls} />
              </label>
            )}
          </div>
          {form.status === "draft" && (
            <p className="font-mono text-[10px] text-muted-foreground">📝 BORRADOR · No se publicará. Puedes previsualizarlo en su URL siendo admin.</p>
          )}
          {form.status === "expired" && (
            <p className="font-mono text-[10px] text-alert-red">⛔ CADUCADO · Aparecerá en gris con aviso de oferta finalizada.</p>
          )}
          {/* PUBLICAR EN TELEGRAM */}
          <button
            type="button"
            onClick={() => openTelegramPanel()}
            className="w-full border border-cyan-glow/50 text-cyan-glow font-mono text-xs py-2 flex items-center justify-center gap-2 hover:bg-cyan-glow/10"
          >
            <Send className="size-3.5" /> 🚀 Publicar en Telegram
          </button>

          <div className="flex gap-2">
            <button type="submit" className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-2">[ GUARDAR ]</button>
            <button type="button" onClick={() => setShowForm(false)} className="border border-surface-700 font-mono text-xs px-4 py-2">[ CANCELAR ]</button>
          </div>
        </form>
      )}

      <div className="bg-surface-800 border border-surface-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-surface-700 font-mono text-xs uppercase text-muted-foreground">
            <tr><th className="text-left p-3">Título</th><th className="text-left p-3">Tienda</th><th className="text-right p-3">Precio</th><th className="text-left p-3">Estado</th><th className="text-left p-3">Fecha</th><th className="p-3">Acciones</th></tr>
          </thead>
          <tbody>
            {deals.map(d => {
              const stCls = d.status === "active" ? "bg-cyan-glow/15 text-cyan-glow"
                : d.status === "scheduled" ? "bg-amber-500/15 text-amber-400"
                : d.status === "expired" ? "bg-alert-red/15 text-alert-red"
                : "bg-surface-700 text-muted-foreground";
              return (
              <tr key={d.id} className="border-b border-surface-700/50 hover:bg-surface-700/30">
                <td className="p-3"><Link to="/chollo/$slug" params={{ slug: d.slug }} className="hover:text-cyan-glow">{d.title}</Link></td>
                <td className="p-3 text-muted-foreground font-mono text-xs">{d.store?.name ?? "—"}</td>
                <td className="p-3 text-right font-mono text-cyan-glow">{formatPrice(d.current_price)}</td>
                <td className="p-3"><span className={`font-mono text-[10px] uppercase px-2 py-1 ${stCls}`}>{d.status}</span></td>
                <td className="p-3 text-muted-foreground font-mono text-xs">
                  {d.status === "scheduled" && d.scheduled_for ? <>📅 {new Date(d.scheduled_for).toLocaleString("es-ES")}</>
                    : d.expires_at ? <>⏱ {new Date(d.expires_at).toLocaleString("es-ES")}</>
                    : formatRelativeTime(d.created_at)}
                </td>
                <td className="p-3 flex gap-1">
                  <button type="button" onClick={() => startEdit(d)} className="p-1.5 hover:text-cyan-glow" title="Editar"><Edit3 className="size-4" /></button>
                  <button type="button" onClick={() => openTelegramPanel(d)} className="p-1.5 hover:text-cyan-glow" title="Publicar en Telegram"><Send className="size-4" /></button>
                  <button type="button" onClick={() => remove(d.id)} className="p-1.5 hover:text-alert-red" title="Eliminar"><Trash2 className="size-4" /></button>
                </td>
              </tr>
              );
            })}
            {deals.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-muted-foreground font-mono text-xs">SIN_RESULTADOS</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
