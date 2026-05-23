import { createFileRoute, Link, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { Package, FolderTree, Users, BarChart3, ShoppingBag } from "lucide-react";

export const Route = createFileRoute("/admin")({
  component: AdminLayout,
  head: () => ({ meta: [{ title: "Admin · BuencholloTech" }] }),
});

function AdminLayout() {
  const { user, isAdmin, loading } = useAuth();
  const nav = useNavigate();
  useEffect(() => {
    if (loading) return;
    if (!user) nav({ to: "/login" });
    else if (!isAdmin) nav({ to: "/" });
  }, [user, isAdmin, loading]);

  if (loading || !isAdmin) return <Layout><div className="max-w-7xl mx-auto p-8 font-mono text-sm">CARGANDO...</div></Layout>;

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; ADMIN_PANEL</div>
        <h1 className="text-3xl font-bold tracking-tighter mb-6">Panel de administración</h1>
        <div className="grid lg:grid-cols-[220px_1fr] gap-6">
          <nav className="bg-surface-800 border border-surface-700 p-2 h-fit">
            <Link to="/admin" activeOptions={{ exact: true }} activeProps={{ className: "bg-surface-700 text-cyan-glow" }} className="flex items-center gap-2 px-3 py-2 font-mono text-xs uppercase hover:bg-surface-700">
              <BarChart3 className="size-4" /> Resumen
            </Link>
            <Link to="/admin/chollos" activeProps={{ className: "bg-surface-700 text-cyan-glow" }} className="flex items-center gap-2 px-3 py-2 font-mono text-xs uppercase hover:bg-surface-700">
              <Package className="size-4" /> Chollos
            </Link>
            <Link to="/admin/categorias" activeProps={{ className: "bg-surface-700 text-cyan-glow" }} className="flex items-center gap-2 px-3 py-2 font-mono text-xs uppercase hover:bg-surface-700">
              <FolderTree className="size-4" /> Categorías
            </Link>
            <Link to="/admin/tiendas" activeProps={{ className: "bg-surface-700 text-cyan-glow" }} className="flex items-center gap-2 px-3 py-2 font-mono text-xs uppercase hover:bg-surface-700">
              <ShoppingBag className="size-4" /> Tiendas
            </Link>
            <Link to="/admin/usuarios" activeProps={{ className: "bg-surface-700 text-cyan-glow" }} className="flex items-center gap-2 px-3 py-2 font-mono text-xs uppercase hover:bg-surface-700">
              <Users className="size-4" /> Usuarios
            </Link>
          </nav>
          <div><Outlet /></div>
        </div>
      </div>
    </Layout>
  );
}
