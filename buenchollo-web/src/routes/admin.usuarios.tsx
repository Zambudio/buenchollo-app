import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { formatRelativeTime } from "@/lib/format";
import { adminUsersApi, type AdminUserItem } from "@/services/api/auth";
import { toast } from "sonner";

export const Route = createFileRoute("/admin/usuarios")({ component: AdminUsers });

function AdminUsers() {
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminUsersApi.list()
      .then(setUsers)
      .catch(() => toast.error("No se pudieron cargar los usuarios"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h2 className="font-mono text-sm uppercase text-cyan-glow mb-4">Usuarios ({users.length})</h2>
      <div className="bg-surface-800 border border-surface-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-surface-700 font-mono text-xs uppercase text-muted-foreground">
            <tr>
              <th className="text-left p-3">Nombre</th>
              <th className="text-left p-3">Roles</th>
              <th className="text-left p-3">Registro</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={3} className="p-3 font-mono text-xs text-muted-foreground">Cargando...</td></tr>
            )}
            {!loading && users.length === 0 && (
              <tr><td colSpan={3} className="p-3 font-mono text-xs text-muted-foreground">Sin usuarios.</td></tr>
            )}
            {users.map(u => (
              <tr key={u.user_id} className="border-b border-surface-700/50">
                <td className="p-3">{u.display_name ?? u.username ?? "—"}</td>
                <td className="p-3 font-mono text-xs">{u.roles.length > 0 ? u.roles.join(", ") : "user"}</td>
                <td className="p-3 text-muted-foreground font-mono text-xs">
                  {u.created_at ? formatRelativeTime(u.created_at) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
