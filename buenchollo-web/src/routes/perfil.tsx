import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { useAuth } from "@/hooks/useAuth";
import { authApi, type MyStats } from "@/services/api/auth";
import { errorMessage } from "@/lib/errors";
import { toast } from "sonner";
import { MessageSquare, ArrowUp, ArrowDown, Heart, ThumbsUp, Inbox, Flame } from "lucide-react";

export const Route = createFileRoute("/perfil")({
  component: ProfilePage,
  head: () => ({
    meta: [
      { title: "Mi perfil · BuencholloTech" },
      { name: "description", content: "Ajustes de tu cuenta de BuencholloTech." },
      { property: "og:title", content: "Mi perfil · BuencholloTech" },
      { property: "og:description", content: "Ajustes de tu cuenta de BuencholloTech." },
      { property: "og:url", content: "https://buenchollotech.lovable.app/perfil" },
      { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.lovable.app/perfil" }],
  }),
});

function ProfilePage() {
  const { user, loading: authLoading, signOut } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [stats, setStats] = useState<MyStats | null>(null);

  useEffect(() => {
    if (!authLoading && !user) nav({ to: "/login" });
  }, [authLoading, user, nav]);

  useEffect(() => {
    if (!user) return;
    authApi
      .getMyProfile()
      .then((p) => {
        setName(p.display_name ?? "");
        setBio(p.bio ?? "");
      })
      .catch(() => {
        /* perfil opcional */
      });
    authApi
      .getMyStats()
      .then(setStats)
      .catch(() => {
        /* stats no críticas */
      });
  }, [user]);

  const save = async () => {
    if (!user) return;
    try {
      await authApi.updateMyProfile({
        display_name: name.slice(0, 50),
        bio: bio.slice(0, 300),
      });
      toast.success("Perfil actualizado");
    } catch (e: unknown) {
      toast.error(errorMessage(e, "Error al guardar"));
    }
  };

  const statItems = stats
    ? [
        { icon: MessageSquare, label: "Comentarios hechos", value: stats.comments_made },
        { icon: Inbox, label: "Respuestas recibidas", value: stats.comments_received },
        { icon: ThumbsUp, label: "Me gusta dados", value: stats.likes_given },
        { icon: ArrowUp, label: "Me gusta recibidos", value: stats.likes_received },
        { icon: ArrowDown, label: "No me gusta recibidos", value: stats.dislikes_received },
        { icon: Flame, label: "Votos a chollos", value: stats.deal_votes_cast },
        { icon: Heart, label: "Favoritos", value: stats.favorites_count },
      ]
    : [];

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; MI_PERFIL</div>
        <h1 className="text-3xl font-bold tracking-tighter mb-6">Mi perfil</h1>

        {/* Estadísticas */}
        <div className="mb-6">
          <h2 className="font-mono text-xs uppercase text-cyan-glow mb-3 border-b border-surface-700 pb-2">
            Estadísticas
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {statItems.map((s) => (
              <div
                key={s.label}
                className="bg-surface-800 border border-surface-700 p-3 flex flex-col gap-1"
              >
                <s.icon className="size-4 text-cyan-glow" />
                <div className="font-mono text-2xl font-bold tabular-nums">{s.value}</div>
                <div className="font-mono text-[10px] uppercase text-muted-foreground leading-tight">
                  {s.label}
                </div>
              </div>
            ))}
            {!stats && (
              <div className="font-mono text-xs text-muted-foreground col-span-full">
                Cargando estadísticas...
              </div>
            )}
          </div>
        </div>

        <div className="bg-surface-800 border border-surface-700 p-6 space-y-4">
          <div>
            <label className="block text-xs font-mono uppercase text-cyan-glow mb-1">Email</label>
            <p className="font-mono text-sm text-muted-foreground">{user?.email}</p>
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-cyan-glow mb-1">
              Nombre visible
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow"
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-cyan-glow mb-1">Bio</label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              className="w-full bg-surface-900 border border-surface-700 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-glow"
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={save}
              className="bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-5 py-3 hover:bg-foreground"
            >
              [ GUARDAR ]
            </button>
            <button
              onClick={signOut}
              className="border border-surface-700 hover:border-alert-red hover:text-alert-red font-mono text-xs font-bold px-5 py-3"
            >
              [ CERRAR SESIÓN ]
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
