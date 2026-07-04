import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Layout } from "@/components/layout/Layout";
import { useAuth } from "@/hooks/useAuth";
import { formatRelativeTime } from "@/lib/format";
import {
  useMarkNotificationsRead,
  useNotificationsList,
} from "@/features/notifications/hooks/useNotifications";
import { toast } from "sonner";

export const Route = createFileRoute("/notificaciones")({
  component: NotificationsPage,
  head: () => ({
    meta: [
      { title: "Notificaciones · BuenChollo Tech" },
      {
        name: "description",
        content: "Bandeja de notificaciones de tus alertas en BuenChollo Tech.",
      },
      { property: "og:title", content: "Notificaciones · BuenChollo Tech" },
      {
        property: "og:description",
        content: "Bandeja de notificaciones de tus alertas en BuenChollo Tech.",
      },
      { property: "og:url", content: "https://buenchollotech.com/notificaciones" },
      { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.com/notificaciones" }],
  }),
});

function NotificationsPage() {
  const { user, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const { data: items = [], isLoading, isError } = useNotificationsList();
  const markRead = useMarkNotificationsRead();

  useEffect(() => {
    if (!authLoading && !user) nav({ to: "/login" });
  }, [authLoading, user, nav]);

  useEffect(() => {
    // Al entrar en la página: marcar como leídas (best-effort silencioso).
    if (items.length > 0 && !markRead.isPending && !markRead.isSuccess) {
      markRead.mutate();
    }
  }, [items.length, markRead]);

  useEffect(() => {
    if (isError) toast.error("No se pudieron cargar las notificaciones");
  }, [isError]);

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; NOTIFICACIONES</div>
        <h1 className="text-3xl font-bold tracking-tighter mb-6">Tus notificaciones</h1>
        {isLoading ? (
          <div className="font-mono text-xs text-muted-foreground py-12 text-center">
            CARGANDO...
          </div>
        ) : items.length === 0 ? (
          <div className="bg-surface-800 border border-surface-700 p-12 text-center text-muted-foreground font-mono text-sm">
            Sin notificaciones por ahora. Crea alertas para recibir avisos cuando aparezcan chollos
            que te interesen.
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((n) => (
              <div key={n.id} className="bg-surface-800 border border-surface-700 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    {n.link_url ? (
                      <Link
                        to={n.link_url}
                        className="font-bold text-base hover:text-cyan-glow transition-colors"
                      >
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
