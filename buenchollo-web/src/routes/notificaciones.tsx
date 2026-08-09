import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { CheckCheck } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { useAuth } from "@/hooks/useAuth";
import { formatRelativeTime } from "@/lib/format";
import {
  useMarkNotificationsRead,
  useMarkNotificationRead,
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
  const markOneRead = useMarkNotificationRead();

  useEffect(() => {
    if (!authLoading && !user) nav({ to: "/login" });
  }, [authLoading, user, nav]);

  useEffect(() => {
    if (isError) toast.error("No se pudieron cargar las notificaciones");
  }, [isError]);

  const hasUnread = items.some((n) => !n.is_read);

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; NOTIFICACIONES</div>
        <div className="flex items-center justify-between gap-4 mb-6">
          <h1 className="text-3xl font-bold tracking-tighter">Tus notificaciones</h1>
          {hasUnread && (
            <button
              type="button"
              onClick={() => {
                markRead.mutate(undefined, {
                  onSuccess: () => toast.success("Notificaciones marcadas como leídas"),
                  onError: () => toast.error("Error al marcar notificaciones como leídas"),
                });
              }}
              disabled={markRead.isPending}
              className="text-xs font-medium text-white bg-[#156287] hover:bg-[#0f4d68] active:scale-95 px-3 py-1.5 rounded-lg transition-all border border-sky-400/40 cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
            >
              <CheckCheck className="size-4" />
              <span>Marcar todas como leídas</span>
            </button>
          )}
        </div>
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
              <div
                key={n.id}
                className={`bg-surface-800 border border-surface-700 p-4 transition-colors ${
                  !n.is_read ? "border-l-4 border-l-[#156287]" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    {n.link_url ? (
                      <Link
                        to={n.link_url}
                        onClick={() => {
                          if (!n.is_read) markOneRead.mutate(n.id);
                        }}
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
