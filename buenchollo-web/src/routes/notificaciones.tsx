import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { formatRelativeTime } from "@/lib/format";

export const Route = createFileRoute("/notificaciones")({
  component: NotificationsPage,
  head: () => ({
    meta: [
      { title: "Notificaciones · BuencholloTech" },
      { name: "description", content: "Bandeja de notificaciones de tus alertas en BuencholloTech." },
      { property: "og:title", content: "Notificaciones · BuencholloTech" },
      { property: "og:description", content: "Bandeja de notificaciones de tus alertas en BuencholloTech." },
      { property: "og:url", content: "https://buenchollotech.lovable.app/notificaciones" }, { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.lovable.app/notificaciones" }],
  }),
});

function NotificationsPage() {
  const { user, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => { if (!authLoading && !user) nav({ to: "/login" }); }, [authLoading, user]);

  useEffect(() => {
    if (!user) return;
    supabase.from("notifications").select("*").eq("user_id", user.id).order("created_at", { ascending: false }).limit(50)
      .then(({ data }) => setItems(data ?? []));
    // marcar leídas
    supabase.from("notifications").update({ is_read: true }).eq("user_id", user.id).eq("is_read", false).then(() => {});
  }, [user]);

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; NOTIFICACIONES</div>
        <h1 className="text-3xl font-bold tracking-tighter mb-6">Tus notificaciones</h1>
        {items.length === 0 ? (
          <div className="bg-surface-800 border border-surface-700 p-12 text-center text-muted-foreground font-mono text-sm">
            Sin notificaciones por ahora. Crea alertas para recibir avisos cuando aparezcan chollos que te interesen.
          </div>
        ) : (
          <div className="space-y-2">
            {items.map(n => (
              <div key={n.id} className="bg-surface-800 border border-surface-700 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-bold text-base">{n.title}</h2>
                    {n.body && <p className="text-sm text-muted-foreground mt-1">{n.body}</p>}
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground whitespace-nowrap">{formatRelativeTime(n.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
