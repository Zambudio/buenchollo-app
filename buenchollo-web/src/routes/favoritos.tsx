import { logError } from "@/lib/logger";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { favoritesApi } from "@/services/api/deals";
import { Layout } from "@/components/layout/Layout";
import { DealCard, type DealCardData } from "@/features/deals/components/DealCard";
import { useAuth } from "@/hooks/useAuth";

export const Route = createFileRoute("/favoritos")({
  component: FavoritesPage,
  head: () => ({
    meta: [
      { title: "Favoritos · BuenChollo Tech" },
      { name: "description", content: "Tus chollos guardados en BuenChollo Tech." },
      { property: "og:title", content: "Favoritos · BuenChollo Tech" },
      { property: "og:description", content: "Tus chollos guardados en BuenChollo Tech." },
      { property: "og:url", content: "https://buenchollotech.com/favoritos" },
      { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.com/favoritos" }],
  }),
});

function FavoritesPage() {
  const { user, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const [deals, setDeals] = useState<DealCardData[]>([]);

  useEffect(() => {
    if (!authLoading && !user) nav({ to: "/login" });
  }, [authLoading, user, nav]);

  useEffect(() => {
    if (!user) return;
    favoritesApi
      .getFavorites()
      .then(setDeals)
      .catch((error) => logError("Error cargando favoritos", error));
  }, [user]);

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; MIS_FAVORITOS</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-8">
          Tus chollos guardados
        </h1>
        {deals.length === 0 ? (
          <p className="text-muted-foreground font-mono">
            Aún no has guardado ningún chollo.{" "}
            <Link to="/explorar" className="text-cyan-glow">
              Explora ahora
            </Link>
            .
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {deals.map((d) => (
              <DealCard key={d.id} deal={d} isFavorite />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
