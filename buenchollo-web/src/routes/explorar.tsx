import { logError } from "@/lib/logger";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Layout } from "@/components/layout/Layout";
import { DealCard, type DealCardData } from "@/features/deals/components/DealCard";
import { useMyVotes } from "@/features/deals/hooks/useMyVotes";
import { useAuth } from "@/hooks/useAuth";
import { z } from "zod";
import { dealsService, favoritesApi } from "@/services/api/deals";
import { categoriesService, type Category } from "@/services/api/categories";
import { storesService, type Store } from "@/services/api/stores";

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

/** Shape de los search params de /explorar. Compartido para que otros
 *  componentes (Header, CategoriesDrawer) puedan tipar sus enlaces. */
export type ExplorarSearch = z.infer<typeof search>;

const SITE = "https://buenchollotech.com";

export const Route = createFileRoute("/explorar")({
  component: ExplorePage,
  validateSearch: (s) => search.parse(s),
  head: () => ({
    meta: [
      { title: "Explorar chollos de tecnología · BuenChollo Tech" },
      {
        name: "description",
        content:
          "Busca chollos de tecnología por categoría, subcategoría, tienda, precio y descuento mínimo. Encuentra la mejor oferta en segundos.",
      },
      { property: "og:title", content: "Explorar chollos de tecnología" },
      {
        property: "og:description",
        content:
          "Filtra por categoría, tienda, precio y descuento. Encuentra el chollo que buscas.",
      },
      { property: "og:url", content: `${SITE}/explorar` },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex, follow" },
    ],
    links: [{ rel: "canonical", href: `${SITE}/explorar` }],
  }),
});

