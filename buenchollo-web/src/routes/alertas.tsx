import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { Plus, Trash2, Power } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/alertas")({
  component: AlertsPage,
  head: () => ({
    meta: [
      { title: "Mis alertas · BuencholloTech" },
      { name: "description", content: "Crea y gestiona radares de chollos personalizados por palabra clave, marca, categoría, tienda, precio y descuento mínimo." },
      { property: "og:title", content: "Mis alertas · BuencholloTech" },
      { property: "og:description", content: "Crea y gestiona radares de chollos personalizados por palabra clave, marca, categoría, tienda, precio y descuento mínimo." },
      { property: "og:url", content: "https://buenchollotech.lovable.app/alertas" }, { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.lovable.app/alertas" }],
  }),
});

function AlertsPage() {
  const { user, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const [alerts, setAlerts] = useState<any[]>([]);

  useEffect(() => { if (!authLoading && !user) nav({ to: "/login" }); }, [authLoading, user]);

  const load = () => {
    if (!user) return;
    supabase.from("alerts").select("*, category:categories(name), store:stores(name)")
      .eq("user_id", user.id).order("created_at", { ascending: false })
      .then(({ data }) => setAlerts(data ?? []));
  };
  useEffect(load, [user]);

  const toggle = async (a: any) => {
    await supabase.from("alerts").update({ is_active: !a.is_active }).eq("id", a.id);
    load();
  };
  const remove = async (id: string) => {
    if (!confirm("¿Eliminar esta alerta?")) return;
    await supabase.from("alerts").delete().eq("id", id);
    toast.success("Alerta eliminada");
    load();
  };

  return (
    <Layout>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="font-mono text-cyan-glow text-xs mb-2">&gt; RADAR_ALERTAS</div>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter">Mis alertas</h1>
          </div>
          <Link to="/alertas/nueva" className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-3 hover:bg-foreground transition-colors flex items-center gap-2">
            <Plus className="size-4" /> NUEVA ALERTA
          </Link>
        </div>

        {alerts.length === 0 ? (
          <div className="bg-surface-800 border border-surface-700 p-12 text-center">
            <p className="text-muted-foreground font-mono mb-4">No tienes alertas configuradas.</p>
            <Link to="/alertas/nueva" className="text-cyan-glow font-mono text-xs">[ CREAR LA PRIMERA ]</Link>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map(a => (
              <div key={a.id} className="bg-surface-800 border border-surface-700 p-5 flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="font-bold text-base truncate">{a.name}</h2>
                    {!a.is_active && <span className="font-mono text-[10px] uppercase bg-surface-700 px-2 py-0.5">Pausada</span>}
                  </div>
                  <div className="text-xs text-muted-foreground font-mono space-x-3">
                    {a.keyword && <span>"{a.keyword}"</span>}
                    {a.category && <span>· {a.category.name}</span>}
                    {a.brand && <span>· {a.brand}</span>}
                    {a.max_price && <span>· hasta {a.max_price}€</span>}
                    {a.min_discount && <span>· {a.min_discount}%+</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => toggle(a)} aria-label={a.is_active ? "Pausar alerta" : "Activar alerta"} className="p-2 hover:text-cyan-glow" title="Activar/Pausar"><Power className="size-4" /></button>
                  <button onClick={() => remove(a.id)} aria-label="Eliminar alerta" className="p-2 hover:text-alert-red" title="Eliminar"><Trash2 className="size-4" /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
