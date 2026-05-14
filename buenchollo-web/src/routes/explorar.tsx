import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Layout } from "@/components/Layout";
import { DealCard, type DealCardData } from "@/components/DealCard";
import { useAuth } from "@/hooks/useAuth";
import { z } from "zod";

const search = z.object({
  q: z.string().optional(),
  cat: z.string().optional(),
  sub: z.string().optional(),
  store: z.string().optional(),
  min: z.number().min(0).optional(),
  max: z.number().min(0).optional(),
  disc: z.number().min(0).max(99).optional(),
  sort: z.enum(["recent", "popular", "discount", "price_asc"]).optional(),
});

const SITE = "https://buenchollotech.lovable.app";

export const Route = createFileRoute("/explorar")({
  component: ExplorePage,
  validateSearch: (s) => search.parse(s),
  head: () => ({
    meta: [
      { title: "Explorar chollos de tecnología · BuencholloTech" },
      { name: "description", content: "Busca chollos de tecnología por categoría, subcategoría, tienda, precio y descuento mínimo. Encuentra la mejor oferta en segundos." },
      { property: "og:title", content: "Explorar chollos de tecnología" },
      { property: "og:description", content: "Filtra por categoría, tienda, precio y descuento. Encuentra el chollo que buscas." },
      { property: "og:url", content: `${SITE}/explorar` },
      { property: "og:type", content: "website" },
    ],
    links: [{ rel: "canonical", href: `${SITE}/explorar` }],
  }),
});