function ExplorePage() {
  const { user } = useAuth();
  const params = Route.useSearch();
  const nav = Route.useNavigate();
  const [deals, setDeals] = useState<DealCardData[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [cats, setCats] = useState<Category[]>([]);
  const [subs, setSubs] = useState<Category[]>([]);
  const [filtersReady, setFiltersReady] = useState(false);
  const [favIds, setFavIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const myVotes = useMyVotes(deals.map((d) => d.id));

  useEffect(() => {
    Promise.all([storesService.getAll(), categoriesService.getAll()])
      .then(([s, c]) => {
        setStores(s);
        setCats(c.filter((x) => !x.parent_id));
        setSubs(c.filter((x) => !!x.parent_id));
        setFiltersReady(true);
      })
      .catch((error) => {
        logError("Error cargando filtros de explorar", error);
        setFiltersReady(true);
      });
  }, []);

  // Los enlaces compartibles usan slugs legibles, pero la API filtra por UUID.
  // También aceptamos UUIDs para no romper URLs antiguas.
  const selectedCat = params.cat
    ? cats.find((category) => category.slug === params.cat || category.id === params.cat)
    : undefined;
  const filteredSubs = selectedCat
    ? subs.filter((subcategory) => subcategory.parent_id === selectedCat.id)
    : [];
  const selectedSub = params.sub
    ? filteredSubs.find(
        (subcategory) => subcategory.slug === params.sub || subcategory.id === params.sub,
      )
    : undefined;

  useEffect(() => {
    if (!filtersReady) return;
    setLoading(true);
    dealsService
      .search({
        category_id: selectedCat?.id,
        subcategory_id: selectedSub?.id,
        store_id: params.store,
        search: params.q,
        min_price: params.min,
        max_price: params.max,
        min_discount: params.disc,
        sort: params.sort,
        limit: 48,
      })
      .then((data) => {
        setDeals(data);
        setLoading(false);
      })
      .catch((error) => {
        logError("Error buscando chollos en explorar", error);
        setLoading(false);
      });
  }, [filtersReady, params, selectedCat?.id, selectedSub?.id]);

  useEffect(() => {
    if (!user) {
      setFavIds(new Set());
      return;
    }
    favoritesApi
      .getFavorites()
      .then((favs) => setFavIds(new Set(favs.map((d) => d.id))))
      .catch(() => setFavIds(new Set()));
  }, [user]);

  const update = (patch: Partial<ExplorarSearch>) => nav({ search: { ...params, ...patch } });

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
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; EXPLORAR CHOLLOS</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-6">
          Todos los chollos {params.q && <span className="text-cyan-glow">/ "{params.q}"</span>}
        </h1>

        <div className="grid lg:grid-cols-[260px_1fr] gap-8">
          {/* Filtros */}
          <aside className="rounded-xl bg-surface-800 border border-surface-700 p-5 h-fit space-y-5">
            <div>
              <label
                htmlFor="filter-cat"
                className="block font-mono text-xs uppercase text-cyan-glow mb-2"
              >
                Categoría
              </label>
              <select
                id="filter-cat"
                value={selectedCat?.slug ?? ""}
                onChange={(e) => update({ cat: e.target.value || undefined, sub: undefined })}
                className="w-full rounded-lg bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono"
              >
                <option value="">Todas</option>
                {cats.map((c) => (
                  <option key={c.id} value={c.slug}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            {selectedCat && filteredSubs.length > 0 && (
              <div>
                <label
                  htmlFor="filter-sub"
                  className="block font-mono text-xs uppercase text-cyan-glow mb-2"
                >
                  Subcategoría
                </label>
                <select
                  id="filter-sub"
                  value={selectedSub?.slug ?? ""}
                  onChange={(e) => update({ sub: e.target.value || undefined })}
                  className="w-full rounded-lg bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono"
                >
                  <option value="">Todas</option>
                  {filteredSubs.map((s) => (
                    <option key={s.id} value={s.slug}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label
                htmlFor="filter-store"
                className="block font-mono text-xs uppercase text-cyan-glow mb-2"
              >
                Tienda
              </label>
              <select
                id="filter-store"
                value={params.store ?? ""}
                onChange={(e) => update({ store: e.target.value || undefined })}
                className="w-full rounded-lg bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono"
              >
                <option value="">Todas</option>
                {stores.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <span
                id="filter-price-label"
                className="block font-mono text-xs uppercase text-cyan-glow mb-2"
              >
                Precio (€)
              </span>
              <div className="flex gap-2">
                <input
                  id="filter-min"
                  aria-labelledby="filter-price-label"
                  aria-label="Precio mínimo en euros"
                  type="number"
                  min={0}
                  step={1}
                  inputMode="numeric"
                  placeholder="Min"
                  value={params.min ?? ""}
                  onKeyDown={(e) => {
                    if (e.key === "-" || e.key === "e" || e.key === "+") e.preventDefault();
                  }}
                  onChange={(e) => update({ min: parseNonNeg(e.target.value) })}
                  className="w-full rounded-lg bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono"
                />
                <input
                  id="filter-max"
                  aria-labelledby="filter-price-label"
                  aria-label="Precio máximo en euros"
                  type="number"
                  min={0}
                  step={1}
                  inputMode="numeric"
                  placeholder="Max"
                  value={params.max ?? ""}
                  onKeyDown={(e) => {
                    if (e.key === "-" || e.key === "e" || e.key === "+") e.preventDefault();
                  }}
                  onChange={(e) => update({ max: parseNonNeg(e.target.value) })}
                  className="w-full rounded-lg bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono"
                />
              </div>
              {params.min != null && params.max != null && params.max < params.min && (
                <p className="text-alert-red text-xs font-mono mt-1">Max debe ser ≥ Min</p>
              )}
            </div>
            <div>
              <label
                htmlFor="filter-disc"
                className="block font-mono text-xs uppercase text-cyan-glow mb-2"
              >
                Descuento mín. %
              </label>
              <input
                id="filter-disc"
                type="number"
                min={0}
                max={99}
                step={1}
                inputMode="numeric"
                placeholder="Ej: 30"
                value={params.disc ?? ""}
                onKeyDown={(e) => {
                  if (e.key === "-" || e.key === "e" || e.key === "+") e.preventDefault();
                }}
                onChange={(e) => update({ disc: parseNonNeg(e.target.value, 99) })}
                className="w-full rounded-lg bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono"
              />
            </div>
            <button
              onClick={() => nav({ search: {} })}
              className="w-full rounded-lg font-mono text-xs border border-surface-700 py-2 hover:border-alert-red hover:text-alert-red transition-colors"
            >
              LIMPIAR FILTROS
            </button>
          </aside>

          {/* Resultados */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="font-mono text-xs text-muted-foreground">
                {loading ? "CARGANDO..." : `${deals.length} RESULTADOS`}
              </span>
              <select
                value={params.sort ?? "recent"}
                onChange={(e) => update({ sort: e.target.value as ExplorarSearch["sort"] })}
                className="rounded-lg bg-surface-900 border border-surface-700 px-2 py-2 text-sm font-mono"
              >
                <option value="recent">Más recientes</option>
                <option value="popular">Más populares</option>
                <option value="discount">Mayor descuento</option>
                <option value="price_asc">Precio más bajo</option>
              </select>
            </div>
            {deals.length === 0 && !loading ? (
              <div className="text-center py-16 text-muted-foreground font-mono text-sm">
                SIN RESULTADOS · prueba con otros filtros
              </div>
            ) : (
              <div className="deal-feed-grid">
                {deals.map((d) => (
                  <DealCard
                    key={d.id}
                    deal={d}
                    isFavorite={favIds.has(d.id)}
                    myVote={myVotes[d.id]}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
