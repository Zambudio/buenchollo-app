import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { formatRelativeTime } from "@/lib/format";

export const Route = createFileRoute("/admin/usuarios")({ component: AdminUsers });

function AdminUsers() {
  const [profiles, setProfiles] = useState<any[]>([]);
  useEffect(() => {
    supabase.from("profiles").select("*, roles:user_roles(role)").order("created_at", { ascending: false }).limit(200)
      .then(({ data }) => setProfiles(data ?? []));
  }, []);
  return (
    <div>
      <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4">Usuarios ({profiles.length})</h2>
      <div className="bg-surface-800 border border-surface-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-surface-700 font-mono text-xs uppercase text-muted-foreground">
            <tr><th className="text-left p-3">Nombre</th><th className="text-left p-3">Roles</th><th className="text-left p-3">Registro</th></tr>
          </thead>
          <tbody>
            {profiles.map(p => (
              <tr key={p.id} className="border-b border-surface-700/50">
                <td className="p-3">{p.display_name ?? "—"}</td>
                <td className="p-3 font-mono text-xs">{(p.roles ?? []).map((r: any) => r.role).join(", ") || "user"}</td>
                <td className="p-3 text-muted-foreground font-mono text-xs">{formatRelativeTime(p.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
