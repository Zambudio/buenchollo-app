import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Layout } from "@/components/Layout";
import { DealCard } from "@/components/DealCard";
import { useAuth } from "@/hooks/useAuth";

export const Route = createFileRoute("/favoritos")({
  component: FavoritesPage,
  head: () => ({
    meta: [
      { title: "Favoritos · BuencholloTech" },
      { name: "description", content: "Tus chollos guardados en BuencholloTech." },
      { property: "og:title", content: "Favoritos · BuencholloTech" },
      { property: "og:description", content: "Tus chollos guardados en BuencholloTech." },
      { property: "og:url", content: "https://buenchollotech.lovable.app/favoritos" }, { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: "https://buenchollotech.lovable.app/favoritos" }],
  }),
});

function FavoritesPage() {
  const { user, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const [deals, setDeals] = useState<any[]>([]);

  useEffect(() => {
    if (!authLoading && !user) nav({ to: "/login" });
  }, [authLoading, user]);

  useEffect(() => {
    if (!user) return;
    supabase.from("favorites")
      .select("deal:deals(id,title,slug,image_url,images,current_price,previous_price,discount_percentage,temperature,published_at,store:stores(name,slug),category:categories!deals_category_id_fkey(name,slug))")
      .eq("user_id", user.id).order("created_at", { ascending: false })
      .then(({ data }) => setDeals((data ?? []).map((x: any) => x.deal).filter(Boolean)));
  }, [user]);

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; MIS_FAVORITOS</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-8">Tus chollos guardados</h1>
        {deals.length === 0 ? (
          <p className="text-muted-foreground font-mono">Aún no has guardado ningún chollo. <Link to="/explorar" className="text-cyan-glow">Explora ahora</Link>.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {deals.map(d => <DealCard key={d.id} deal={d} isFavorite />)}
          </div>
        )}
      </div>
    </Layout>
  );
}
