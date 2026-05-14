import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Layout } from "@/components/Layout";
import { DealCard } from "@/components/DealCard";

const SITE = "https://buenchollotech.lovable.app";

export const Route = createFileRoute("/categoria/$slug")({
  component: CategoryPage,
  loader: async ({ params }) => {
    const { data } = await supabase
      .from("categories")
      .select("name,description")
      .eq("slug", params.slug)
      .maybeSingle();
    return { cat: data };
  },
  head: ({ params, loaderData }) => {
    const c: any = loaderData?.cat;
    const name = c?.name ?? params.slug;
    const url = `${SITE}/categoria/${params.slug}`;
    const desc = c?.description ?? `Chollos y ofertas de ${name} curados a diario en BuencholloTech.`;
    return {
      meta: [
        { title: `Chollos de ${name} · BuencholloTech` },
        { name: "description", content: String(desc).slice(0, 200) },
        { property: "og:title", content: `Chollos de ${name}` },
        { property: "og:description", content: String(desc).slice(0, 200) },
        { property: "og:url", content: url },
        { property: "og:type", content: "website" },
      ],
      links: [{ rel: "canonical", href: url }],
      scripts: [
        {
          type: "application/ld+json",
          children: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            name: `Chollos de ${name}`,
            url,
          }),
        },
      ],
    };
  },
});

function CategoryPage() {
  const { slug } = Route.useParams();
  const [cat, setCat] = useState<any>(null);
  const [deals, setDeals] = useState<any[]>([]);

  useEffect(() => {
    (async () => {
      const { data: c } = await supabase.from("categories").select("*").eq("slug", slug).maybeSingle();
      setCat(c);
      if (!c) return;
      const sel = "id,title,slug,image_url,images,current_price,previous_price,discount_percentage,temperature,published_at,store:stores(name,slug),category:categories!deals_category_id_fkey(name,slug)";
      const { data } = await supabase.from("deals").select(sel).eq("status", "active")
        .or(`category_id.eq.${c.id},subcategory_id.eq.${c.id}`)
        .order("published_at", { ascending: false }).limit(48);
      setDeals(data ?? []);
    })();
  }, [slug]);

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <Link to="/categorias" className="font-mono text-xs text-cyan-glow hover:text-foreground">← TODAS LAS CATEGORÍAS</Link>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mt-3 mb-2">{cat?.name ?? "Categoría"}</h1>
        <p className="text-muted-foreground font-mono text-sm mb-8">{deals.length} chollos activos</p>
        {deals.length === 0 ? (
          <p className="text-muted-foreground font-mono">No hay chollos por ahora en esta categoría.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {deals.map(d => <DealCard key={d.id} deal={d} />)}
          </div>
        )}
      </div>
    </Layout>
  );
}
