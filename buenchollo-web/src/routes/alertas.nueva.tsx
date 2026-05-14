import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";

export const Route = createFileRoute("/alertas/nueva")({
  component: NewAlertPage,
  head: () => ({
    meta: [
      { title: "Nueva alerta · BuencholloTech" },
      { name: "description", content: "Crea una nueva alerta para recibir avisos cuando aparezca un chollo que cumpla tus criterios." },
      { property: "og:title", content: "Nueva alerta · BuencholloTech" },
      { property: "og:description", content: "Crea una nueva alerta para recibir avisos cuando aparezca un chollo que cumpla tus criterios." },
      { property: "og:url", content: "https://buenchollotech.lovable.app/alertas/nueva" }, { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.lovable.app/alertas/nueva" }],
  }),
});

function NewAlertPage() {
  const { user, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const [cats, setCats] = useState<any[]>([]);
  const [stores, setStores] = useState<any[]>([]);
  const [form, setForm] = useState({
    name: "", keyword: "", category_id: "", brand: "", store_id: "",
    min_price: "", max_price: "", min_discount: "",
  });

  useEffect(() => { if (!authLoading && !user) nav({ to: "/login" }); }, [authLoading, user]);
  useEffect(() => {
    Promise.all([
      supabase.from("categories").select("id,name").eq("is_active", true).order("display_order"),
      supabase.from("stores").select("id,name").eq("is_active", true).order("name"),
    ]).then(([c, s]) => { setCats(c.data ?? []); setStores(s.data ?? []); });
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    if (form.name.trim().length < 2) { toast.error("Pon un nombre a la alerta"); return; }
    const { error } = await supabase.from("alerts").insert({
      user_id: user.id,
      name: form.name.trim().slice(0, 100),
      keyword: form.keyword.trim() || null,
      category_id: form.category_id || null,
      brand: form.brand.trim() || null,
      store_id: form.store_id || null,
      min_price: form.min_price ? +form.min_price : null,
      max_price: form.max_price ? +form.max_price : null,
      min_discount: form.min_discount ? +form.min_discount : null,
    });
    if (error) { console.error("Error creando alerta:", error); toast.error("No se pudo crear la alerta. Inténtalo de nuevo."); return; }
    toast.success("Alerta creada");
    nav({ to: "/alertas" });
  };

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));
  const inputCls = "w-full bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow";

  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        <Link to="/alertas" className="font-mono text-xs text-cyan-glow">← MIS ALERTAS</Link>
        <h1 className="text-3xl font-bold tracking-tighter mt-3 mb-6">Nueva alerta</h1>

        <form onSubmit={submit} className="bg-surface-800 border border-surface-700 p-6 space-y-4">
          <div>
            <label className="block text-xs font-mono uppercase text-cyan-glow mb-1" htmlFor="alert-name">Nombre *</label>
            <input id="alert-name" value={form.name} onChange={(e) => set("name", e.target.value)} className={inputCls} placeholder="Ej: RTX 4070 por menos de 600€" />
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono uppercase text-cyan-glow mb-1" htmlFor="alert-keyword">Palabra clave</label>
              <input id="alert-keyword" value={form.keyword} onChange={(e) => set("keyword", e.target.value)} className={inputCls} placeholder="iphone, rtx 4070..." />
            </div>
            <div>
              <label className="block text-xs font-mono uppercase text-cyan-glow mb-1" htmlFor="alert-brand">Marca</label>
              <input id="alert-brand" value={form.brand} onChange={(e) => set("brand", e.target.value)} className={inputCls} placeholder="Apple, Sony..." />
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono uppercase text-cyan-glow mb-1" htmlFor="alert-cat">Categoría</label>
              <select id="alert-cat" value={form.category_id} onChange={(e) => set("category_id", e.target.value)} className={inputCls}>
                <option value="">Cualquiera</option>
                {cats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono uppercase text-cyan-glow mb-1" htmlFor="alert-store">Tienda</label>
              <select id="alert-store" value={form.store_id} onChange={(e) => set("store_id", e.target.value)} className={inputCls}>
                <option value="">Cualquiera</option>
                {stores.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-mono uppercase text-cyan-glow mb-1" htmlFor="alert-min">Precio min €</label>
              <input id="alert-min" type="number" value={form.min_price} onChange={(e) => set("min_price", e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs font-mono uppercase text-cyan-glow mb-1" htmlFor="alert-max">Precio max €</label>
              <input id="alert-max" type="number" value={form.max_price} onChange={(e) => set("max_price", e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs font-mono uppercase text-cyan-glow mb-1" htmlFor="alert-disc">Descuento min %</label>
              <input id="alert-disc" type="number" value={form.min_discount} onChange={(e) => set("min_discount", e.target.value)} className={inputCls} />
            </div>
          </div>
          <button type="submit" className="w-full bg-cyan-glow text-surface-900 font-mono text-xs font-bold py-3 hover:bg-foreground transition-colors">
            [ CREAR ALERTA ]
          </button>
        </form>
      </div>
    </Layout>
  );
}
