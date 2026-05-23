import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { alertsApi, type Alert } from "@/services/api/alerts";
import { Plus, Trash2, Power, Tag, Store, Euro, Percent, Search } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/alertas")({
  component: AlertsPage,
  head: () => ({
    meta: [
      { title: "Mis alertas · BuencholloTech" },
      { name: "description", content: "Gestiona tus radares de precios. Recibe avisos cuando aparezca un chollo que cumpla tus criterios." },
      { property: "og:title", content: "Mis alertas · BuencholloTech" },
      { name: "robots", content: "noindex, nofollow" },
    ],
  }),
});

function AlertsPage() {
  const { user, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { if (!authLoading && !user) nav({ to: "/login" }); }, [authLoading, user]);

  const load = async () => {
    if (!user) return;
    try {
      setAlerts(await alertsApi.list());
    } catch {
      toast.error("No se pudieron cargar las alertas");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [user]);

  const toggle = async (a: Alert) => {
    try {
      const updated = await alertsApi.toggle(a.id, !a.is_active);
      setAlerts(prev => prev.map(x => x.id === a.id ? updated : x));
      toast.success(updated.is_active ? "Alerta activada" : "Alerta pausada");
    } catch {
      toast.error("No se pudo actualizar la alerta");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("¿Eliminar esta alerta?")) return;
    try {
      await alertsApi.delete(id);
      setAlerts(prev => prev.filter(x => x.id !== id));
      toast.success("Alerta eliminada");
    } catch {
      toast.error("No se pudo eliminar la alerta");
    }
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        {/* Cabecera */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="font-mono text-cyan-glow text-xs mb-2">&gt; RADAR_ALERTAS</div>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter">Mis alertas</h1>
          </div>
          <Link
            to="/alertas/nueva"
            className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-4 py-3 hover:bg-foreground transition-colors flex items-center gap-2"
          >
            <Plus className="size-4" /> NUEVA ALERTA
          </Link>
        </div>

        {loading ? (
          <div className="font-mono text-xs text-muted-foreground py-12 text-center">CARGANDO...</div>
        ) : alerts.length === 0 ? (
          <div className="bg-surface-800 border border-surface-700 p-16 text-center">
            <div className="font-mono text-4xl text-cyan-glow mb-4">◎</div>
            <p className="text-foreground font-bold text-lg mb-2">Sin radares activos</p>
            <p className="text-muted-foreground text-sm mb-6">Crea una alerta y te avisamos cuando aparezca un chollo que te interese.</p>
            <Link to="/alertas/nueva" className="inline-flex items-center gap-2 bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-5 py-3 hover:bg-foreground transition-colors">
              <Plus className="size-4" /> CONFIGURAR PRIMER RADAR
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map(a => (
              <div
                key={a.id}
                className={`bg-surface-800 border p-5 flex items-center justify-between gap-4 transition-colors ${a.is_active ? "border-surface-700 hover:border-surface-600" : "border-surface-700 opacity-60"}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`size-2 rounded-full shrink-0 ${a.is_active ? "bg-cyan-glow animate-pulse" : "bg-surface-600"}`} />
                    <h2 className="font-bold text-base truncate">{a.name}</h2>
                    {!a.is_active && (
                      <span className="font-mono text-[10px] uppercase bg-surface-700 text-muted-foreground px-2 py-0.5 shrink-0">pausada</span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {a.keyword && (
                      <span className="flex items-center gap-1 text-[11px] font-mono bg-surface-900 border border-surface-600 px-2 py-0.5 text-foreground">
                        <Search className="size-3 text-cyan-glow" /> {a.keyword}
                      </span>
                    )}
                    {a.category && (
                      <span className="flex items-center gap-1 text-[11px] font-mono bg-surface-900 border border-surface-600 px-2 py-0.5 text-foreground">
                        <Tag className="size-3 text-cyan-glow" /> {a.category.name}
                      </span>
                    )}
                    {a.store && (
                      <span className="flex items-center gap-1 text-[11px] font-mono bg-surface-900 border border-surface-600 px-2 py-0.5 text-foreground">
                        <Store className="size-3 text-cyan-glow" /> {a.store.name}
                      </span>
                    )}
                    {a.brand && (
                      <span className="flex items-center gap-1 text-[11px] font-mono bg-surface-900 border border-surface-600 px-2 py-0.5 text-foreground">
                        {a.brand}
                      </span>
                    )}
                    {(a.min_price != null || a.max_price != null) && (
                      <span className="flex items-center gap-1 text-[11px] font-mono bg-surface-900 border border-surface-600 px-2 py-0.5 text-foreground">
                        <Euro className="size-3 text-cyan-glow" />
                        {a.min_price != null ? `${a.min_price}` : "0"}–{a.max_price != null ? `${a.max_price}` : "∞"}
                      </span>
                    )}
                    {a.min_discount != null && (
                      <span className="flex items-center gap-1 text-[11px] font-mono bg-surface-900 border border-surface-600 px-2 py-0.5 text-foreground">
                        <Percent className="size-3 text-cyan-glow" /> -{a.min_discount}% mín.
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button" onClick={() => toggle(a)}
                    aria-label={a.is_active ? "Pausar alerta" : "Activar alerta"}
                    title={a.is_active ? "Pausar" : "Activar"}
                    className={`p-2 border transition-colors ${a.is_active ? "border-surface-600 hover:border-cyan-glow hover:text-cyan-glow" : "border-cyan-glow text-cyan-glow hover:bg-cyan-glow/10"}`}
                  >
                    <Power className="size-4" />
                  </button>
                  <button
                    type="button" onClick={() => remove(a.id)}
                    aria-label="Eliminar alerta"
                    title="Eliminar"
                    className="p-2 border border-surface-600 hover:border-alert-red hover:text-alert-red transition-colors"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
