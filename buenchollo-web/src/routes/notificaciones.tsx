import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { formatRelativeTime } from "@/lib/format";
import { notificationsApi, type Notification } from "@/services/api/notifications";
import { toast } from "sonner";

export const Route = createFileRoute("/notificaciones")({
  component: NotificationsPage,
  head: () => ({
    meta: [
      { title: "Notificaciones · BuencholloTech" },
      { name: "description", content: "Bandeja de notificaciones de tus alertas en BuencholloTech." },
      { property: "og:title", content: "Notificaciones · BuencholloTech" },
      { property: "og:description", content: "Bandeja de notificaciones de tus alertas en BuencholloTech." },
      { property: "og:url", content: "https://buenchollotech.lovable.app/notificaciones" },
      { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.lovable.app/notificaciones" }],
  }),
});

function NotificationsPage() {
  const { user, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { if (!authLoading && !user) nav({ to: "/login" }); }, [authLoading, user]);

  useEffect(() => {
    if (!user) return;
    notificationsApi.list()
      .then(setItems)
      .then(() => notificationsApi.markRead())
      .then(() => window.dispatchEvent(new Event("notifications:changed")))
      .catch(() => toast.error("No se pudieron cargar las notificaciones"))
      .finally(() => setLoading(false));
  }, [user]);

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; NOTIFICACIONES</div>
        <h1 className="text-3xl font-bold tracking-tighter mb-6">Tus notificaciones</h1>
        {loading ? (
          <div className="font-mono text-xs text-muted-foreground py-12 text-center">CARGANDO...</div>
        ) : items.length === 0 ? (
          <div className="bg-surface-800 border border-surface-700 p-12 text-center text-muted-foreground font-mono text-sm">
            Sin notificaciones por ahora. Crea alertas para recibir avisos cuando aparezcan chollos que te interesen.
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((n) => (
              <div key={n.id} className="bg-surface-800 border border-surface-700 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    {n.link_url ? (
                      <Link to={n.link_url} className="font-bold text-base hover:text-cyan-glow transition-colors">
                        {n.title}
                      </Link>
                    ) : (
                      <h2 className="font-bold text-base">{n.title}</h2>
                    )}
                    {n.body && <p className="text-sm text-muted-foreground mt-1">{n.body}</p>}
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground whitespace-nowrap">
                    {formatRelativeTime(n.created_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
