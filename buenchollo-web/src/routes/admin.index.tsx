import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { adminApi, type AdminStats } from "@/services/api/auth";
import { errorMessage } from "@/lib/errors";
import { toast } from "sonner";

export const Route = createFileRoute("/admin/")({ component: AdminHome });

function AdminHome() {
  const [stats, setStats] = useState<AdminStats | null>(null);

  useEffect(() => {
    adminApi
      .getStats()
      .then(setStats)
      .catch((e: unknown) =>
        toast.error(errorMessage(e, "No se pudieron cargar las estadísticas")),
      );
  }, []);

  return (
    <div>
      <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4">Resumen general</h2>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Chollos totales" value={stats?.deals} />
        <StatCard label="Chollos activos" value={stats?.active} />
        <StatCard label="Usuarios" value={stats?.users} />
        <StatCard label="Favoritos guardados" value={stats?.favs} />
        <StatCard label="Alertas activas" value={stats?.alerts} />
        <StatCard label="Comentarios" value={stats?.comments} />
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="bg-surface-800 border border-surface-700 p-5">
      <div className="font-mono text-xs uppercase text-muted-foreground mb-2">{label}</div>
      <div className="font-mono text-3xl font-extrabold text-cyan-glow tabular-nums">
        {value ?? "—"}
      </div>
    </div>
  );
}