function ExplorePage() {
  const { user } = useAuth();
  const params = Route.useSearch();
  const nav = Route.useNavigate();
  const [deals, setDeals] = useState<DealCardData[]>([]);
  const [stores, setStores] = useState<any[]>([]);
  const [cats, setCats] = useState<any[]>([]);
  const [subs, setSubs] = useState<any[]>([]);
  const [favIds, setFavIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      supabase.from("stores").select("id,name,slug").eq("is_active", true).order("name"),
      supabase.from("categories").select("id,name,slug,parent_id").eq("is_active", true).order("display_order"),
    ]).then(([s, c]) => {
      setStores(s.data ?? []);
      setCats((c.data ?? []).filter((x: any) => !x.parent_id));
      setSubs((c.data ?? []).filter((x: any) => x.parent_id));
    });
  }, []);

  // Subcategorías filtradas según la categoría elegida
  const filteredSubs = params.cat ? subs.filter(s => s.parent_id === params.cat) : [];

  useEffect(() => {
    setLoading(true);
    const sel = "id,title,slug,image_url,images,current_price,previous_price,discount_percentage,temperature,published_at,status,expires_at,store:stores(name,slug),category:categories!deals_category_id_fkey(name,slug)";
    let q = supabase.from("deals").select(sel).eq("status", "active");
    if (params.q) q = q.ilike("title", `%${params.q}%`);
    if (params.cat) q = q.eq("category_id", params.cat);
    if (params.sub) q = q.eq("subcategory_id", params.sub);
    if (params.store) q = q.eq("store_id", params.store);
    if (params.min != null) q = q.gte("current_price", params.min);
    if (params.max != null) q = q.lte("current_price", params.max);
    if (params.disc != null) q = q.gte("discount_percentage", params.disc);
    const sort = params.sort ?? "recent";
    if (sort === "recent") q = q.order("published_at", { ascending: false });
    if (sort === "popular") q = q.order("temperature", { ascending: false });
    if (sort === "discount") q = q.order("discount_percentage", { ascending: false });
    if (sort === "price_asc") q = q.order("current_price", { ascending: true });
    q.limit(48).then(({ data }) => { setDeals((data ?? []) as any); setLoading(false); });
  }, [params]);

  useEffect(() => {
    if (!user) return;
    supabase.from("favorites").select("deal_id").eq("user_id", user.id)
      .then(({ data }) => setFavIds(new Set((data ?? []).map(f => f.deal_id))));
  }, [user]);

  const update = (patch: any) => nav({ search: { ...params, ...patch } as any });

  // Sanitiza enteros >= 0 (acepta vacío => undefined). Limita opcionalmente con max.
  const parseNonNeg = (v: string, max?: number): number | undefined => {
    if (v === "" || v == null) return undefined;
    const n = Math.floor(Number(v));
    if (!Number.isFinite(n) || n < 0) return undefined;
    return max != null ? Math.min(n, max) : n;
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; EXPLORAR_CHOLLOS</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-6">Todos los chollos {params.q && <span className="text-cyan-glow">/ "{params.q}"</span>}</h1>

        <div className="grid lg:grid-cols-[260px_1fr] gap-8">
          {/* Filtros */}
          <aside className="bg-surface-800 border border-surface-700 p-5 h-fit space-y-5">
            <div>
              <label htmlFor="filter-cat" className="block font-mono text-xs uppercase text-cyan-glow mb-2">Categoría</label>
              <select id="filter-cat" value={params.cat ?? ""} onChange={(e) => update({ cat: e.target.value || undefined, sub: undefined })}
                className="w-full bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono">
                <option value="">Todas</option>
                {cats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            {params.cat && filteredSubs.length > 0 && (
              <div>
                <label htmlFor="filter-sub" className="block font-mono text-xs uppercase text-cyan-glow mb-2">Subcategoría</label>
                <select id="filter-sub" value={params.sub ?? ""} onChange={(e) => update({ sub: e.target.value || undefined })}
                  className="w-full bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono">
                  <option value="">Todas</option>
                  {filteredSubs.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
            )}
            <div>
              <label htmlFor="filter-store" className="block font-mono text-xs uppercase text-cyan-glow mb-2">Tienda</label>
              <select id="filter-store" value={params.store ?? ""} onChange={(e) => update({ store: e.target.value || undefined })}
                className="w-full bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono">
                <option value="">Todas</option>
                {stores.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <span id="filter-price-label" className="block font-mono text-xs uppercase text-cyan-glow mb-2">Precio (€)</span>
              <div className="flex gap-2">
                <input id="filter-min" aria-labelledby="filter-price-label" aria-label="Precio mínimo en euros" type="number" min={0} step={1} inputMode="numeric" placeholder="Min" value={params.min ?? ""}
                  onKeyDown={(e) => { if (e.key === "-" || e.key === "e" || e.key === "+") e.preventDefault(); }}
                  onChange={(e) => update({ min: parseNonNeg(e.target.value) })}
                  className="w-full bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono" />
                <input id="filter-max" aria-labelledby="filter-price-label" aria-label="Precio máximo en euros" type="number" min={0} step={1} inputMode="numeric" placeholder="Max" value={params.max ?? ""}
                  onKeyDown={(e) => { if (e.key === "-" || e.key === "e" || e.key === "+") e.preventDefault(); }}
                  onChange={(e) => update({ max: parseNonNeg(e.target.value) })}
                  className="w-full bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono" />
              </div>
              {params.min != null && params.max != null && params.max < params.min && (
                <p className="text-alert-red text-xs font-mono mt-1">Max debe ser ≥ Min</p>
              )}
            </div>
            <div>
              <label htmlFor="filter-disc" className="block font-mono text-xs uppercase text-cyan-glow mb-2">Descuento mín. %</label>
              <input id="filter-disc" type="number" min={0} max={99} step={1} inputMode="numeric" placeholder="Ej: 30" value={params.disc ?? ""}
                onKeyDown={(e) => { if (e.key === "-" || e.key === "e" || e.key === "+") e.preventDefault(); }}
                onChange={(e) => update({ disc: parseNonNeg(e.target.value, 99) })}
                className="w-full bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono" />
            </div>
            <button onClick={() => nav({ search: {} as any })} className="w-full font-mono text-xs border border-surface-700 py-2 hover:border-alert-red hover:text-alert-red transition-colors">
              [ LIMPIAR FILTROS ]
            </button>
          </aside>

          {/* Resultados */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="font-mono text-xs text-muted-foreground">{loading ? "CARGANDO..." : `${deals.length} RESULTADOS`}</span>
              <select value={params.sort ?? "recent"} onChange={(e) => update({ sort: e.target.value })}
                className="bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono">
                <option value="recent">Más recientes</option>
                <option value="popular">Más populares</option>
                <option value="discount">Mayor descuento</option>
                <option value="price_asc">Precio más bajo</option>
              </select>
            </div>
            {deals.length === 0 && !loading ? (
              <div className="text-center py-16 text-muted-foreground font-mono text-sm">
                NO_RESULTS · prueba con otros filtros
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                {deals.map(d => <DealCard key={d.id} deal={d} isFavorite={favIds.has(d.id)} />)}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
