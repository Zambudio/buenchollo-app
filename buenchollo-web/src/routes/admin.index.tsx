import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";

export const Route = createFileRoute("/admin/")({ component: AdminHome });

function AdminHome() {
  const [stats, setStats] = useState<any>({});
  useEffect(() => {
    Promise.all([
      supabase.from("deals").select("id", { count: "exact", head: true }),
      supabase.from("deals").select("id", { count: "exact", head: true }).eq("status", "active"),
      supabase.from("favorites").select("id", { count: "exact", head: true }),
      supabase.from("alerts").select("id", { count: "exact", head: true }),
      supabase.from("deal_comments").select("id", { count: "exact", head: true }),
      supabase.from("profiles").select("id", { count: "exact", head: true }),
    ]).then(([d, da, f, a, c, u]) => {
      setStats({ deals: d.count, active: da.count, favs: f.count, alerts: a.count, comments: c.count, users: u.count });
    });
  }, []);

  const Card = ({ label, value }: any) => (
    <div className="bg-surface-800 border border-surface-700 p-5">
      <div className="font-mono text-xs uppercase text-muted-foreground mb-2">{label}</div>
      <div className="font-mono text-3xl font-extrabold text-cyan-glow tabular-nums">{value ?? "—"}</div>
    </div>
  );

  return (
    <div>
      <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4">Resumen general</h2>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card label="Chollos totales" value={stats.deals} />
        <Card label="Chollos activos" value={stats.active} />
        <Card label="Usuarios" value={stats.users} />
        <Card label="Favoritos guardados" value={stats.favs} />
        <Card label="Alertas activas" value={stats.alerts} />
        <Card label="Comentarios" value={stats.comments} />
      </div>
    </div>
  );
}
